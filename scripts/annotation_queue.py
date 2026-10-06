"""Small SQLite-backed queue for shared thread-annotation workers.

The queue is deliberately offline.  Workers read an input packet, write the
model result to ``results/<input basename>``, and then submit that result for
validation.  The manifest and result format are the same as the annotation
pilot; validation is delegated to :mod:`assemble_thread_annotations`.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import time
from typing import Any


# Keep this script executable from the repository root as well as importable
# as ``scripts.annotation_queue``.
try:
    from scripts.assemble_thread_annotations import validate_result
    from scripts.annotation_manifest import validate_manifest_tasks as _validate_manifest
except ModuleNotFoundError:  # pragma: no cover - exercised by direct execution
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from scripts.assemble_thread_annotations import validate_result
    from scripts.annotation_manifest import validate_manifest_tasks as _validate_manifest


STATES = ("pending", "running", "complete", "failed")
DECISIONS = ("candidate_issue", "no_issue", "needs_context")
# Full-run model calls can take longer than ten minutes.  The CLI also accepts
# a shorter lease when a caller explicitly wants one.
DEFAULT_LEASE_SECONDS = 30 * 60
VALIDATION_DEFERRED_MARKER = "validation-deferred"


class QueueError(RuntimeError):
    """A queue operation cannot be completed without changing its state."""


def _queue_path(run_dir: Path | str) -> Path:
    return Path(run_dir) / "queue.sqlite3"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _error(errors: list[str]) -> str | None:
    if not errors:
        return None
    return "; ".join(sorted(set(errors)))


def _normalise_input_file(run_dir: Path, value: str | Path) -> str:
    path = Path(value)
    if path.is_absolute():
        try:
            path = path.resolve().relative_to(run_dir.resolve())
        except ValueError as exc:
            raise QueueError("input-file must be inside run-dir") from exc
    if not path.parts or ".." in path.parts:
        raise QueueError("input-file must be a relative path inside run-dir")
    return path.as_posix()


def _result_path(run_dir: Path, input_file: str) -> Path:
    return run_dir / "results" / Path(input_file).name


def _validation_deferred(run_dir: Path | str) -> bool:
    return (Path(run_dir) / VALIDATION_DEFERRED_MARKER).exists()


def _connect(run_dir: Path | str) -> sqlite3.Connection:
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(_queue_path(run_dir)), timeout=30)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA busy_timeout = 30000")
    connection.execute("PRAGMA journal_mode = WAL")
    connection.execute("PRAGMA synchronous = NORMAL")
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            thread_key TEXT NOT NULL UNIQUE,
            input_file TEXT NOT NULL UNIQUE,
            input_sha256 TEXT NOT NULL,
            stratum TEXT NOT NULL,
            worker_id TEXT NOT NULL,
            manifest_json TEXT NOT NULL,
            state TEXT NOT NULL CHECK (state IN ('pending', 'running', 'complete', 'failed')),
            worker TEXT,
            lease_until REAL,
            attempts INTEGER NOT NULL DEFAULT 0,
            error TEXT,
            decision TEXT,
            created_at REAL NOT NULL,
            updated_at REAL NOT NULL
        )
        """
    )
    connection.execute("CREATE INDEX IF NOT EXISTS tasks_state_id ON tasks(state, id)")
    connection.execute("CREATE INDEX IF NOT EXISTS tasks_worker_state ON tasks(worker, state)")
    connection.commit()
    return connection


def _inspect_task(run_dir: Path, task: dict[str, Any]) -> tuple[str, str | None, str | None]:
    """Return ``(kind, error, decision)`` for a task's on-disk files.

    ``kind`` is ``valid``, ``missing`` or ``invalid``.  A missing result is
    intentionally separate from a valid ``no_issue`` result.
    """

    input_file = task["input_file"]
    if _validation_deferred(run_dir):
        if not _result_path(run_dir, input_file).is_file():
            return "missing", "result_missing", None
        return "valid", None, None

    input_path = run_dir / input_file
    if not input_path.is_file():
        return "missing", "input_missing", None
    try:
        actual_sha256 = _sha256(input_path)
    except OSError:
        return "missing", "input_missing", None
    if actual_sha256 != task["input_sha256"]:
        return "invalid", "input_sha256_mismatch_manifest", None
    try:
        packet = _load_json(input_path)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return "invalid", "input_invalid_json", None

    result_path = _result_path(run_dir, input_file)
    if not result_path.is_file():
        return "missing", "result_missing", None
    try:
        result = _load_json(result_path)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return "invalid", "result_invalid_json", None
    errors = validate_result(result, packet, task, actual_sha256)
    if errors:
        return "invalid", _error(errors), None
    return "valid", None, result["decision"]


def _row_task(run_dir: Path, row: sqlite3.Row) -> dict[str, Any]:
    task = json.loads(row["manifest_json"])
    task.update({
        "state": row["state"],
        "worker": row["worker"],
        "lease_until": row["lease_until"],
        "attempts": row["attempts"],
        "error": row["error"],
        "decision": row["decision"],
        "input_path": str((run_dir / row["input_file"]).resolve()),
        "output_path": str(_result_path(run_dir, row["input_file"]).resolve()),
    })
    return task


def _reconcile_locked(
    connection: sqlite3.Connection,
    run_dir: Path,
    where: str = "state IN ('pending', 'running', 'failed')",
    parameters: tuple[Any, ...] = (),
) -> None:
    """Complete tasks whose valid result was written before a worker stopped.

    This runs while the caller owns ``BEGIN IMMEDIATE``.  It is intentionally
    limited to non-complete rows, so a result-only recovery never reopens a
    valid completion.
    """

    rows = connection.execute(f"SELECT * FROM tasks WHERE {where}", parameters).fetchall()
    now = time.time()
    for row in rows:
        task = json.loads(row["manifest_json"])
        kind, _, decision = _inspect_task(run_dir, task)
        if kind == "valid":
            connection.execute(
                """
                UPDATE tasks SET state='complete', worker=NULL, lease_until=NULL,
                  error=NULL, decision=?, updated_at=? WHERE id=?
                """,
                (decision, now, row["id"]),
            )


def init_queue(
    run_dir: Path | str, *, incremental: bool = False
) -> dict[str, int | dict[str, int]]:
    """Import manifest tasks and reuse only structurally valid results.

    Incremental imports trust an existing row whose thread key, input path and
    input hash are unchanged.  This lets a producer append manifest batches
    without rereading completed or currently running input files.
    """

    run_dir = Path(run_dir)
    manifest = _load_json(run_dir / "manifest.json")
    tasks = _validate_manifest(manifest)
    connection = _connect(run_dir)
    now = time.time()
    try:
        connection.execute("BEGIN IMMEDIATE")
        for task in tasks:
            old = connection.execute(
                "SELECT * FROM tasks WHERE thread_key = ?", (task["thread_key"],)
            ).fetchone()
            same_input = old is not None and (
                old["input_file"] == task["input_file"]
                and old["input_sha256"] == task["input_sha256"]
            )
            if incremental and old is not None:
                if not same_input:
                    raise ValueError(
                        "incremental manifest changed input path/hash for "
                        f"{task['thread_key']}"
                    )
                # Preserve every runtime field, including ownership and lease;
                # only refresh the manifest payload used in future claim output.
                connection.execute(
                    """
                    UPDATE tasks SET stratum=?, worker_id=?, manifest_json=?
                    WHERE thread_key=?
                    """,
                    (
                        str(task["stratum"]), _json(task["worker_id"]),
                        _json(task), task["thread_key"],
                    ),
                )
                continue

            kind, reason, decision = _inspect_task(run_dir, task)
            if old is None:
                state = "complete" if kind == "valid" else "pending"
                worker = None
                lease_until = None
                attempts = 0
                error = None if kind == "valid" else reason
            else:
                if kind == "valid":
                    state = "complete"
                    worker = None
                    lease_until = None
                    error = None
                elif old["state"] == "complete" or not same_input:
                    state = "pending"
                    worker = None
                    lease_until = None
                    error = reason
                else:
                    # A live worker or an explicit failed state belongs to the
                    # queue until release/retry; init must not steal it.
                    state = old["state"]
                    worker = old["worker"]
                    lease_until = old["lease_until"]
                    error = old["error"] or reason
                attempts = old["attempts"]

            conflict = connection.execute(
                "SELECT id FROM tasks WHERE input_file = ? AND thread_key <> ?",
                (task["input_file"], task["thread_key"]),
            ).fetchone()
            if conflict is not None:
                raise ValueError(f"input_file belongs to another thread: {task['input_file']}")

            stored_decision = None
            if kind == "valid":
                stored_decision = decision
                if (
                    _validation_deferred(run_dir)
                    and old is not None
                    and same_input
                    and old["state"] == "complete"
                ):
                    stored_decision = old["decision"]

            values = (
                task["thread_key"], task["input_file"], task["input_sha256"],
                str(task["stratum"]), _json(task["worker_id"]), _json(task),
                state, worker, lease_until, attempts, error, stored_decision,
                old["created_at"] if old is not None else now, now,
            )
            if old is None:
                connection.execute(
                    """
                    INSERT INTO tasks
                    (thread_key, input_file, input_sha256, stratum, worker_id,
                     manifest_json, state, worker, lease_until, attempts, error,
                     decision, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    values,
                )
            else:
                connection.execute(
                    """
                    UPDATE tasks SET input_file=?, input_sha256=?, stratum=?,
                      worker_id=?, manifest_json=?, state=?, worker=?,
                      lease_until=?, attempts=?, error=?, decision=?, updated_at=?
                    WHERE thread_key=?
                    """,
                    (
                        task["input_file"], task["input_sha256"], str(task["stratum"]),
                        _json(task["worker_id"]), _json(task), state, worker,
                        lease_until, attempts, error,
                        stored_decision, now, task["thread_key"],
                    ),
                )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
    return status(run_dir)


def claim(
    run_dir: Path | str,
    worker: str,
    limit: int = 1,
    lease_seconds: int | float = DEFAULT_LEASE_SECONDS,
) -> list[dict[str, Any]]:
    """Atomically claim pending tasks, returning owned tasks first."""

    if not isinstance(worker, str) or not worker.strip():
        raise ValueError("worker must be non-empty")
    if limit < 1:
        raise ValueError("limit must be positive")
    if lease_seconds <= 0:
        raise ValueError("lease_seconds must be positive")
    run_dir = Path(run_dir)
    connection = _connect(run_dir)
    now = time.time()
    try:
        connection.execute("BEGIN IMMEDIATE")
        _reconcile_locked(
            connection, run_dir, "state='running' AND worker=?", (worker,)
        )
        own = connection.execute(
            "SELECT id FROM tasks WHERE state='running' AND worker=? ORDER BY id LIMIT ?",
            (worker, limit),
        ).fetchall()
        if own:
            ids = [row["id"] for row in own]
            placeholders = ",".join("?" for _ in ids)
            connection.execute(
                f"UPDATE tasks SET lease_until=?, updated_at=? WHERE id IN ({placeholders})",
                (now + float(lease_seconds), now, *ids),
            )
        else:
            pending = connection.execute(
                "SELECT id FROM tasks WHERE state='pending' ORDER BY id LIMIT ?", (limit,)
            ).fetchall()
            ids = [row["id"] for row in pending]
            if ids:
                placeholders = ",".join("?" for _ in ids)
                connection.execute(
                    f"""
                    UPDATE tasks SET state='running', worker=?, lease_until=?,
                      attempts=attempts+1, updated_at=?
                    WHERE state='pending' AND id IN ({placeholders})
                    """,
                    (worker, now + float(lease_seconds), now, *ids),
                )
        rows = []
        if ids:
            placeholders = ",".join("?" for _ in ids)
            rows = connection.execute(
                f"SELECT * FROM tasks WHERE id IN ({placeholders}) ORDER BY id", ids
            ).fetchall()
        connection.commit()
        return [_row_task(run_dir, row) for row in rows]
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def submit(run_dir: Path | str, worker: str, input_file: str | Path) -> dict[str, Any]:
    """Validate a worker's result and mark its owned task complete/failed."""

    run_dir = Path(run_dir)
    input_file = _normalise_input_file(run_dir, input_file)
    connection = _connect(run_dir)
    try:
        row = connection.execute(
            "SELECT * FROM tasks WHERE input_file=?", (input_file,)
        ).fetchone()
        if row is None:
            raise QueueError(f"unknown input_file: {input_file}")
        if row["state"] != "running" or row["worker"] != worker:
            raise QueueError("task is not running for this worker")
        task = json.loads(row["manifest_json"])
        kind, reason, decision = _inspect_task(run_dir, task)
        connection.execute("BEGIN IMMEDIATE")
        # Check ownership again after taking the write lock.  A release/retry
        # racing with validation must never allow a late submit to complete a
        # task claimed by another worker.
        current = connection.execute("SELECT * FROM tasks WHERE id=?", (row["id"],)).fetchone()
        if current is None or current["state"] != "running" or current["worker"] != worker:
            raise QueueError("task is no longer running for this worker")
        state = "complete" if kind == "valid" else "failed"
        connection.execute(
            """
            UPDATE tasks SET state=?, worker=NULL, lease_until=NULL, error=?,
              decision=?, updated_at=? WHERE id=?
            """,
            (state, reason, decision if kind == "valid" else None, time.time(), row["id"]),
        )
        updated = connection.execute("SELECT * FROM tasks WHERE id=?", (row["id"],)).fetchone()
        connection.commit()
        return _row_task(run_dir, updated)
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def defer_validation(run_dir: Path | str) -> int:
    """Enable output-only completion and reconcile failed tasks with results."""

    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / VALIDATION_DEFERRED_MARKER).touch(exist_ok=True)
    connection = _connect(run_dir)
    try:
        connection.execute("BEGIN IMMEDIATE")
        before = connection.execute(
            "SELECT COUNT(*) FROM tasks WHERE state='failed'"
        ).fetchone()[0]
        _reconcile_locked(connection, run_dir, "state='failed'")
        after = connection.execute(
            "SELECT COUNT(*) FROM tasks WHERE state='failed'"
        ).fetchone()[0]
        connection.commit()
        return before - after
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def advance(
    run_dir: Path | str,
    worker: str,
    input_file: str | Path | None = None,
) -> dict[str, Any] | None:
    """Submit one completed task, then claim at most one next task."""

    if input_file is not None:
        submitted = submit(run_dir, worker, input_file)
        if submitted["state"] != "complete":
            reason = submitted.get("error") or "submission_failed"
            raise QueueError(f"cannot advance: {reason}")
    next_tasks = claim(run_dir, worker, limit=1)
    return next_tasks[0] if next_tasks else None


def release(run_dir: Path | str, worker: str) -> int:
    """Return all currently running tasks for ``worker`` to pending."""

    connection = _connect(run_dir)
    try:
        connection.execute("BEGIN IMMEDIATE")
        _reconcile_locked(
            connection, Path(run_dir), "state='running' AND worker=?", (worker,)
        )
        cursor = connection.execute(
            """
            UPDATE tasks SET state='pending', worker=NULL, lease_until=NULL,
              updated_at=? WHERE state='running' AND worker=?
            """,
            (time.time(), worker),
        )
        count = cursor.rowcount
        connection.commit()
        return count
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def retry(run_dir: Path | str) -> int:
    """Requeue failed tasks and running tasks whose lease has expired."""

    connection = _connect(run_dir)
    try:
        connection.execute("BEGIN IMMEDIATE")
        _reconcile_locked(connection, Path(run_dir), "state IN ('running', 'failed')")
        now = time.time()
        cursor = connection.execute(
            """
            UPDATE tasks SET state='pending', worker=NULL, lease_until=NULL,
              updated_at=?
            WHERE state='failed'
               OR (state='running' AND (lease_until IS NULL OR lease_until <= ?))
            """,
            (now, now),
        )
        count = cursor.rowcount
        connection.commit()
        return count
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def status(run_dir: Path | str) -> dict[str, Any]:
    """Return state counts and decisions for valid completed results."""

    connection = _connect(run_dir)
    try:
        result: dict[str, Any] = {state: 0 for state in STATES}
        for row in connection.execute("SELECT state, COUNT(*) AS count FROM tasks GROUP BY state"):
            if row["state"] in result:
                result[row["state"]] = row["count"]
        decisions = {decision: 0 for decision in DECISIONS}
        for row in connection.execute(
            "SELECT decision, COUNT(*) AS count FROM tasks "
            "WHERE state='complete' AND decision IS NOT NULL GROUP BY decision"
        ):
            if row["decision"] in decisions:
                decisions[row["decision"]] = row["count"]
        result["decision_counts"] = decisions
        result["validation_deferred"] = _validation_deferred(run_dir)
        result["unvalidated_output_count"] = connection.execute(
            "SELECT COUNT(*) FROM tasks WHERE state='complete' AND decision IS NULL"
        ).fetchone()[0]
        return result
    finally:
        connection.close()


def _print(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, sort_keys=True))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    def run_dir_parser(name: str) -> argparse.ArgumentParser:
        child = subparsers.add_parser(name)
        child.add_argument("--run-dir", required=True, type=Path)
        return child

    init_parser = run_dir_parser("init")
    init_parser.add_argument(
        "--incremental", action="store_true",
        help="skip unchanged existing tasks while importing appended manifest tasks",
    )
    claim_parser = run_dir_parser("claim")
    claim_parser.add_argument("--worker", required=True)
    claim_parser.add_argument("--limit", type=int, default=1)
    claim_parser.add_argument("--lease-seconds", type=float, default=DEFAULT_LEASE_SECONDS)
    submit_parser = run_dir_parser("submit")
    submit_parser.add_argument("--worker", required=True)
    submit_parser.add_argument("--input-file", required=True)
    release_parser = run_dir_parser("release")
    release_parser.add_argument("--worker", required=True)
    run_dir_parser("defer-validation")
    advance_parser = run_dir_parser("advance")
    advance_parser.add_argument("--worker", required=True)
    advance_parser.add_argument("--input-file")
    run_dir_parser("status")
    run_dir_parser("retry")
    args = parser.parse_args(argv)

    try:
        if args.command == "init":
            _print(init_queue(args.run_dir, incremental=args.incremental))
        elif args.command == "claim":
            _print(claim(args.run_dir, args.worker, args.limit, args.lease_seconds))
        elif args.command == "submit":
            _print(submit(args.run_dir, args.worker, args.input_file))
        elif args.command == "release":
            _print({"released": release(args.run_dir, args.worker)})
        elif args.command == "defer-validation":
            _print({"reconciled": defer_validation(args.run_dir)})
        elif args.command == "advance":
            _print(advance(args.run_dir, args.worker, args.input_file))
        elif args.command == "status":
            _print(status(args.run_dir))
        elif args.command == "retry":
            _print({"retried": retry(args.run_dir)})
    except (OSError, ValueError, QueueError, sqlite3.Error, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

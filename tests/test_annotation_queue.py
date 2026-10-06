import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sqlite3

import pytest

import scripts.annotation_queue as annotation_queue
from scripts.annotation_queue import (
    QueueError,
    advance,
    claim,
    defer_validation,
    init_queue,
    release,
    retry,
    status,
    submit,
)


def _write_json(path: Path, value):
    text = json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return hashlib.sha256(text.encode()).hexdigest()


def _packet(number: int) -> dict:
    return {
        "thread_key": f"owner/repo#{number}:{number * 10}",
        "anchor": {
            "path": "src/main.py",
            "side": "right",
            "from_line": 10,
            "to_line": 10,
            "location_status": "verified",
        },
        "thread": [{"id": number * 10, "body": "Please simplify this."}],
        "neighbor_threads": [],
    }


def _result(packet: dict, input_sha: str, decision="no_issue") -> dict:
    return {
        "thread_key": packet["thread_key"],
        "input_sha256": input_sha,
        "decision": decision,
        "reason": "The discussion does not establish a concrete issue.",
        "evidence_comment_ids": [packet["thread"][0]["id"]],
        "issues": [],
    }


def _prepare(tmp_path: Path, count=1, *, write_results=None, bad_hash=None):
    write_results = set(write_results or ())
    tasks = []
    packets = {}
    for number in range(1, count + 1):
        packet = _packet(number)
        input_file = f"inputs/{number:04d}.json"
        input_sha = _write_json(tmp_path / input_file, packet)
        packets[input_file] = (packet, input_sha)
        tasks.append({
            "thread_key": packet["thread_key"],
            "input_file": input_file,
            "input_sha256": bad_hash if bad_hash is not None else input_sha,
            "stratum": "full",
            "worker_id": number,
        })
        if number in write_results:
            _write_json(
                tmp_path / "results" / Path(input_file).name,
                _result(packet, input_sha),
            )
    _write_json(tmp_path / "manifest.json", {"tasks": tasks})
    return packets, tasks


def test_init_reuses_valid_results_and_keeps_missing_separate(tmp_path):
    _prepare(tmp_path, count=2, write_results={1})

    imported = init_queue(tmp_path)

    assert imported["complete"] == 1
    assert imported["pending"] == 1
    assert imported["decision_counts"] == {
        "candidate_issue": 0,
        "needs_context": 0,
        "no_issue": 1,
    }
    assert not (tmp_path / "state.sqlite3").exists()
    with sqlite3.connect(tmp_path / "queue.sqlite3") as db:
        rows = db.execute("SELECT state, decision FROM tasks ORDER BY id").fetchall()
    assert rows == [("complete", "no_issue"), ("pending", None)]


def test_default_init_moves_lost_complete_result_back_to_pending(tmp_path):
    _prepare(tmp_path, write_results={1})
    init_queue(tmp_path)
    (tmp_path / "results" / "0001.json").unlink()

    imported = init_queue(tmp_path)

    assert imported["complete"] == 0
    assert imported["pending"] == 1
    with sqlite3.connect(tmp_path / "queue.sqlite3") as db:
        assert db.execute("SELECT error FROM tasks").fetchone() == ("result_missing",)


def test_incremental_preserves_running_task_and_imports_new_task(tmp_path):
    _prepare(tmp_path)
    init_queue(tmp_path)
    original = claim(tmp_path, "worker-a")[0]

    packet = _packet(2)
    input_file = "inputs/0002.json"
    input_sha = _write_json(tmp_path / input_file, packet)
    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    manifest["tasks"].append({
        "thread_key": packet["thread_key"],
        "input_file": input_file,
        "input_sha256": input_sha,
        "stratum": "full",
        "worker_id": 2,
    })
    _write_json(tmp_path / "manifest.json", manifest)
    (tmp_path / original["input_file"]).unlink()

    imported = init_queue(tmp_path, incremental=True)

    assert imported["running"] == 1
    assert imported["pending"] == 1
    with sqlite3.connect(tmp_path / "queue.sqlite3") as db:
        row = db.execute(
            "SELECT state, worker, attempts FROM tasks WHERE thread_key=?",
            (original["thread_key"],),
        ).fetchone()
    assert row == ("running", "worker-a", 1)


def test_incremental_rejects_changed_input_hash(tmp_path):
    packets, _ = _prepare(tmp_path)
    expected_hash = packets["inputs/0001.json"][1]
    init_queue(tmp_path)
    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    manifest["tasks"][0]["input_sha256"] = "0" * 64
    _write_json(tmp_path / "manifest.json", manifest)

    with pytest.raises(ValueError, match="changed input path/hash"):
        init_queue(tmp_path, incremental=True)
    with sqlite3.connect(tmp_path / "queue.sqlite3") as db:
        assert db.execute("SELECT input_sha256, state FROM tasks").fetchone() == (
            expected_hash,
            "pending",
        )


def test_concurrent_claims_do_not_duplicate_tasks(tmp_path):
    _prepare(tmp_path, count=8)
    init_queue(tmp_path)

    def take(worker):
        return claim(tmp_path, worker, limit=4)

    with ThreadPoolExecutor(max_workers=2) as pool:
        batches = list(pool.map(take, ("worker-a", "worker-b")))
    claimed = [task for batch in batches for task in batch]

    assert len(claimed) == 8
    assert len({task["thread_key"] for task in claimed}) == 8
    assert all(Path(task["input_path"]).is_file() for task in claimed)
    assert all(Path(task["output_path"]).parent.name == "results" for task in claimed)
    assert status(tmp_path)["running"] == 8


def test_same_worker_gets_existing_running_tasks_before_new_work(tmp_path):
    _prepare(tmp_path, count=3)
    init_queue(tmp_path)

    first = claim(tmp_path, "worker-a", limit=2)
    again = claim(tmp_path, "worker-a", limit=2)

    assert [task["thread_key"] for task in again] == [
        task["thread_key"] for task in first
    ]
    assert status(tmp_path)["pending"] == 1


def test_invalid_result_fails_then_retry_preserves_attempts(tmp_path):
    packets, _ = _prepare(tmp_path)
    init_queue(tmp_path)
    task = claim(tmp_path, "worker-a")[0]
    packet, input_sha = packets[task["input_file"]]
    invalid = _result(packet, "0" * 64)
    _write_json(tmp_path / "results" / Path(task["input_file"]).name, invalid)

    failed = submit(tmp_path, "worker-a", task["input_file"])

    assert failed["state"] == "failed"
    assert "input_sha256_mismatch" in failed["error"]
    assert failed["attempts"] == 1
    assert retry(tmp_path) == 1
    pending = claim(tmp_path, "worker-b")[0]
    assert pending["attempts"] == 2
    _write_json(
        tmp_path / "results" / Path(pending["input_file"]).name,
        _result(packet, input_sha),
    )
    complete = submit(tmp_path, "worker-b", pending["input_file"])
    assert complete["state"] == "complete"
    assert status(tmp_path)["complete"] == 1


def test_manifest_input_hash_mismatch_never_becomes_complete(tmp_path):
    _prepare(tmp_path, bad_hash="0" * 64)
    imported = init_queue(tmp_path)
    assert imported["pending"] == 1
    task = claim(tmp_path, "worker-a")[0]
    packet = _packet(1)
    _write_json(
        tmp_path / "results" / Path(task["input_file"]).name,
        _result(packet, "0" * 64),
    )

    failed = submit(tmp_path, "worker-a", task["input_file"])

    assert failed["state"] == "failed"
    assert "input_sha256_mismatch_manifest" in failed["error"]
    assert status(tmp_path)["complete"] == 0


def test_release_reconciles_result_written_before_submit(tmp_path):
    packets, _ = _prepare(tmp_path)
    init_queue(tmp_path)
    task = claim(tmp_path, "worker-a")[0]
    packet, input_sha = packets[task["input_file"]]
    _write_json(
        tmp_path / "results" / Path(task["input_file"]).name,
        _result(packet, input_sha),
    )

    assert release(tmp_path, "worker-a") == 0
    assert status(tmp_path)["complete"] == 1


def test_expired_running_is_retried_but_complete_is_not_retried(tmp_path):
    _prepare(tmp_path, count=2)
    init_queue(tmp_path)
    claimed = claim(tmp_path, "worker-a", limit=2)
    running, complete_candidate = claimed
    connection = sqlite3.connect(tmp_path / "queue.sqlite3")
    connection.execute(
        "UPDATE tasks SET lease_until=? WHERE input_file=?",
        (0, running["input_file"]),
    )
    connection.commit()
    connection.close()

    # A valid completion remains complete even when another task expires.
    packet, input_sha = _packet(2), None
    input_sha = hashlib.sha256(
        (tmp_path / complete_candidate["input_file"]).read_bytes()
    ).hexdigest()
    _write_json(
        tmp_path / "results" / Path(complete_candidate["input_file"]).name,
        _result(packet, input_sha),
    )
    assert retry(tmp_path) == 1
    counts = status(tmp_path)
    assert counts["pending"] == 1
    assert counts["complete"] == 1
    assert retry(tmp_path) == 0


def test_deferred_inspection_skips_input_and_result_validation(tmp_path, monkeypatch):
    _prepare(tmp_path)
    (tmp_path / "validation-deferred").touch()
    result_path = tmp_path / "results" / "0001.json"
    result_path.parent.mkdir()
    result_path.write_text("not json", encoding="utf-8")

    monkeypatch.setattr(
        annotation_queue,
        "_sha256",
        lambda _: pytest.fail("deferred inspection read the input"),
    )
    monkeypatch.setattr(
        annotation_queue,
        "validate_result",
        lambda *args: pytest.fail("deferred inspection validated the result"),
    )

    imported = init_queue(tmp_path)

    assert imported["complete"] == 1
    assert imported["validation_deferred"] is True
    assert imported["unvalidated_output_count"] == 1
    assert imported["decision_counts"] == {
        "candidate_issue": 0,
        "needs_context": 0,
        "no_issue": 0,
    }


def test_deferred_missing_output_still_fails(tmp_path):
    _prepare(tmp_path)
    init_queue(tmp_path)
    task = claim(tmp_path, "worker-a", limit=1)[0]
    (tmp_path / "validation-deferred").touch()

    failed = submit(tmp_path, "worker-a", task["input_file"])

    assert failed["state"] == "failed"
    assert failed["error"] == "result_missing"
    assert status(tmp_path)["failed"] == 1


def test_defer_validation_reconciles_failed_without_touching_live_running(tmp_path):
    _prepare(tmp_path, count=2)
    init_queue(tmp_path)
    claimed = claim(tmp_path, "worker-a", limit=2)
    failed_task, live_task = claimed
    result_dir = tmp_path / "results"
    result_dir.mkdir()
    (result_dir / Path(failed_task["input_file"]).name).write_text(
        "not json", encoding="utf-8"
    )
    (result_dir / Path(live_task["input_file"]).name).write_text(
        "also not json", encoding="utf-8"
    )

    failed = submit(tmp_path, "worker-a", failed_task["input_file"])
    assert failed["state"] == "failed"

    assert defer_validation(tmp_path) == 1
    with sqlite3.connect(tmp_path / "queue.sqlite3") as db:
        rows = db.execute(
            "SELECT input_file, state, decision FROM tasks ORDER BY id"
        ).fetchall()
    assert rows == [
        (failed_task["input_file"], "complete", None),
        (live_task["input_file"], "running", None),
    ]


def test_advance_submits_before_claiming_and_stops_on_failure(tmp_path, monkeypatch):
    events = []
    next_task = {"input_file": "inputs/0002.json"}

    def fake_submit(run_dir, worker, input_file):
        events.append(("submit", input_file))
        return {"state": "complete"}

    def fake_claim(run_dir, worker, limit):
        events.append(("claim", limit))
        return [next_task]

    monkeypatch.setattr(annotation_queue, "submit", fake_submit)
    monkeypatch.setattr(annotation_queue, "claim", fake_claim)

    assert advance(tmp_path, "worker-a", "inputs/0001.json") == next_task
    assert events == [
        ("submit", "inputs/0001.json"),
        ("claim", 1),
    ]

    events.clear()

    def failed_submit(run_dir, worker, input_file):
        events.append(("submit", input_file))
        return {"state": "failed", "error": "result_missing"}

    monkeypatch.setattr(annotation_queue, "submit", failed_submit)
    with pytest.raises(QueueError, match="result_missing"):
        advance(tmp_path, "worker-a", "inputs/0001.json")
    assert events == [("submit", "inputs/0001.json")]

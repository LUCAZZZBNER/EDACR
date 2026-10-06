"""Validate model thread annotations and assemble the pilot JSONL outputs.

The model workers write one JSON result beside each prepared input.  This
script is deliberately an offline bookkeeping step: it reads those files,
validates their references and locations, and atomically replaces the
aggregate files in the run directory.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any

try:
    from scripts.annotation_manifest import validate_manifest_tasks
except ModuleNotFoundError:  # Direct execution: python scripts/assemble_thread_annotations.py
    from annotation_manifest import validate_manifest_tasks


DECISIONS = {"candidate_issue", "no_issue", "needs_context"}
CATEGORIES = {"code_defect", "security", "performance", "maintainability_readability"}
GROUPS = ("random", "challenge")
MODEL = "gpt-5.6-luna"
REASONING = "max"
RESULT_FIELDS = {"thread_key", "input_sha256", "decision", "reason", "evidence_comment_ids", "issues"}
ISSUE_FIELDS = {"summary", "category", "evidence_comment_ids", "path", "side", "from_line", "to_line"}


def _same_json_value(left: Any, right: Any) -> bool:
    """Compare JSON scalar IDs without treating true as the integer 1."""

    return type(left) is type(right) and left == right


def _contains_id(value: Any, values: list[Any]) -> bool:
    return any(_same_json_value(value, candidate) for candidate in values)


def _nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _atomic_text(path: Path, text: str) -> None:
    """Replace *path* atomically, keeping the temporary file in its directory."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="\n", dir=path.parent, prefix=f".{path.name}.",
            suffix=".tmp", delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def _atomic_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    text = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows)
    _atomic_text(path, text)


def _atomic_json(path: Path, value: Any) -> None:
    _atomic_text(path, json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n")


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _input_comment_ids(packet: Any) -> tuple[list[Any], list[Any]]:
    """Return (current-thread IDs, all available IDs) from an input packet."""

    current: list[Any] = []
    if isinstance(packet, dict) and isinstance(packet.get("thread"), list):
        for comment in packet["thread"]:
            if isinstance(comment, dict) and "id" in comment:
                current.append(comment["id"])

    all_ids = list(current)
    neighbors = packet.get("neighbor_threads", []) if isinstance(packet, dict) else []
    if isinstance(neighbors, list):
        for neighbor in neighbors:
            if not isinstance(neighbor, dict):
                continue
            if "root_id" in neighbor:
                all_ids.append(neighbor["root_id"])
            comments = neighbor.get("comments", [])
            if isinstance(comments, list):
                for comment in comments:
                    if isinstance(comment, dict) and "id" in comment:
                        all_ids.append(comment["id"])
    return current, all_ids


def _validate_ids(
    value: Any,
    current_ids: list[Any],
    all_ids: list[Any],
    prefix: str,
) -> list[str]:
    errors: list[str] = []
    if not isinstance(value, list):
        return [f"{prefix}_not_list"]
    if any(not _contains_id(comment_id, all_ids) for comment_id in value):
        errors.append(f"{prefix}_unknown")
    if not any(_contains_id(comment_id, current_ids) for comment_id in value):
        errors.append(f"{prefix}_missing_current_thread")
    return errors


def _validate_location(issue: Any, anchor: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(anchor, dict):
        return ["input_anchor_missing"]
    if not isinstance(issue, dict):
        return ["issue_not_object"]

    required = ("path", "side", "from_line", "to_line")
    if any(key not in issue for key in required):
        errors.append("issue_anchor_fields_missing")

    issue_from = issue.get("from_line")
    issue_to = issue.get("to_line")
    anchor_from = anchor.get("from_line")
    anchor_to = anchor.get("to_line")
    if isinstance(issue_from, bool) or isinstance(issue_to, bool):
        errors.append("issue_line_bool")
    if (issue_from is None) != (issue_to is None):
        errors.append("issue_line_pair_empty")
    if (anchor_from is None) != (anchor_to is None):
        errors.append("input_line_pair_empty")
    if issue_from is not None and not isinstance(issue_from, int):
        errors.append("issue_line_not_integer")
    if issue_to is not None and not isinstance(issue_to, int):
        errors.append("issue_line_not_integer")
    if not all(
        _same_json_value(issue.get(key), anchor.get(key)) for key in required
    ):
        errors.append("issue_anchor_mismatch")
    return errors


def validate_result(result: Any, packet: Any, task: dict[str, Any], actual_sha256: str) -> list[str]:
    """Return all structural validation error codes for one model result."""

    errors: list[str] = []
    if not isinstance(result, dict):
        return ["result_not_object"]
    if set(result) - RESULT_FIELDS:
        errors.append("result_unknown_fields")
    expected_key = task.get("thread_key")
    if result.get("thread_key") != expected_key:
        errors.append("thread_key_mismatch")
    if not isinstance(packet, dict) or packet.get("thread_key") != expected_key:
        errors.append("input_thread_key_mismatch")
    if result.get("input_sha256") != actual_sha256 or result.get("input_sha256") != task.get("input_sha256"):
        errors.append("input_sha256_mismatch")

    decision = result.get("decision")
    if not isinstance(decision, str) or decision not in DECISIONS:
        errors.append("decision_invalid")
    if not _nonempty_string(result.get("reason")):
        errors.append("reason_empty")

    current_ids, all_ids = _input_comment_ids(packet)
    errors.extend(_validate_ids(result.get("evidence_comment_ids"), current_ids, all_ids, "evidence"))

    issues = result.get("issues")
    if not isinstance(issues, list):
        errors.append("issues_not_list")
        issues = []
    if decision == "candidate_issue" and not issues:
        errors.append("candidate_without_issue")
    if isinstance(decision, str) and decision in {"no_issue", "needs_context"} and issues:
        errors.append("non_candidate_with_issues")

    anchor = packet.get("anchor") if isinstance(packet, dict) else None
    for issue in issues:
        if not isinstance(issue, dict):
            errors.append("issue_not_object")
            continue
        if set(issue) - ISSUE_FIELDS:
            errors.append("issue_unknown_fields")
        if not _nonempty_string(issue.get("summary")):
            errors.append("issue_summary_empty")
        if not isinstance(issue.get("category"), str) or issue["category"] not in CATEGORIES:
            errors.append("issue_category_invalid")
        errors.extend(_validate_ids(
            issue.get("evidence_comment_ids"), current_ids, all_ids, "issue_evidence"
        ))
        errors.extend(_validate_location(issue, anchor))
    return errors


def _group_for(task: dict[str, Any]) -> str:
    if task.get("stratum") == "full":
        return "full"
    return "random" if task.get("stratum") == "random" else "challenge"


def _new_group() -> dict[str, Any]:
    return {
        "task_count": 0,
        "valid_output_count": 0,
        "missing_count": 0,
        "invalid_count": 0,
        "decision_counts": {decision: 0 for decision in sorted(DECISIONS)},
        "issue_count": 0,
        "verified_issue_count": 0,
        "validity_errors": {},
        "validity_error_count": 0,
        "human_verified": False,
        "classification_not_gold_standard": True,
        "classification_disagreements": None,
    }


def _record_errors(group: dict[str, Any], errors: list[str]) -> None:
    counts = Counter(group["validity_errors"])
    counts.update(errors)
    group["validity_errors"] = dict(sorted(counts.items()))
    group["validity_error_count"] += len(errors)


def _provenance(task: dict[str, Any], packet: dict[str, Any]) -> dict[str, Any]:
    anchor = packet.get("anchor") if isinstance(packet, dict) else {}
    return {
        "model": MODEL,
        "reasoning": REASONING,
        "stratum": task.get("stratum"),
        "location_status": anchor.get("location_status") if isinstance(anchor, dict) else None,
        "input_file": task.get("input_file"),
    }


def _needs_review_row(
    kind: str,
    task: dict[str, Any],
    *,
    result: dict[str, Any] | None = None,
    errors: list[str] | None = None,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "type": kind,
        "thread_key": task.get("thread_key"),
        "input_file": task.get("input_file"),
    }
    if result is not None:
        row.update({
            "decision": result.get("decision"),
            "reason": result.get("reason"),
            "evidence_comment_ids": result.get("evidence_comment_ids"),
            "issues": result.get("issues", []),
        })
    if errors is not None:
        row["errors"] = errors
    return row


def assemble(run_dir: Path | str) -> dict[str, Any]:
    """Validate all manifest tasks and atomically write the four aggregates."""

    run_dir = Path(run_dir)
    manifest_path = run_dir / "manifest.json"
    manifest = _load_json(manifest_path)
    tasks = validate_manifest_tasks(manifest)

    assessments: list[dict[str, Any]] = []
    candidate_rows: list[dict[str, Any]] = []
    review_rows: list[dict[str, Any]] = []
    groups = {name: _new_group() for name in GROUPS}
    if any(task.get('stratum') == 'full' for task in tasks):
        groups['full'] = _new_group()

    for task_value in tasks:
        if not isinstance(task_value, dict):
            task = {}
            group = groups["challenge"]
            group["task_count"] += 1
            group["invalid_count"] += 1
            _record_errors(group, ["task_not_object"])
            review_rows.append(_needs_review_row("invalid", task, errors=["task_not_object"]))
            continue

        task = task_value
        group = groups[_group_for(task)]
        group["task_count"] += 1
        input_file = task.get("input_file")
        if not isinstance(input_file, str) or not input_file:
            errors = ["input_file_missing"]
            group["invalid_count"] += 1
            _record_errors(group, errors)
            review_rows.append(_needs_review_row("invalid", task, errors=errors))
            continue

        input_path = run_dir / input_file
        result_path = run_dir / "results" / Path(input_file).name
        if not input_path.is_file():
            errors = ["input_missing"]
            group["missing_count"] += 1
            review_rows.append(_needs_review_row("missing", task, errors=errors))
            continue

        actual_sha256 = _sha256(input_path)
        if actual_sha256 != task.get("input_sha256"):
            errors = ["input_sha256_mismatch_manifest"]
            group["invalid_count"] += 1
            _record_errors(group, errors)
            review_rows.append(_needs_review_row("invalid", task, errors=errors))
            continue

        try:
            packet = _load_json(input_path)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            errors = ["input_invalid_json"]
            group["invalid_count"] += 1
            _record_errors(group, errors)
            review_rows.append(_needs_review_row("invalid", task, errors=errors))
            continue

        if not result_path.is_file():
            errors = ["result_missing"]
            group["missing_count"] += 1
            review_rows.append(_needs_review_row("missing", task, errors=errors))
            continue

        try:
            result = _load_json(result_path)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            errors = ["result_invalid_json"]
            group["invalid_count"] += 1
            _record_errors(group, errors)
            review_rows.append(_needs_review_row("invalid", task, errors=errors))
            continue

        errors = validate_result(result, packet, task, actual_sha256)
        if errors:
            errors = sorted(set(errors))
            group["invalid_count"] += 1
            _record_errors(group, errors)
            review_rows.append(_needs_review_row("invalid", task, result=result if isinstance(result, dict) else None,
                                                 errors=errors))
            continue

        group["valid_output_count"] += 1
        decision = result["decision"]
        group["decision_counts"][decision] += 1
        if decision == "candidate_issue":
            group["issue_count"] += len(result["issues"])
            location_status = packet.get("anchor", {}).get("location_status")
            if location_status == "verified":
                group["verified_issue_count"] += len(result["issues"])
                pr = packet.get("pr", {}) if isinstance(packet.get("pr"), dict) else {}
                for issue in result["issues"]:
                    row = dict(issue)
                    row.update({
                        "thread_key": result["thread_key"],
                        "input_file": task["input_file"],
                        "githubPrUrl": pr.get("githubPrUrl"),
                        "source_commit": pr.get("source_commit"),
                        "target_commit": pr.get("target_commit"),
                        "pr": {
                            "githubPrUrl": pr.get("githubPrUrl"),
                            "source_commit": pr.get("source_commit"),
                            "target_commit": pr.get("target_commit"),
                        },
                        "issue": dict(issue),
                    })
                    candidate_rows.append(row)
            else:
                review_rows.append(_needs_review_row("unlocated_candidate", task, result=result))
        elif decision == "needs_context":
            review_rows.append(_needs_review_row("needs_context", task, result=result))

        assessment = dict(result)
        assessment["provenance"] = _provenance(task, packet)
        assessments.append(assessment)

    report: dict[str, Any] = {
        "model": MODEL,
        "reasoning": REASONING,
        "human_verified": False,
        "classification_not_gold_standard": True,
        "classification_disagreements": None,
        "random": groups["random"],
        "challenge": groups["challenge"],
        "groups": groups,
        "total": {
            "task_count": sum(group["task_count"] for group in groups.values()),
            "valid_output_count": sum(group["valid_output_count"] for group in groups.values()),
            "missing_count": sum(group["missing_count"] for group in groups.values()),
            "invalid_count": sum(group["invalid_count"] for group in groups.values()),
            "issue_count": sum(group["issue_count"] for group in groups.values()),
            "verified_issue_count": sum(group["verified_issue_count"] for group in groups.values()),
        },
    }
    if 'full' in groups:
        report['full'] = groups['full']
        report['expected_task_count'] = manifest.get('population_threads', len(tasks))
        report['input_preparation_complete'] = manifest.get('status') == 'complete'
        report['classification_complete'] = (
            report['input_preparation_complete']
            and report['total']['valid_output_count'] == report['expected_task_count']
            and report['total']['missing_count'] == 0
            and report['total']['invalid_count'] == 0
        )
    _atomic_jsonl(run_dir / "thread_assessments.jsonl", assessments)
    _atomic_jsonl(run_dir / "candidate_issues.jsonl", candidate_rows)
    _atomic_jsonl(run_dir / "needs_review.jsonl", review_rows)
    _atomic_json(run_dir / "report.json", report)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        report = assemble(args.run_dir)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    print(json.dumps(report["total"], ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

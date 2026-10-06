import hashlib
import json
from pathlib import Path

from scripts.assemble_thread_annotations import assemble


def _write_json(path: Path, value):
    text = json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return hashlib.sha256(text.encode()).hexdigest()


def _packet(thread_key="owner/repo#1:10", *, location_status="verified"):
    return {
        "thread_key": thread_key,
        "pr": {
            "githubPrUrl": "https://github.com/owner/repo/pull/1",
            "source_commit": "source",
            "target_commit": "target",
        },
        "anchor": {
            "path": "src/main.py",
            "side": "right",
            "from_line": 10,
            "to_line": 10,
            "location_status": location_status,
        },
        "thread": [{"id": 10, "body": "Please simplify this."}],
        "neighbor_threads": [{"root_id": 20, "comments": [{"id": 21, "body": "Neighbor"}]}],
    }


def _result(packet, *, decision="candidate_issue", evidence=None, issues=None, input_sha256=None):
    return {
        "thread_key": packet["thread_key"],
        "input_sha256": input_sha256,
        "decision": decision,
        "reason": "The thread contains a concrete review request.",
        "evidence_comment_ids": [10] if evidence is None else evidence,
        "issues": ([{
            "summary": "The implementation is harder to read than necessary.",
            "category": "maintainability_readability",
            "evidence_comment_ids": [10],
            "path": packet["anchor"]["path"],
            "side": packet["anchor"]["side"],
            "from_line": packet["anchor"]["from_line"],
            "to_line": packet["anchor"]["to_line"],
        }] if issues is None and decision == "candidate_issue" else (issues or [])),
    }


def _run(tmp_path, specs):
    tasks = []
    for ordinal, spec in enumerate(specs, 1):
        packet = spec.get("packet", _packet(f"owner/repo#{ordinal}:{ordinal * 10}"))
        input_file = f"inputs/{ordinal:04d}.json"
        input_sha = _write_json(tmp_path / input_file, packet)
        task = {
            "thread_key": packet["thread_key"],
            "input_file": input_file,
            "input_sha256": spec.get("manifest_sha", input_sha),
            "stratum": spec.get("stratum", "random"),
            "challenge": spec.get("challenge"),
            "worker_id": 1,
        }
        tasks.append(task)
        if spec.get("result", True) is not None:
            result = spec["result"]
            if result is True:
                result = _result(packet, input_sha256=input_sha)
            elif isinstance(result, dict) and result.get("input_sha256") is None:
                result = {**result, "input_sha256": input_sha}
            _write_json(tmp_path / "results" / Path(input_file).name, result)
    _write_json(tmp_path / "manifest.json", {"tasks": tasks})
    return assemble(tmp_path)


def _jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def test_unknown_evidence_and_fabricated_line_are_invalid(tmp_path):
    packet = _packet()
    result = _result(packet, evidence=[999])
    result["issues"][0]["from_line"] = 999
    report = _run(tmp_path, [{"packet": packet, "result": result}])

    assert report["random"]["valid_output_count"] == 0
    assert report["random"]["decision_counts"]["no_issue"] == 0
    review = _jsonl(tmp_path / "needs_review.jsonl")
    assert review[0]["type"] == "invalid"
    assert "evidence_unknown" in review[0]["errors"]
    assert "issue_anchor_mismatch" in review[0]["errors"]
    assert _jsonl(tmp_path / "thread_assessments.jsonl") == []
    assert _jsonl(tmp_path / "candidate_issues.jsonl") == []


def test_manifest_hash_mismatch_is_invalid_and_not_no_issue(tmp_path):
    packet = _packet()
    report = _run(tmp_path, [{"packet": packet, "manifest_sha": "0" * 64, "result": True}])

    assert report["random"]["invalid_count"] == 1
    assert report["random"]["missing_count"] == 0
    assert report["random"]["decision_counts"]["no_issue"] == 0
    review = _jsonl(tmp_path / "needs_review.jsonl")
    assert review == [{
        "errors": ["input_sha256_mismatch_manifest"],
        "input_file": "inputs/0001.json",
        "thread_key": packet["thread_key"],
        "type": "invalid",
    }]


def test_needs_context_with_empty_issues_is_valid_review(tmp_path):
    packet = _packet()
    result = _result(packet, decision="needs_context", issues=[])
    report = _run(tmp_path, [{"packet": packet, "result": result}])

    assert report["random"]["valid_output_count"] == 1
    assert report["random"]["decision_counts"] == {
        "candidate_issue": 0,
        "needs_context": 1,
        "no_issue": 0,
    }
    assert len(_jsonl(tmp_path / "thread_assessments.jsonl")) == 1
    review = _jsonl(tmp_path / "needs_review.jsonl")
    assert review[0]["type"] == "needs_context"
    assert review[0]["issues"] == []


def test_missing_result_is_separate_from_no_issue(tmp_path):
    packet = _packet()
    report = _run(tmp_path, [{"packet": packet, "result": None}])

    assert report["random"]["missing_count"] == 1
    assert report["random"]["invalid_count"] == 0
    assert report["random"]["decision_counts"]["no_issue"] == 0
    assert _jsonl(tmp_path / "needs_review.jsonl")[0]["type"] == "missing"


def test_full_population_is_not_reported_as_challenge_sample(tmp_path):
    report = _run(tmp_path, [{'packet': _packet(), 'stratum': 'full', 'result': True}])
    assert report['full']['task_count'] == 1
    assert report['full']['decision_counts']['candidate_issue'] == 1
    assert report['challenge']['task_count'] == 0
    assert report['random']['task_count'] == 0
    assert report['total']['task_count'] == 1
    assert report['classification_complete'] is False
    manifest_path = tmp_path / 'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    manifest.update(status='in_progress', population_threads=2)
    _write_json(manifest_path, manifest)
    report = assemble(tmp_path)
    assert report['expected_task_count'] == 2
    assert report['classification_complete'] is False
    manifest.update(status='complete', population_threads=1)
    _write_json(manifest_path, manifest)
    assert assemble(tmp_path)['classification_complete'] is True


def test_malformed_model_enum_does_not_abort_other_tasks(tmp_path):
    packet = _packet()
    invalid = _result(packet)
    invalid['decision'] = ['candidate_issue']
    invalid['issues'][0]['category'] = {'name': 'code_defect'}
    report = _run(tmp_path, [
        {'packet': packet, 'result': invalid},
        {'packet': _packet('owner/repo#2:10'), 'result': True},
    ])
    assert report['total']['invalid_count'] == 1
    assert report['total']['valid_output_count'] == 1
    assert report['classification_disagreements'] is None


def test_group_statistics_and_only_verified_candidates_are_exported(tmp_path):
    unlocated = _packet("owner/repo#2:20", location_status="missing_reliable_original_anchor")
    verified = _packet("owner/repo#3:30", location_status="verified")
    report = _run(tmp_path, [
        {"packet": _packet("owner/repo#1:10"), "stratum": "random", "result": _result(
            _packet("owner/repo#1:10"), decision="no_issue", issues=[]
        )},
        {"packet": unlocated, "stratum": "challenge", "challenge": "unlocated", "result": _result(
            unlocated, input_sha256=None
        )},
        {"packet": verified, "stratum": "challenge", "challenge": "short_reply", "result": True},
    ])

    assert report["random"]["decision_counts"]["no_issue"] == 1
    assert report["challenge"]["decision_counts"]["candidate_issue"] == 2
    assert report["challenge"]["issue_count"] == 2
    assert report["challenge"]["verified_issue_count"] == 1
    candidates = _jsonl(tmp_path / "candidate_issues.jsonl")
    assert len(candidates) == 1
    assert candidates[0]["thread_key"] == verified["thread_key"]
    review_types = {row["type"] for row in _jsonl(tmp_path / "needs_review.jsonl")}
    assert "unlocated_candidate" in review_types

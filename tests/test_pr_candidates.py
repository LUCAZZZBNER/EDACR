import copy
import hashlib
import json
from pathlib import Path

import pytest

from scripts.build_pr_candidates import aggregate, build, statistics


def sample(number, threads, *, repo='owner/repo', loc=50):
    comments = []
    for root, path, located in threads:
        comments.append({'path': path, 'side': 'right', 'from_line': 10 if located else None,
                         'to_line': 10 if located else None,
                         'metadata': {'thread_root_id': root, 'comment_id': root,
                                      'location_status': 'verified' if located else 'missing_original_hunk'}})
    return {'githubPrUrl': f'https://github.com/{repo}/pull/{number}',
            'source_commit': f'source-{number}', 'target_commit': f'target-{number}',
            'project_main_language': 'C++', 'comments': comments,
            'metadata': {'repository': repo, 'number': number, 'title': 'Example',
                         'closed_at': '2026-01-01', 'merged_at': None,
                         'statistics': {'changed_loc': loc, 'changed_files': 2, 'hunks': 3},
                         'diff_path': f'diffs/{number}.diff', 'diff_sha256': 'diff-hash'}}


def assessment(pr, root, decision='candidate_issue', *, multiple=False):
    comment = next(c for c in pr['comments'] if c['metadata']['thread_root_id'] == root)
    issue = {k: comment[k] for k in ('path', 'side', 'from_line', 'to_line')}
    issue.update(summary='A supported suggestion', category='maintainability_readability', evidence_comment_ids=[root])
    return {'thread_key': f"{pr['metadata']['repository']}#{pr['metadata']['number']}:{root}",
            'input_sha256': f'input-{root}', 'decision': decision, 'reason': 'Existing assessment',
            'evidence_comment_ids': [root], 'issues': [issue] * (2 if multiple else 1) if decision == 'candidate_issue' else [],
            'provenance': {'input_file': f'inputs/{root}.json', 'location_status': comment['metadata']['location_status'],
                           'model': 'original-model', 'reasoning': 'max'}}


def corpus():
    samples = [sample(1, [(10, 'rtl/a.SV', True), (11, 'rtl/b.sv', False)]),
               sample(2, [(20, 'Makefile', True)], loc=1001),
               sample(3, [(30, 'file.cpp', True)], loc=0)]
    assessments = [assessment(samples[0], 10, multiple=True), assessment(samples[0], 11),
                   assessment(samples[1], 20, 'needs_context'), assessment(samples[2], 30, 'no_issue')]
    return samples, assessments


def test_preserves_zero_candidate_prs_multiple_issues_and_unlocated_evidence():
    samples, assessments = corpus()
    original = copy.deepcopy((samples, assessments))
    rows = aggregate(samples, assessments, {assessments[0]['thread_key']: {'actor': 'repair actor'}})
    assert len(rows) == 3
    assert [r['candidate_issue_count'] for r in rows] == [3, 0, 0]
    assert [r['located_candidate_issue_count'] for r in rows] == [2, 0, 0]
    assert rows[0]['threads'][0]['annotation_repair']['actor'] == 'repair actor'
    assert rows[0]['threads'][0]['issues'][0]['issue_id'] != rows[0]['threads'][0]['issues'][1]['issue_id']
    assert rows[0]['threads'][1]['issues'][0]['from_line'] is None
    assert rows[0]['threads'][1]['original_comment_ids'] == [11]
    assert rows[0]['threads'][1]['issues'][0]['evidence_comment_ids'] == [11]
    assert rows[0]['source_commit'] == 'source-1'
    assert (samples, assessments) == original


def test_statistics_use_issue_extension_and_unique_pr_counts():
    samples, assessments = corpus()
    stats = statistics(aggregate(samples, assessments))
    assert stats['totals']['pr_count'] == 3
    assert stats['totals']['candidate_pr_count'] == 1
    assert stats['distributions']['file_extension']['.sv'] == {
        'candidate_issue_count': 3, 'located_candidate_issue_count': 2, 'unlocated_candidate_issue_count': 1,
        'candidate_pr_count': 1, 'located_candidate_pr_count': 1}
    assert stats['distributions']['project_main_language']['C++']['pr_count'] == 3
    assert set(stats['distributions']['changed_loc']) == {'0', '1-50', '1001+'}
    assert stats['issues_per_pr']['candidate_issue_count']['exact'] == {0: 2, 3: 1}
    assert stats['issues_per_pr']['located_candidate_issue_count']['binned'] == {'0': 2, '2-5': 1}
    assert stats['numeric_summaries_all_prs']['candidate_issue_count']['median'] == 0


@pytest.mark.parametrize('failure', ['duplicate_assessment', 'missing', 'orphan', 'duplicate_pr', 'anchor'])
def test_rejects_silent_join_errors(failure):
    samples, assessments = corpus()
    if failure == 'duplicate_assessment':
        assessments.append(copy.deepcopy(assessments[0]))
    elif failure == 'missing':
        assessments.pop()
    elif failure == 'orphan':
        extra = copy.deepcopy(assessments[0]); extra['thread_key'] = 'elsewhere/repo#9:9'; assessments.append(extra)
    elif failure == 'duplicate_pr':
        samples.append(copy.deepcopy(samples[0]))
    else:
        assessments[0]['issues'][0]['from_line'] = 999
    with pytest.raises(ValueError):
        aggregate(samples, assessments)


def prepare_files(tmp_path):
    data, run, output = tmp_path / 'data', tmp_path / 'run', tmp_path / 'output'
    (data / 'dataset').mkdir(parents=True); run.mkdir()
    samples, assessments = corpus()
    sample_path = data / 'dataset/samples.json'
    sample_path.write_text(json.dumps(samples))
    sha = hashlib.sha256(sample_path.read_bytes()).hexdigest()
    (data / 'dataset/manifest.json').write_text(json.dumps({'samples_sha256': sha, 'complete': False}))
    (run / 'manifest.json').write_text(json.dumps({'source_samples_sha256': sha, 'tasks': [
        {'thread_key': a['thread_key'], 'input_sha256': a['input_sha256'], 'input_file': a['provenance']['input_file']}
        for a in assessments]}))
    (run / 'report.json').write_text(json.dumps({'classification_complete': True,
        'total': {'task_count': 4, 'valid_output_count': 4, 'missing_count': 0, 'invalid_count': 0,
                  'issue_count': 3, 'verified_issue_count': 2},
        'full': {'decision_counts': {'candidate_issue': 2, 'needs_context': 1, 'no_issue': 1}}}))
    (run / 'thread_assessments.jsonl').write_text(''.join(json.dumps(a) + '\n' for a in assessments))
    pr = samples[0]
    (run / 'candidate_issues.jsonl').write_text(''.join(json.dumps({
        'thread_key': assessments[0]['thread_key'], 'githubPrUrl': pr['githubPrUrl'],
        'source_commit': pr['source_commit'], 'target_commit': pr['target_commit'], 'issue': issue}) + '\n'
        for issue in assessments[0]['issues']))
    return data, run, output


def test_export_is_repeatable_and_keeps_collection_completeness(tmp_path):
    data, run, output = prepare_files(tmp_path)
    build(data, run, output)
    before = {p.name: p.read_bytes() for p in output.iterdir()}
    build(data, run, output)
    assert before == {p.name: p.read_bytes() for p in output.iterdir()}
    assert json.loads((output / 'manifest.json').read_text())['source_collection_complete'] is False
    assert len((output / 'pr_summary.csv').read_text().splitlines()) == 4


@pytest.mark.parametrize('failure', ['source_hash', 'revision', 'content', 'counts'])
def test_export_refuses_stale_or_inconsistent_sources(tmp_path, failure):
    data, run, output = prepare_files(tmp_path)
    if failure == 'source_hash':
        with (data / 'dataset/samples.json').open('a') as f:
            f.write(' ')
    elif failure == 'counts':
        p = run / 'report.json'; report = json.loads(p.read_text()); report['total']['issue_count'] = 99
        p.write_text(json.dumps(report))
    else:
        p = run / 'candidate_issues.jsonl'; rows = [json.loads(line) for line in p.read_text().splitlines()]
        if failure == 'revision': rows[0]['target_commit'] = 'wrong-revision'
        else: rows[0]['issue']['summary'] = 'different claim'
        p.write_text(''.join(json.dumps(row) + '\n' for row in rows))
    with pytest.raises(ValueError):
        build(data, run, output)
    assert not output.exists()

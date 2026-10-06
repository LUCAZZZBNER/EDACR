import hashlib
import json

from edabench.build import build, construct
from edabench.storage import Store


def seed(tmp_path, filename='rtl/core.sv', size=1002):
    store = Store(tmp_path)
    repo, number = 'owner/repo', 7
    store.meta('input_rows', [{'full_name': repo, 'duplicate': False}])
    store.meta('cutoff', '2025-01-01T00:00:00Z')
    store.meta('excel_sha256', 'fixture')
    store.put('repository', repo, repo, {'language': 'SystemVerilog'})
    store.task('index:' + repo, 'complete')
    store.task(f'pr:{repo}#{number}', 'complete')
    store.task(f'material:{repo}#{number}', 'complete')
    pr = {'title': '格式修改', 'body': 'Keep original language', 'html_url': 'https://github.com/owner/repo/pull/7',
          'closed_at': '2024-01-01T00:00:00Z', 'merged_at': None, 'head': {'sha': 'final'},
          'base': {'sha': 'source'}, 'additions': 9000, 'deletions': 9000}
    store.put('pr', repo, number, pr)
    patch = f'@@ -0,0 +1,{size} @@\n' + '\n'.join('+' + str(n) for n in range(size))
    root = {'id': 1, 'original_commit_id': 'selected', 'created_at': '2024-01-01',
            'path': filename, 'original_line': 1, 'side': 'RIGHT', 'diff_hunk': patch,
            'body': 'Thanks!', 'user': None}
    store.put('inline', repo, number, [root, {**root, 'id': 2, 'in_reply_to_id': 1,
              'original_commit_id': 'reply-sha', 'body': 'OK'},
              {**root, 'id': 3, 'original_commit_id': 'selected', 'original_line': 9999, 'body': 'Unlocatable'}])
    store.put('threads', repo, number, [{'id': 'thread', 'isResolved': True, 'isOutdated': True,
              'comments': [{'databaseId': 1}, {'databaseId': 2}]}])
    store.put('construction', repo, number, {'state': 'ready', 'source': 'source', 'target': 'selected',
              'api_base_sha': 'source', 'candidate_base_sha': 'source', 'baseline_method': 'fixture',
              'diff_key': 'source..selected', 'subsequent_evidence': {'status': 'unavailable', 'reason': 'force_push'}})
    (tmp_path / 'fixture.diff').write_text(patch)
    store.put('diff', repo, 'source..selected', {'complete': True, 'path': 'fixture.diff',
              'sha256': hashlib.sha256(patch.encode()).hexdigest(), 'method': 'fixture',
              'files': [{'filename': filename, 'patch': patch}],
              'statistics': {'changed_loc': size, 'additions': size, 'deletions': 0, 'changed_files': 1, 'hunks': 1}})
    return store


def test_large_pr_selected_revision_schema_and_original_comments(tmp_path):
    store = seed(tmp_path)
    sample, reason, counts = construct(store, 'owner/repo', '7')
    assert reason is None
    assert sample['change_line_count'] == 1002
    assert sample['target_commit'] == 'selected'
    assert sample['metadata']['final_head_sha'] == 'final'
    assert sample['metadata']['title'] == '格式修改'
    assert [c['note'] for c in sample['comments']] == ['Thanks!', 'OK', 'Unlocatable']
    assert sample['comments'][2]['from_line'] is None
    assert sample['comments'][1]['metadata']['original_commit_id'] == 'reply-sha'
    assert sample['comments'][1]['from_line'] == 1
    assert sample['category'] == ''
    assert all(c['category'] == c['context'] == '' for c in sample['comments'])
    assert 'adopted' not in json.dumps(sample)
    assert counts['unlocatable_comments'] == 1


def test_pure_docs_excluded_and_diff_integrity_required(tmp_path):
    store = seed(tmp_path, filename='README.md')
    assert construct(store, 'owner/repo', '7')[1] == 'no_code_changes'
    (tmp_path / 'fixture.diff').write_text('corrupt')
    assert construct(store, 'owner/repo', '7')[1] == 'diff_file_missing_or_corrupt'


def test_offline_build_is_byte_stable(tmp_path, monkeypatch):
    import socket
    monkeypatch.setattr(socket, 'socket', lambda *a, **k: (_ for _ in ()).throw(AssertionError('network forbidden')))
    store = seed(tmp_path)
    assert build(store)['sample_count'] == 1
    files = list((tmp_path / 'dataset').glob('*.json'))
    before = {f.name: f.read_bytes() for f in files}
    build(store)
    assert before == {f.name: f.read_bytes() for f in files}

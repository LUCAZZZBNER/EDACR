import pytest

from edabench.material import validated_files
from edabench.revisions import is_bot, is_code, locate, parse_patch, region_evidence, select_revision

PATCH = '@@ -1,3 +1,4 @@\n keep\n-old\n+new\n+extra\n end'


def comment(id, sha='b', reply=None, user=None, time='2025-01-01T00:00:00Z', **kw):
    return {'id': id, 'original_commit_id': sha, 'in_reply_to_id': reply,
            'user': user, 'created_at': time, 'body': 'Thanks!', **kw}


def test_thread_votes_reply_inheritance_bot_root_and_unknown_identity():
    data = [comment(1, 'a', user={'type': 'Bot'}), comment(2, 'wrong-reply-sha', reply=1),
            comment(3, 'b'), comment(4, 'b', reply=3), comment(5, 'b', reply=3),
            comment(6, 'b', reply=3, user={'login': 'something[bot]'})]
    selected, threads, counts, _ = select_revision(data)
    assert selected == 'a'  # tied independent threads, SHA tie break, regardless of reply count
    assert counts['b']['threads'] == 1
    assert threads[0]['comments'][1]['body'] == 'Thanks!'
    assert not is_bot(comment(7, user={'login': 'robot-helper'}))
    assert not is_bot(comment(8))
    assert select_revision([comment(1, 'b', time='2024'), comment(2, 'a', time='2025')])[0] == 'b'
    assert select_revision([comment(1, reply=99)])[3][0]['reason'] == 'missing_or_cyclic_thread_root'


@pytest.mark.parametrize('side,start,end', [('RIGHT', 2, 3), ('LEFT', 2, 2)])
def test_original_outdated_multiline_and_rename(side, start, end):
    root = comment(1, path='new.py', side=side, start_side=side, original_line=end,
                   original_start_line=start, line=None, diff_hunk=PATCH)
    files = [{'filename': 'new.py', 'previous_filename': 'old.py', 'patch': PATCH}]
    anchor, reason = locate(root, files)
    assert reason is None
    assert anchor['path'] == ('old.py' if side == 'LEFT' else 'new.py')
    assert (anchor['from_line'], anchor['to_line']) == (start, end)


def test_legacy_position_and_bad_hunk():
    file = {'filename': 'x.py', 'patch': PATCH}
    root = comment(1, path='x.py', original_position=3, diff_hunk=PATCH)
    anchor, reason = locate(root, [file])
    assert anchor['side'] == 'right' and anchor['to_line'] == 2
    root['diff_hunk'] = PATCH.replace('new', 'different')
    assert locate(root, [file])[1] == 'original_hunk_conflicts_with_selected_baseline'
    root['original_position'] = 999
    assert locate(root, [file])[1] == 'missing_reliable_original_anchor'
    with pytest.raises(ValueError, match='truncated'):
        parse_patch(PATCH.rsplit('\n', 1)[0])


def test_code_policy():
    for path in ('rtl/core.sv', 'test/x.py', 'build.sbt', 'clock.sdc', 'x.tcl', 'Makefile', '.github/workflows/test.yml'):
        assert is_code(path)
    for path in ('README.md', 'docs/a.rst', 'logo.png', 'paper.pdf'):
        assert not is_code(path)


def test_compare_caps_truncation_and_stats():
    file = {'patch': PATCH, 'additions': 2, 'deletions': 1, 'changes': 3}
    assert validated_files({'files': [file]}) == [file]
    for bad in ({'files': [file] * 300}, {'files': [{}]},
                {'files': [{**file, 'additions': 50}]},
                {'files': [{**file, 'patch': PATCH.rsplit('\n', 1)[0]}]}):
        with pytest.raises(ValueError):
            validated_files(bad)


def test_region_evidence_uses_edits_not_context():
    file = {'filename': 'x.py'}
    later = [{'filename': 'x.py', 'patch': PATCH}]
    assert not region_evidence({'side': 'right', 'from_line': 1, 'to_line': 1}, file, later)['region_modified']
    assert region_evidence({'side': 'right', 'from_line': 2, 'to_line': 2}, file, later)['region_modified']
    assert region_evidence({'side': 'left'}, file, later)['status'] == 'not_assessed'

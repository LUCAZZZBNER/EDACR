import hashlib
import json
import random
import sqlite3
from pathlib import Path

from scripts.prepare_thread_pilot import choose_threads, prepare


def test_uniform_sample_is_distinct_from_targeted_challenges():
    population = []
    for n in range(1000):
        comments = [{
            'note': 'Same as above' if n % 5 == 0 else 'Please explain this.',
            'from_line': None if n % 5 == 1 else 10,
            'to_line': None if n % 5 == 1 else 12,
            'metadata': {'location_status': 'missing_original_hunk' if n % 5 == 1 else 'verified',
                         'in_reply_to_id': 1},
        }] * (4 if n % 5 == 2 else 1)
        population.append((n, n, comments))
    selection = choose_threads(population, 123)
    assert len(selection) == len({i for i, _, _ in selection}) == 200
    assert [i for i, _, _ in selection[:150]] == random.Random(123).sample(range(1000), 150)
    assert all(stratum == 'random' and challenge is None for _, stratum, challenge in selection[:150])
    assert all(stratum == 'challenge' for _, stratum, _ in selection[150:])
    assert selection == choose_threads(population, 123)


def _annotation_fixture(tmp_path):
    data = tmp_path / 'data'
    (data / 'dataset').mkdir(parents=True)
    repo, number = 'owner/repo', 7
    patch = '@@ -1 +1 @@\n-old\n+new\n'
    diff_path = data / 'fixture.diff'
    diff_path.write_text(patch)
    diff_sha256 = hashlib.sha256(patch.encode()).hexdigest()
    comments = []
    for root_id, line in ((101, 1), (102, 2)):
        comments.append({
            'id': root_id, 'original_commit_id': 'selected', 'created_at': '2024-01-01T00:00:00Z',
            'path': 'src/a.sv', 'original_line': line, 'side': 'RIGHT', 'diff_hunk': patch,
            'body': f'question {root_id}', 'user': {'login': 'reviewer', 'type': 'User'},
        })
    inline = comments
    samples_comments = []
    for comment in comments:
        samples_comments.append({
            'note': comment['body'], 'path': comment['path'], 'side': 'right',
            'from_line': comment['original_line'], 'to_line': comment['original_line'],
            'metadata': {
                'thread_root_id': comment['id'], 'location_status': 'verified',
                'in_reply_to_id': None,
            },
        })
    sample = {
        'githubPrUrl': 'https://github.com/owner/repo/pull/7',
        'source_commit': 'source', 'target_commit': 'selected', 'project_main_language': 'SystemVerilog',
        'comments': samples_comments,
        'metadata': {
            'repository': repo, 'number': number, 'title': 'fixture', 'body': 'body',
            'diff_sha256': diff_sha256,
        },
    }
    (data / 'dataset/samples.json').write_text(json.dumps([sample]))
    db = sqlite3.connect(data / 'state.sqlite3')
    db.executescript('CREATE TABLE entities(kind TEXT, repo TEXT, id TEXT, body TEXT, PRIMARY KEY(kind, repo, id));')
    records = [
        ('pr', {'user': {'login': 'author'}}),
        ('inline', inline),
        ('construction', {'diff_key': 'source..selected'}),
        ('diff', {'path': 'fixture.diff', 'sha256': diff_sha256,
                  'files': [{'filename': 'src/a.sv', 'patch': patch}]}),
    ]
    db.executemany('INSERT INTO entities VALUES (?,?,?,?)',
                   [(kind, repo, str(number if kind != 'diff' else 'source..selected'), json.dumps(value))
                    for kind, value in records])
    db.commit()
    db.close()
    return data


def _valid_result(task, packet):
    comment_id = packet['thread'][0]['id']
    return {
        'thread_key': task['thread_key'], 'input_sha256': task['input_sha256'],
        'decision': 'no_issue', 'reason': 'fixture has no actionable issue',
        'evidence_comment_ids': [comment_id], 'issues': [],
    }


def test_full_scope_packets_and_resume_preserve_existing_inputs(tmp_path):
    data = _annotation_fixture(tmp_path)
    output = tmp_path / 'full'
    prepare(data, output, all_threads=True)
    manifest_path = output / 'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    assert manifest['scope'] == manifest['stratum'] == 'full'
    assert manifest['status'] == 'complete'
    assert len(manifest['tasks']) == 2
    assert {task['stratum'] for task in manifest['tasks']} == {'full'}

    first_input = output / manifest['tasks'][0]['input_file']
    first_bytes = first_input.read_bytes()
    manifest['tasks'] = manifest['tasks'][:1]
    manifest['status'] = 'in_progress'
    manifest['completion']['state'] = 'in_progress'
    manifest_path.write_text(json.dumps(manifest))
    prepare(data, output, all_threads=True)
    resumed = json.loads(manifest_path.read_text())
    assert resumed['status'] == 'complete'
    assert len(resumed['tasks']) == 2
    assert first_input.read_bytes() == first_bytes


def test_reuse_pilot_requires_matching_input_hash_and_validates_result(tmp_path):
    data = _annotation_fixture(tmp_path)
    pilot = tmp_path / 'pilot'
    prepare(data, pilot, all_threads=True, workers=1)
    pilot_manifest_path = pilot / 'manifest.json'
    pilot_manifest = json.loads(pilot_manifest_path.read_text())
    source_task = pilot_manifest['tasks'][0]
    source_packet = json.loads((pilot / source_task['input_file']).read_text())
    (pilot / 'results' / Path(source_task['input_file']).name).write_text(
        json.dumps(_valid_result(source_task, source_packet)))

    output = tmp_path / 'full-reuse'
    prepare(data, output, all_threads=True, workers=1, reuse_pilot=pilot)
    manifest = json.loads((output / 'manifest.json').read_text())
    task = manifest['tasks'][0]
    assert task['reuse_source']['validation'] == 'passed'
    assert task['reuse_source']['copied'] is True
    assert json.loads((output / 'results' / Path(task['input_file']).name).read_text()) == _valid_result(task, source_packet)

    # A matching thread key with a different packet hash is not a reusable result.
    bad_pilot = tmp_path / 'bad-pilot'
    bad_pilot.mkdir()
    bad_manifest = dict(pilot_manifest)
    bad_manifest['tasks'] = [dict(source_task, input_sha256='0' * 64)]
    (bad_pilot / 'manifest.json').write_text(json.dumps(bad_manifest))
    (bad_pilot / 'inputs').mkdir()
    (bad_pilot / 'results').mkdir()
    (bad_pilot / source_task['input_file']).write_bytes((pilot / source_task['input_file']).read_bytes())
    (bad_pilot / 'results' / Path(source_task['input_file']).name).write_bytes(
        (pilot / 'results' / Path(source_task['input_file']).name).read_bytes())
    bad_output = tmp_path / 'bad-reuse'
    prepare(data, bad_output, all_threads=True, workers=1, reuse_pilot=bad_pilot)
    assert not (bad_output / 'results' / Path(source_task['input_file']).name).exists()

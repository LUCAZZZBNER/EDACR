import hashlib
import json

import pytest

from scripts.annotation_manifest import validate_manifest_tasks
from scripts.assemble_thread_annotations import assemble, validate_result
from scripts.prepare_thread_pilot import write_json


def task(key='owner/repo#1:10', filename='inputs/0001.json'):
    return {'thread_key': key, 'input_file': filename, 'input_sha256': 'a' * 64,
            'stratum': 'full', 'worker_id': 1}


def test_input_hash_binds_actual_utf8_bytes_on_every_platform(tmp_path):
    path = tmp_path / 'input.json'
    digest = write_json(path, {'body': '中文\nsecond line'})
    actual = path.read_bytes()
    assert digest == hashlib.sha256(actual).hexdigest()
    assert b'\r\n' not in actual
    assert json.loads(actual)['body'] == '中文\nsecond line'


def test_standalone_assembly_rejects_duplicate_before_writing(tmp_path):
    write_json(tmp_path / 'manifest.json', {'status': 'complete', 'population_threads': 2,
                                           'tasks': [task(), task()]})
    with pytest.raises(ValueError, match='duplicate thread_key'):
        assemble(tmp_path)
    assert not (tmp_path / 'report.json').exists()


@pytest.mark.parametrize('tasks, message', [
    ([task(), task('owner/repo#2:20')], 'duplicate input_file'),
    ([task(), task('owner/repo#2:20', 'other/0001.json')], 'duplicate result filename'),
])
def test_manifest_rejects_file_aliases(tasks, message):
    with pytest.raises(ValueError, match=message):
        validate_manifest_tasks({'tasks': tasks})


def test_complete_population_must_equal_unique_tasks():
    with pytest.raises(ValueError, match='population'):
        validate_manifest_tasks({'tasks': [task()], 'population_threads': 2, 'status': 'complete'})
    assert len(validate_manifest_tasks({'tasks': [task()], 'population_threads': 2,
                                       'status': 'in_progress'})) == 1


@pytest.mark.parametrize('where, field', [('result', 'human_verified'),
                                        ('result', 'tests_executed'),
                                        ('issue', 'provenance')])
def test_worker_cannot_claim_verification_or_supply_unknown_fields(where, field):
    packet = {'thread_key': task()['thread_key'], 'thread': [{'id': 10}],
              'anchor': {'path': 'a.sv', 'side': 'left', 'from_line': 1, 'to_line': 1}}
    issue = {**packet['anchor'], 'summary': 'Concrete change request',
             'category': 'maintainability_readability', 'evidence_comment_ids': [10]}
    result = {'thread_key': packet['thread_key'], 'input_sha256': 'a' * 64,
              'decision': 'candidate_issue', 'reason': 'Supported request',
              'evidence_comment_ids': [10], 'issues': [issue]}
    assert validate_result(result, packet, task(), 'a' * 64) == []
    (result if where == 'result' else issue)[field] = True
    assert where + '_unknown_fields' in validate_result(result, packet, task(), 'a' * 64)

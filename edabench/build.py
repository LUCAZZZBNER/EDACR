from collections import Counter
import json
from pathlib import Path

from .revisions import is_bot, is_code, locate, region_evidence, select_revision
from .storage import digest

RULES_VERSION = 'eda-raw-review-v1'


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n')
    temporary.replace(path)


def construct(store, repo, number):
    pr = store.get('pr', repo, number)
    store.put('alignment_failures', repo, number, [])
    comments = store.get('inline', repo, number) or []
    target, threads, counts, failures = select_revision(comments)
    counters = {'inline_comments': len(comments), 'bot_comments': sum(is_bot(c) for c in comments),
                'unlocatable_comments': 0}
    task = store.task(f'pr:{repo}#{number}')
    if not task or task['state'] != 'complete':
        return None, 'raw_collection_incomplete', counters
    if not target:
        return None, 'no_nonbot_rooted_threads', counters
    material_task = store.task(f'material:{repo}#{number}')
    construction = store.get('construction', repo, number)
    if not material_task or material_task['state'] != 'complete' or not construction:
        return None, 'material_pending:' + ((material_task or {}).get('reason') or 'not_collected'), counters
    if construction['state'] != 'ready':
        return None, construction['reason'], counters
    if construction['target'] != target:
        return None, 'cached_selection_mismatch', counters
    diff = store.get('diff', repo, construction['diff_key'])
    if not diff or not diff['complete']:
        return None, 'complete_diff_missing', counters
    path = store.root / diff['path']
    if not path.exists() or digest(path) != diff['sha256']:
        return None, 'diff_file_missing_or_corrupt', counters
    if not any(is_code(f['filename']) or is_code(f.get('previous_filename', '')) for f in diff['files']):
        return None, 'no_code_changes', counters
    thread_by_comment = {}
    for thread in store.get('threads', repo, number) or []:
        for comment in thread['comments']:
            thread_by_comment[comment['databaseId']] = thread
    later = construction['subsequent_evidence']
    later_diff = store.get('diff', repo, later['diff_key']) if later['status'] == 'available' else None
    if later_diff:
        later_path = store.root / later_diff['path']
        if not later_path.exists() or digest(later_path) != later_diff['sha256']:
            later_diff = None
            later = {'status': 'unavailable', 'reason': 'subsequent_diff_missing_or_corrupt'}
    exported, located, conflicts, location_failures = [], 0, [], []
    for thread in threads:
        root = thread['root']
        anchor, reason = locate(root, diff['files'])
        if reason == 'original_hunk_conflicts_with_selected_baseline':
            conflicts.append(root['id'])
        graph = thread_by_comment.get(root['id'])
        evidence = {**later}
        if later_diff and anchor:
            file = next(f for f in diff['files'] if root['path'] in (f['filename'], f.get('previous_filename')))
            evidence.update(region_evidence(anchor, file, later_diff['files']))
        for comment in thread['comments']:
            if is_bot(comment):
                continue
            if anchor:
                located += 1
            else:
                counters['unlocatable_comments'] += 1
                location_failures.append({'comment_id': comment['id'], 'thread_root_id': root['id'], 'reason': reason})
            exported.append({'is_ai_comment': False, 'note': comment.get('body') or '',
                             'path': anchor['path'] if anchor else root.get('path'),
                             'side': anchor['side'] if anchor else (root.get('side') or '').lower() or None,
                             'source_model': '', 'from_line': anchor['from_line'] if anchor else None,
                             'to_line': anchor['to_line'] if anchor else None, 'category': '', 'context': '',
                             'metadata': {'comment_id': comment['id'], 'thread_root_id': root['id'],
                                          'in_reply_to_id': comment.get('in_reply_to_id'),
                                          'thread_id': graph['id'] if graph else None,
                                          'author': comment.get('user'), 'created_at': comment['created_at'],
                                          'original_commit_id': comment.get('original_commit_id'),
                                          'commit_id': comment.get('commit_id'),
                                          'original_path': comment.get('path'),
                                          'original_line': comment.get('original_line'),
                                          'original_start_line': comment.get('original_start_line'),
                                          'original_position': comment.get('original_position'),
                                          'diff_hunk': comment.get('diff_hunk'),
                                          'location_status': 'verified' if anchor else reason,
                                          'location_method': anchor['method'] if anchor else None,
                                          'is_resolved': graph['isResolved'] if graph else None,
                                          'is_outdated': graph['isOutdated'] if graph else None,
                                          'subsequent_region_evidence': evidence,
                                          'raw_entity': ['inline', repo, str(number), comment['id']]}})
    store.put('alignment_failures', repo, number, location_failures)
    if conflicts:
        return None, 'original_hunk_conflicts_with_selected_baseline', counters
    if not located:
        return None, 'no_locatable_nonbot_comment', counters
    repository = next((r for _, name, r in store.items('repository') if name == repo), {})
    return {'change_line_count': diff['statistics']['changed_loc'],
            'project_main_language': repository.get('language'), 'source_commit': construction['source'],
            'target_commit': target, 'githubPrUrl': pr['html_url'], 'category': '', 'comments': exported,
            'metadata': {'repository': repo, 'number': int(number), 'title': pr['title'], 'body': pr.get('body'),
                         'closed_at': pr['closed_at'], 'merged_at': pr.get('merged_at'),
                         'api_base_sha': construction['api_base_sha'], 'candidate_base_sha': construction['candidate_base_sha'],
                         'baseline_method': construction['baseline_method'], 'final_head_sha': pr['head']['sha'],
                         'revision_counts': counts, 'thread_failures': failures, 'statistics': diff['statistics'],
                         'verified_comment_count': located, 'diff_path': diff['path'], 'diff_sha256': diff['sha256'],
                         'diff_method': diff['method'], 'rules_version': RULES_VERSION,
                         'raw_database': 'state.sqlite3', 'raw_pr_entity': ['pr', repo, str(number)],
                         'history_entity': ['history', repo, str(number)],
                         'events_entity': ['events', repo, str(number)]}}, None, counters


def status(store):
    tasks = [dict(r) for r in store.db.execute('SELECT * FROM tasks ORDER BY key')]
    permanent_reasons = ('historical_revision_unavailable', 'historical_base_ref_change',
                         'historical_base_before_force_push_unavailable', 'archive_tree_hash_mismatch',
                         'HTTP 404', 'HTTP 410', 'HTTP 422')
    unrecoverable = [t for t in tasks if t['state'] == 'failed'
                     and any(reason in (t['reason'] or '') for reason in permanent_reasons)]
    return {'cutoff': store.meta('cutoff'),
            'task_states': dict(Counter(t['state'] for t in tasks)),
            'repositories': [t for t in tasks if t['key'].startswith('index:')],
            'failed_tasks': [t for t in tasks if t['state'] == 'failed'],
            'unrecoverable_with_cached_material': unrecoverable,
            'unfinished_task_count': sum(t['state'] != 'complete' for t in tasks),
            'raw_pr_count': store.db.execute("SELECT COUNT(*) FROM entities WHERE kind='pr'").fetchone()[0],
            'constructed_pr_count': store.db.execute("SELECT COUNT(*) FROM entities WHERE kind='construction'").fetchone()[0],
            'quotas': {kind: store.meta('quota_' + kind) for kind in ('core', 'graphql')},
            'last_build': store.meta('last_build')}


def build(store):
    samples, decisions, report = [], [], {}
    for row in store.meta('input_rows') or []:
        if row['duplicate']:
            continue
        original = row['full_name']
        record = next(((name, body) for org, name, body in store.items('repository') if org == original), None)
        repo = record[0] if record else original
        report[repo] = {'input_name': original, 'scan_task': store.task('index:' + original),
                        'closed_prs': sum(1 for _ in store.items('pr_index', repo)),
                        'indexed_inline_comments': sum(1 for _ in store.items('comment_index', repo)),
                        'indexed_bot_comments': sum(is_bot(c) for _, _, c in store.items('comment_index', repo)),
                        'collected_prs': 0, 'retained_prs': 0, 'inline_comments': 0,
                        'bot_comments': 0, 'unlocatable_comments': 0, 'reasons': Counter()}
    for repo, number, pr in store.items('pr'):
        sample, reason, counters = construct(store, repo, number)
        r = report[repo]
        r['collected_prs'] += 1
        for k, value in counters.items():
            r[k] += value
        if sample:
            samples.append(sample)
            r['retained_prs'] += 1
        else:
            r['reasons'][reason] += 1
        decisions.append({'repository': repo, 'number': int(number), 'retained': sample is not None, 'reason': reason})
    samples.sort(key=lambda s: (s['metadata']['repository'].lower(), s['metadata']['number']))
    state = status(store)
    task_rows = list(store.db.execute('SELECT state FROM tasks'))
    complete = bool(report) and all(r['scan_task'] and r['scan_task']['state'] == 'complete' for r in report.values()) and all(t[0] == 'complete' for t in task_rows)
    # An index-only run is not a complete collection: every indexed candidate must have a completed PR task.
    import re
    for repo in report:
        for _, _, comment in store.items('comment_index', repo):
            if is_bot(comment):
                continue
            match = re.search(r'/pulls/(\d+)$', comment['pull_request_url'])
            if match and store.get('pr_index', repo, match[1]):
                task = store.task(f'pr:{repo}#{match[1]}')
                material = store.task(f'material:{repo}#{match[1]}')
                if not task or task['state'] != 'complete' or not material or material['state'] != 'complete':
                    complete = False
    output = store.root / 'dataset'
    atomic_json(output / 'samples.json', samples)
    atomic_json(output / 'decisions.json', decisions)
    atomic_json(output / 'alignment_failures.json', [
        {'repository': repo, 'number': int(number), **failure}
        for repo, number, failures in store.items('alignment_failures') for failure in failures])
    unavailable_history = [
        {'repository': repo, 'number': int(number), 'sha': sha, **record}
        for repo, number, history in store.items('history') for sha, record in history.items()
        if record['state'] != 'available']
    atomic_json(output / 'unavailable_history.json', unavailable_history)
    atomic_json(output / 'report.json', {'repositories': report, 'failed_tasks': state['failed_tasks'],
                                       'unrecoverable_with_cached_material': state['unrecoverable_with_cached_material'],
                                       'unavailable_history_count': len(unavailable_history),
                                       'unfinished_tasks': [dict(r) for r in store.db.execute("SELECT * FROM tasks WHERE state!='complete' ORDER BY key")],
                                       'sample_count': len(samples), 'complete': complete})
    references = Path(__file__).resolve().parent.parent / 'reference' / 'aacr-source.json'
    reference = json.loads(references.read_text()) if references.exists() else None
    observed = store.db.execute('SELECT MIN(fetched_at),MAX(fetched_at) FROM responses').fetchone()
    manifest = {'rules_version': RULES_VERSION, 'cutoff': store.meta('cutoff'),
                'api_observation_range': {'first': observed[0], 'last': observed[1]},
                'input_sha256': store.meta('excel_sha256'), 'input_rows': store.meta('input_rows'),
                'reference': reference, 'sample_count': len(samples), 'complete': complete,
                'samples_sha256': digest(output / 'samples.json'),
                'rules': {'closed_and_merged_or_unmerged': True, 'one_revision_per_pr': True,
                          'revision_votes': 'independent rooted threads with at least one non-bot',
                          'tie_break': ['earliest_root_review_time', 'sha'], 'languages': 'unrestricted',
                          'size_limit': None, 'semantic_annotation': False,
                          'bot_rule': 'GitHub user.type Bot or login suffix [bot]',
                          'code_file_policy': 'edabench/revisions.py:is_code',
                          'unlocatable_selected_comments': 'retained with null line numbers',
                          'minimum_verified_comments': 1, 'adoption_required': False},
                'temporal_scope': 'created/closed by cutoff; API responses and thread state observed at individual fetched_at times'}
    atomic_json(output / 'manifest.json', manifest)
    store.meta('last_build', {'sample_count': len(samples), 'complete': complete,
                              'samples_sha256': manifest['samples_sha256']})
    return {'sample_count': len(samples), 'complete': complete, 'output': str(output)}

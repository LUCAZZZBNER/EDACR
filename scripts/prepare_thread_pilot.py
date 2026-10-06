"""Prepare reproducible, read-only thread inputs for the 200-thread pilot."""
import argparse
from collections import defaultdict
import hashlib
import json
import os
from pathlib import Path
import random
import re
import shutil
import sqlite3
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from edabench.revisions import is_bot, parse_patch, select_revision
from scripts.assemble_thread_annotations import validate_result


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n'
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', newline='\n', dir=path.parent,
                                         prefix=f'.{path.name}.', suffix='.tmp', delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()
    return hashlib.sha256(text.encode()).hexdigest()


def _sha256_file(path):
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def choose_threads(population, seed):
    rng = random.Random(seed)
    random_indices = rng.sample(range(len(population)), 150)
    selected = [(i, 'random', None) for i in random_indices]
    used = set(random_indices)
    tests = {
        'unlocated': lambda cs: cs[0]['metadata']['location_status'] != 'verified',
        'multi_turn': lambda cs: len(cs) >= 4,
        'short_reply': lambda cs: any(c['metadata']['in_reply_to_id'] and len(c['note']) <= 80 for c in cs),
        'cross_reference': lambda cs: any(re.search(r'\b(same as|as above|as below|see above|see below)\b|同上|如上', c['note'], re.I) for c in cs),
        'multiline': lambda cs: cs[0]['from_line'] is not None and cs[0]['to_line'] > cs[0]['from_line'],
    }
    for name, predicate in tests.items():
        pool = [i for i, (_, _, cs) in enumerate(population) if i not in used and predicate(cs)]
        if len(pool) < 10:
            raise ValueError(f'not enough distinct threads for {name}')
        indices = rng.sample(pool, 10)
        selected.extend((i, 'challenge', name) for i in indices)
        used.update(indices)
    return selected


def _make_packet(pr, raw_pr, threads, construction, diff, diff_path, root_id, exported):
    """Build one packet; this is shared by pilot and full preparation."""
    thread = next(t for t in threads if t['root']['id'] == root_id)
    root = thread['root']
    anchor = {k: exported[0][k] for k in ('path', 'side', 'from_line', 'to_line')}
    anchor['location_status'] = exported[0]['metadata']['location_status']
    matching = [f for f in diff['files'] if root['path'] in (f['filename'], f.get('previous_filename'))]
    file_diff = matching[0] if len(matching) == 1 else None
    context = {}
    if file_diff:
        parsed, _, _ = parse_patch(file_diff.get('patch') or '')
        for side, line_map in parsed.items():
            first = anchor['from_line'] or root.get('original_start_line') or root.get('original_line') or 1
            last = anchor['to_line'] or root.get('original_line') or first
            context[side] = [{'line': n, 'text': text} for n, text in sorted(line_map.items())
                             if first - 12 <= n <= last + 12]

    def compact(comment):
        return {**{k: comment.get(k) for k in (
            'id', 'body', 'created_at', 'in_reply_to_id', 'original_commit_id', 'commit_id',
            'path', 'original_line', 'original_start_line', 'side', 'start_side', 'subject_type', 'html_url')},
                'author': (comment.get('user') or {}).get('login'),
                'is_pr_author': (comment.get('user') or {}).get('login') == (raw_pr.get('user') or {}).get('login'),
                'is_explicit_bot': is_bot(comment)}

    neighbors = [t for t in threads if t['root']['id'] != root_id and t['root']['path'] == root['path']]
    line = root.get('original_line') or 0
    neighbors.sort(key=lambda t: (abs((t['root'].get('original_line') or 0) - line), t['root']['id']))
    repo, number = pr['metadata']['repository'], pr['metadata']['number']
    key = f'{repo}#{number}:{root_id}'
    return {
        'thread_key': key,
        'pr': {k: pr[k] for k in ('githubPrUrl', 'source_commit', 'target_commit', 'project_main_language')},
        'pr_metadata': {k: pr['metadata'][k] for k in ('repository', 'number', 'title', 'body')},
        'anchor': anchor,
        'thread': [compact(c) for c in thread['comments']],
        'original_diff_hunk': root.get('diff_hunk'),
        'selected_code_context': context,
        'neighbor_threads': [{'root_id': t['root']['id'], 'comments': [compact(c) for c in t['comments']],
                              'original_diff_hunk': t['root'].get('diff_hunk')} for t in neighbors[:4]],
        'context_limits': 'Only nearest four other threads on the same file and selected revision are included; missing context must not be invented.',
        'full_diff_path': str(diff_path.resolve()),
        'full_diff_sha256': diff['sha256'],
        'selected_file_patch': file_diff,
    }


def _load_pilot_reuse(path):
    path = Path(path)
    manifest_path = path / 'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    if not isinstance(manifest, dict) or not isinstance(manifest.get('tasks'), list):
        raise ValueError('pilot manifest.tasks must be a list')
    by_key = {}
    for task in manifest['tasks']:
        if not isinstance(task, dict):
            continue
        key = (task.get('thread_key'), task.get('input_sha256'))
        if key[0] is not None and key[1] is not None:
            if key in by_key:
                raise ValueError(f'duplicate pilot task key: {key[0]}')
            by_key[key] = task
    return path, manifest, by_key


def _reuse_result(pilot, pilot_task, packet, task, output):
    """Copy a validated pilot result, returning its provenance or None."""
    pilot_path, _, _ = pilot
    input_path = pilot_path / pilot_task['input_file']
    result_name = Path(pilot_task['input_file']).name
    result_path = pilot_path / 'results' / result_name
    if not input_path.is_file() or not result_path.is_file():
        return None
    actual_sha256 = _sha256_file(input_path)
    if actual_sha256 != pilot_task.get('input_sha256') or actual_sha256 != task.get('input_sha256'):
        return None
    try:
        pilot_packet = json.loads(input_path.read_text())
        result = json.loads(result_path.read_text())
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    if validate_result(result, pilot_packet, pilot_task, actual_sha256):
        return None
    if validate_result(result, packet, task, task['input_sha256']):
        return None
    destination = output / 'results' / Path(task['input_file']).name
    copied = False
    if destination.is_file():
        try:
            existing = json.loads(destination.read_text())
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            existing = None
        if not validate_result(existing, packet, task, task['input_sha256']):
            return {
                'run_dir': str(pilot_path.resolve()),
                'input_file': pilot_task['input_file'],
                'result_file': str((Path('results') / result_name).as_posix()),
                'validation': 'passed', 'copied': False,
            }
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=destination.parent, prefix=f'.{destination.name}.',
                                         suffix='.tmp', delete=False) as handle:
            temporary = Path(handle.name)
            with result_path.open('rb') as source:
                shutil.copyfileobj(source, handle)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()
    copied = True
    return {
        'run_dir': str(pilot_path.resolve()),
        'input_file': pilot_task['input_file'],
        'result_file': str((Path('results') / result_name).as_posix()),
        'validation': 'passed', 'copied': copied,
    }


def prepare(data, output, seed=20260926, workers=None, all_threads=False, reuse_pilot=None):
    """Prepare pilot inputs, or all dataset threads when ``all_threads`` is true."""
    data, output = Path(data), Path(output)
    if workers is None:
        workers = 32 if all_threads else 30
    if workers <= 0:
        raise ValueError('workers must be positive')
    if reuse_pilot is not None and not all_threads:
        raise ValueError('--reuse-pilot requires --all')
    manifest_path = output / 'manifest.json'
    existing_manifest = None
    if manifest_path.exists():
        if not all_threads:
            raise ValueError('pilot already prepared; reuse existing manifest to preserve provenance')
        existing_manifest = json.loads(manifest_path.read_text())

    dataset_path = data / 'dataset/samples.json'
    dataset_bytes = dataset_path.read_bytes()
    source_samples_sha256 = hashlib.sha256(dataset_bytes).hexdigest()
    samples = json.loads(dataset_bytes)
    population = []
    for pi, pr in enumerate(samples):
        groups = defaultdict(list)
        for comment in pr['comments']:
            groups[comment['metadata']['thread_root_id']].append(comment)
        population.extend((pi, root_id, cs) for root_id, cs in sorted(groups.items()))
    selected = ([(i, 'full', None) for i in range(len(population))] if all_threads
                else choose_threads(population, seed))
    rubric = Path(__file__).resolve().parents[1] / 'docs/thread-annotation.md'
    rubric_sha256 = _sha256_file(rubric)

    pilot = None
    pilot_index = {}
    if reuse_pilot is not None:
        pilot = _load_pilot_reuse(reuse_pilot)
        pilot_index = pilot[2]

    if existing_manifest is not None:
        if (existing_manifest.get('scope') != 'full'
                or existing_manifest.get('source_samples_sha256') != source_samples_sha256
                or existing_manifest.get('rubric_sha256') != rubric_sha256):
            raise ValueError('full manifest source or rubric hash changed; use a new output directory')
        tasks = list(existing_manifest.get('tasks', []))
        by_thread_key = {t.get('thread_key'): t for t in tasks if isinstance(t, dict)}
    else:
        tasks = []
        by_thread_key = {}

    previous_pilot_source = existing_manifest.get('pilot_source') if existing_manifest else None

    def manifest_value(status, *, copied=0, processed=None):
        value = {
            'seed': seed, 'population_threads': len(population),
            'population_comments': sum(len(p['comments']) for p in samples),
            'source_samples_sha256': source_samples_sha256,
            'model': 'gpt-5.6-luna', 'reasoning_effort': 'max', 'execution': 'Codex subagents',
            'human_verified': False, 'rubric_sha256': rubric_sha256,
            'sampling': ('all dataset threads' if all_threads else
                         '150 uniform random threads without replacement, followed by 10 each of 5 targeted challenge buckets; all distinct'),
            'tasks': tasks,
        }
        if all_threads:
            value.update({
                'scope': 'full', 'stratum': 'full', 'status': status,
                'source_summary': {
                    'samples_sha256': source_samples_sha256,
                    'rubric_sha256': rubric_sha256,
                    'population_threads': len(population),
                    'population_comments': sum(len(p['comments']) for p in samples),
                },
                'completion': {
                    'state': status, 'processed_threads': len(tasks) if processed is None else processed,
                    'total_threads': len(population), 'reused_results': copied,
                },
                'pilot_source': ({
                    'run_dir': str(pilot[0].resolve()),
                    'manifest_sha256': _sha256_file(pilot[0] / 'manifest.json'),
                } if pilot is not None else previous_pilot_source),
            })
        return value

    if all_threads and existing_manifest is None:
        output.mkdir(parents=True, exist_ok=True)
        write_json(manifest_path, manifest_value('in_progress', processed=0))

    db = sqlite3.connect(f'file:{(data / "state.sqlite3").resolve()}?mode=ro', uri=True)
    db.execute('BEGIN')

    def get(kind, repo, number):
        row = db.execute('SELECT body FROM entities WHERE kind=? AND repo=? AND id=?',
                         (kind, repo, str(number))).fetchone()
        if not row:
            raise ValueError(f'missing {kind} {repo} {number}')
        return json.loads(row[0])

    cached_key = None
    cached = None
    reused_count = sum(1 for task in tasks if isinstance(task, dict)
                       and task.get('reuse_source', {}).get('copied') is True)
    current_pi = None
    for ordinal, (index, stratum, challenge) in enumerate(selected, 1):
        pi, root_id, exported = population[index]
        pr = samples[pi]
        repo, number = pr['metadata']['repository'], pr['metadata']['number']
        cache_key = (repo, str(number))
        if cache_key != cached_key:
            raw_pr = get('pr', repo, number)
            raw = get('inline', repo, number)
            target, threads, _, _ = select_revision(raw)
            if target != pr['target_commit']:
                raise ValueError('selected revision changed')
            construction = get('construction', repo, number)
            diff = get('diff', repo, construction['diff_key'])
            diff_path = data / diff['path']
            full_diff_sha256 = _sha256_file(diff_path)
            if full_diff_sha256 != pr['metadata']['diff_sha256']:
                raise ValueError('diff hash mismatch')
            cached_key = cache_key
            cached = (raw_pr, threads, construction, diff, diff_path, full_diff_sha256)
        raw_pr, threads, construction, diff, diff_path, full_diff_sha256 = cached
        packet = _make_packet(pr, raw_pr, threads, construction, diff, diff_path, root_id, exported)
        filename = f'inputs/{ordinal:04d}.json'
        checksum = hashlib.sha256((json.dumps(packet, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode()).hexdigest()
        input_path = output / filename
        if input_path.exists():
            if _sha256_file(input_path) != checksum:
                raise ValueError(f'input hash mismatch for existing {filename}')
        else:
            checksum = write_json(input_path, packet)
        key = packet['thread_key']
        task = {'thread_key': key, 'input_file': filename, 'input_sha256': checksum,
                'stratum': stratum, 'challenge': challenge, 'worker_id': (ordinal - 1) % workers + 1}
        previous = by_thread_key.get(key)
        if previous is not None:
            if previous.get('input_sha256') != checksum or previous.get('input_file') != filename:
                raise ValueError(f'existing task changed for {key}')
            task = previous
        else:
            by_thread_key[key] = task
            tasks.append(task)
        if all_threads and pilot is not None and 'reuse_source' not in task:
            pilot_task = pilot_index.get((key, checksum))
            if pilot_task is not None:
                source = _reuse_result(pilot, pilot_task, packet, task, output)
                if source is not None:
                    task['reuse_source'] = source
                    if source.get('copied'):
                        reused_count += 1

        if all_threads:
            if current_pi is None:
                current_pi = pi
            elif pi != current_pi:
                print(json.dumps({'progress': 'pr', 'pr_index': current_pi + 1,
                                  'threads': ordinal - 1, 'total_threads': len(population)}), flush=True)
                current_pi = pi
            if ordinal % 1000 == 0:
                write_json(manifest_path, manifest_value('in_progress', copied=reused_count, processed=ordinal))
                print(json.dumps({'progress': 'threads', 'threads': ordinal,
                                  'total_threads': len(population)}), flush=True)
    db.close()
    if all_threads:
        if current_pi is not None:
            print(json.dumps({'progress': 'pr', 'pr_index': current_pi + 1,
                              'threads': len(selected), 'total_threads': len(population)}), flush=True)
        write_json(manifest_path, manifest_value('complete', copied=reused_count, processed=len(tasks)))
    else:
        write_json(manifest_path, manifest_value('complete'))
    for worker in range(1, workers + 1):
        write_json(output / f'assignments/worker-{worker:02d}.json',
                   [t for t in tasks if t['worker_id'] == worker])
    (output / 'results').mkdir(exist_ok=True)
    print(json.dumps({'tasks': len(tasks), 'workers': workers, 'output': str(output)}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, default=Path('data'))
    parser.add_argument('--output', type=Path)
    parser.add_argument('--seed', type=int, default=20260926)
    parser.add_argument('--workers', type=int)
    parser.add_argument('--all', dest='all_threads', action='store_true',
                        help='prepare every dataset thread instead of the 200-thread pilot')
    parser.add_argument('--reuse-pilot', type=Path,
                        help='reuse validated final results from a pilot run (requires --all)')
    args = parser.parse_args()
    if args.reuse_pilot is not None and not args.all_threads:
        parser.error('--reuse-pilot requires --all')
    if args.workers is not None and args.workers <= 0:
        parser.error('--workers must be positive')
    output = args.output or (Path('data/annotation/full-20260926') if args.all_threads
                             else Path('data/annotation/pilot-200-20260926'))
    workers = args.workers or (32 if args.all_threads else 30)
    prepare(args.data, output, args.seed, workers, args.all_threads, args.reuse_pilot)

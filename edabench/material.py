import asyncio
import hashlib
import logging
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import tempfile

import httpx

from .collect import compare
from .github import APIError, AuthenticationError
from .revisions import HUNK, parse_patch, select_revision
from .storage import digest

log = logging.getLogger(__name__)
ARCHIVES = asyncio.Semaphore(2)
ARCHIVE_LOCKS = {}
SHA = re.compile(r'^[0-9a-f]{40}$')


def git(directory, *args, input=None):
    result = subprocess.run(['git', '-c', 'core.autocrlf=false', '-c', 'core.quotePath=false',
                             '-c', 'core.safecrlf=false', *args], cwd=directory,
                            input=input, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode:
        raise ValueError('local_git_failed:' + args[0])
    return result.stdout


def validated_files(compared):
    files = compared.get('files', [])
    # GitHub compare reports at most 300 files, even when commits are paginated.
    if len(files) >= 300:
        raise ValueError('compare_file_limit')
    for file in files:
        patch = file.get('patch')
        if patch is None:
            raise ValueError('compare_patch_missing')
        _, _, hunks = parse_patch(patch)
        additions = sum(line.startswith('+') for line in patch.splitlines())
        deletions = sum(line.startswith('-') for line in patch.splitlines())
        if (additions, deletions) != (file['additions'], file['deletions']):
            raise ValueError('compare_patch_statistics_mismatch')
        if file['changes'] != additions + deletions or (file['changes'] and not hunks):
            raise ValueError('compare_patch_incomplete')
    return files



async def archive(store, repo, sha, *, temporary_root=None):
    root = Path(temporary_root) if temporary_root is not None else store.root
    key = (str(root.resolve()), repo, sha)
    lock = ARCHIVE_LOCKS.setdefault(key, asyncio.Lock())
    async with lock:
        return await download_archive(root, repo, sha)


def validate_archive(path):
    with tarfile.open(path) as source:
        source.getmembers()


async def download_archive(root, repo, sha):
    if not SHA.fullmatch(sha):
        raise ValueError('invalid_commit_sha')
    path = root / 'archives' / repo / (sha + '.tar.gz')
    if path.exists():
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    async with ARCHIVES:
        if path.exists():
            return path
        async with httpx.AsyncClient(timeout=httpx.Timeout(180, read=180), follow_redirects=True) as http:
            for attempt in range(4):
                partial = path.with_suffix('.partial')
                try:
                    async with http.stream('GET', f'https://codeload.github.com/{repo}/tar.gz/{sha}') as response:
                        if response.status_code != 200:
                            raise APIError(response.status_code, 'archive_download_failed')
                        with partial.open('wb') as output:
                            async for chunk in response.aiter_bytes():
                                output.write(chunk)
                    # A successful HTTP response is not enough; check tar integrity now.
                    await asyncio.to_thread(validate_archive, partial)
                    partial.replace(path)
                    return path
                except (httpx.TransportError, tarfile.TarError, APIError) as exc:
                    partial.unlink(missing_ok=True)
                    if isinstance(exc, APIError) and exc.status in (404, 410, 422):
                        raise
                    if attempt == 3:
                        raise ValueError('archive_download_retries_exhausted') from None
                    await asyncio.sleep(2 ** attempt)


async def tree_entries(api, repo, tree_sha):
    data = await api.get(f'/repos/{repo}/git/trees/{tree_sha}', recursive='1')
    if not data['truncated']:
        return data['tree']
    async def walk(sha, prefix=''):
        result = []
        data = await api.get(f'/repos/{repo}/git/trees/{sha}')
        if data.get('truncated'):
            raise ValueError('nonrecursive_tree_truncated')
        for entry in data['tree']:
            item = {**entry, 'path': prefix + entry['path']}
            result.append(item)
            if entry['type'] == 'tree':
                result.extend(await walk(entry['sha'], item['path'] + '/'))
        return result
    return await walk(tree_sha)


def snapshot(directory, archive_path, entries, expected_tree):
    for path in directory.iterdir():
        if path.name == '.git':
            continue
        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(path)
        else:
            path.unlink()
    with tarfile.open(archive_path) as source:
        for member in source.getmembers():
            components = member.name.split('/', 1)
            if len(components) != 2 or not components[1]:
                continue
            member.name = components[1]
            if '.git' in Path(member.name).parts:
                raise ValueError('archive_contains_git_directory')
            source.extract(member, directory, filter='data')
    git(directory, 'read-tree', '--empty')
    git(directory, 'add', '-A', '-f', '--', '.')
    for entry in entries:
        if entry['mode'] == '160000':
            git(directory, 'update-index', '--add', '--cacheinfo', '160000', entry['sha'], entry['path'])
    tree = git(directory, 'write-tree').decode().strip()
    if tree != expected_tree:
        raise ValueError('archive_tree_hash_mismatch:export_ignored_or_unrecoverable_content')
    return tree


def local_diff(base_archive, head_archive, base_entries, head_entries, base_tree, head_tree):
    with tempfile.TemporaryDirectory(prefix='edabench-diff-') as work:
        directory = Path(work)
        git(directory, 'init', '-q')
        old = snapshot(directory, base_archive, base_entries, base_tree)
        new = snapshot(directory, head_archive, head_entries, head_tree)
        patch = git(directory, 'diff', '--no-ext-diff', '--no-textconv', '--binary', '--full-index', '-M', old, new)
        raw = git(directory, 'diff', '--raw', '--no-abbrev', '-z', '-M', old, new).split(b'\0')
        empty = git(directory, 'hash-object', '-w', '--stdin', input=b'').decode().strip()
        files = []
        index = 0
        while index < len(raw) and raw[index]:
            mode1, mode2, sha1, sha2, status = raw[index].decode().split()
            name1 = raw[index + 1].decode('utf-8', 'surrogateescape')
            index += 2
            name2 = name1
            if status[0] in 'RC':
                name2 = raw[index].decode('utf-8', 'surrogateescape')
                index += 1
            file = {'filename': name2, 'status': {'A': 'added', 'D': 'removed', 'R': 'renamed',
                     'C': 'copied', 'M': 'modified', 'T': 'changed'}.get(status[0], status),
                    'sha': sha2, 'additions': 0, 'deletions': 0}
            if name1 != name2:
                file['previous_filename'] = name1
            if mode1 == ':160000' or mode2 == '160000':
                # Submodules have no text blob. The complete git patch still preserves gitlink SHAs.
                file.update(patch='', binary=True, gitlink=True)
                file['additions'] = int(mode2 != '000000')
                file['deletions'] = int(mode1 != ':000000')
            else:
                left = empty if sha1 == '0' * 40 else sha1
                right = empty if sha2 == '0' * 40 else sha2
                blob_diff = git(directory, 'diff', '--no-ext-diff', '--no-textconv', left, right).decode('utf-8', 'replace')
                lines = blob_diff.splitlines(keepends=True)
                start = next((n for n, line in enumerate(lines) if HUNK.match(line)), len(lines))
                file['patch'] = ''.join(lines[start:]).rstrip('\n')
                file['binary'] = 'Binary files ' in blob_diff
                parse_patch(file['patch'])
                file['additions'] = sum(line.startswith('+') for line in lines[start:])
                file['deletions'] = sum(line.startswith('-') for line in lines[start:])
            file['changes'] = file['additions'] + file['deletions']
            files.append(file)
        return files, patch


async def complete_diff(api, store, repo, base, head):
    key = base + '..' + head
    existing = store.get('diff', repo, key)
    if existing:
        path = store.root / existing['path']
        if path.exists() and digest(path) == existing['sha256'] and existing['method'] != 'validated_compare_patches':
            return existing
    compared = await compare(api, repo, base, head)
    # compare is a three-dot diff: exact two-tree diff requires base to be its merge base.
    if compared['merge_base_commit']['sha'] != base:
        raise ValueError('diff_source_is_not_ancestor_of_target')
    reason = None
    try:
        files = validated_files(compared)
        raw, _ = await api.request(f'/repos/{repo}/compare/{base}...{head}',
                                   accept='application/vnd.github.diff')
        if not isinstance(raw, str) or (raw and not raw.startswith('diff --git ')):
            raise ValueError('compare_diff_media_type_invalid')
        sections = re.split(r'(?m)^diff --git ', raw)[1:]
        if len(sections) != len(files):
            raise ValueError('compare_diff_file_count_mismatch')
        for section, file in zip(sections, files):
            old = file.get('previous_filename', file['filename'])
            if section.split('\n', 1)[0] != f'a/{old} b/{file["filename"]}':
                raise ValueError('compare_diff_path_mismatch')
            lines = section.splitlines()
            start = next((i for i, line in enumerate(lines) if HUNK.match(line)), len(lines))
            text_patch = '\n'.join(lines[start:])
            parse_patch(text_patch)
            if (sum(x.startswith('+') for x in lines[start:]), sum(x.startswith('-') for x in lines[start:])) != (file['additions'], file['deletions']):
                raise ValueError('compare_diff_statistics_mismatch')
            if text_patch != file['patch'].rstrip('\n'):
                raise ValueError('compare_diff_patch_mismatch')
        patch = raw.encode()
        method = 'validated_compare_diff'
    except AuthenticationError:
        raise
    except (ValueError, APIError) as exc:
        reason = str(exc)
        archives, entries, trees = [], [], []
        with tempfile.TemporaryDirectory(prefix='archive-work-', dir=store.root) as work:
            for sha in (base, head):
                commit = await api.get(f'/repos/{repo}/git/commits/{sha}')
                tree = commit['tree']['sha']
                trees.append(tree)
                entries.append(await tree_entries(api, repo, tree))
                cached = store.root / 'archives' / repo / (sha + '.tar.gz')
                archives.append(cached if cached.exists() else
                                await archive(store, repo, sha, temporary_root=work))
            files, patch = await asyncio.to_thread(local_diff, *archives, *entries, *trees)
        method = 'tree_hash_verified_archives_and_git'
    path = store.root / 'diffs' / repo / (key + '.diff')
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as output:
        output.write(patch)
        temporary = Path(output.name)
    temporary.replace(path)
    record = {'source': base, 'target': head, 'files': files, 'method': method,
              'fallback_reason': reason, 'path': str(path.relative_to(store.root)),
              'sha256': hashlib.sha256(patch).hexdigest(), 'complete': True,
              'statistics': {'additions': sum(f['additions'] for f in files),
                             'deletions': sum(f['deletions'] for f in files),
                             'changed_files': len(files),
                             'hunks': sum(len(parse_patch(f.get('patch', ''))[2]) for f in files)}}
    record['statistics']['changed_loc'] = record['statistics']['additions'] + record['statistics']['deletions']
    store.put('diff', repo, key, record)
    return record


async def materialize(api, store, repo, number):
    final_files = store.get('final_files_status', repo, number)
    if final_files and not final_files['complete']:
        final_pr = store.get('pr', repo, number)
        final_comparison = await compare(api, repo, final_pr['base']['sha'], final_pr['head']['sha'])
        full = await complete_diff(api, store, repo, final_comparison['merge_base_commit']['sha'], final_pr['head']['sha'])
        if len(full['files']) != final_pr['changed_files']:
            raise ValueError('final_file_limit_fallback_count_mismatch')
        store.put('files', repo, number, full['files'])
        store.put('final_files_status', repo, number, {**final_files, 'complete': True,
                  'fallback_diff_key': full['source'] + '..' + full['target']})
    comments = store.get('inline', repo, number)
    target, threads, counts, failures = select_revision(comments)
    selection = {'target': target, 'revision_counts': counts, 'thread_failures': failures}
    store.put('selection', repo, number, selection)
    if not target:
        store.put('construction', repo, number, {'state': 'excluded', 'reason': 'no_nonbot_rooted_threads'})
        return
    pr = store.get('pr', repo, number)
    history = store.get('history', repo, number)
    if history.get(target, {}).get('state') != 'available':
        raise ValueError('selected_historical_revision_unavailable')
    events = store.get('events', repo, number)
    first_review = counts[target]['first_review']
    base = pr['base']['sha']
    # A ref-name change does not expose a historical base SHA. Do not substitute a current branch.
    if any(e['__typename'] == 'BaseRefChangedEvent' for e in events):
        raise ValueError('historical_base_ref_change_cannot_be_verified')
    later_base_pushes = sorted((e for e in events if e['__typename'] == 'BaseRefForcePushedEvent'
                                and e['createdAt'] >= first_review), key=lambda e: e['createdAt'])
    if later_base_pushes:
        base = (later_base_pushes[0].get('beforeCommit') or {}).get('oid')
        if not base:
            raise ValueError('historical_base_before_force_push_unavailable')
    compared = await compare(api, repo, base, target)
    source = compared['merge_base_commit']['sha']
    store.put('revision', repo, source, compared['merge_base_commit'])
    await complete_diff(api, store, repo, source, target)
    evidence = {'status': 'not_assessed', 'reason': 'selected_revision_is_final_head'}
    if pr['head']['sha'] != target:
        try:
            subsequent = await complete_diff(api, store, repo, target, pr['head']['sha'])
            evidence = {'status': 'available', 'diff_key': subsequent['source'] + '..' + subsequent['target'],
                        'target': pr['head']['sha']}
        except AuthenticationError:
            raise
        except (APIError, ValueError) as exc:
            evidence = {'status': 'unavailable', 'reason': str(exc)}
    store.put('construction', repo, number, {'state': 'ready', 'source': source, 'target': target,
              'api_base_sha': pr['base']['sha'], 'candidate_base_sha': base,
              'baseline_method': 'merge_base_and_original_hunk_validation',
              'diff_key': source + '..' + target, 'subsequent_evidence': evidence})

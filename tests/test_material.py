import asyncio
from pathlib import Path

import pytest

from edabench.material import complete_diff, git, local_diff
from edabench.storage import Store


def git_fixture(tmp_path):
    repo = tmp_path / 'repo'
    repo.mkdir()
    git(repo, 'init', '-q')
    (repo / 'old.py').write_text('same\nold\nend\n')
    (repo / 'README.md').write_text('docs\n')
    (repo / 'binary.dat').write_bytes(b'\x00\x01')
    git(repo, 'add', '.')
    git(repo, '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.org', 'commit', '-qm', 'base')
    base = git(repo, 'rev-parse', 'HEAD').decode().strip()
    base_tree = git(repo, 'rev-parse', 'HEAD^{tree}').decode().strip()
    (repo / 'old.py').rename(repo / 'new.py')
    (repo / 'new.py').write_text('same\nnew\nend\n')
    (repo / 'binary.dat').write_bytes(b'\x00\x02')
    (repo / 'run.sh').write_text('#!/bin/sh\ntrue\n')
    (repo / 'run.sh').chmod(0o755)
    (repo / 'link').symlink_to('new.py')
    git(repo, 'add', '-A')
    git(repo, '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.org', 'commit', '-qm', 'target')
    target = git(repo, 'rev-parse', 'HEAD').decode().strip()
    target_tree = git(repo, 'rev-parse', 'HEAD^{tree}').decode().strip()
    archives = []
    for sha in (base, target):
        path = tmp_path / (sha + '.tar.gz')
        path.write_bytes(git(repo, 'archive', '--format=tar.gz', '--prefix=repo/', sha))
        archives.append(path)
    return base, target, base_tree, target_tree, archives


def test_archive_full_diff_and_tree_integrity(tmp_path):
    base, target, base_tree, target_tree, archives = git_fixture(tmp_path)
    files, patch = local_diff(*archives, [], [], base_tree, target_tree)
    rename = next(f for f in files if f['filename'] == 'new.py')
    assert rename['previous_filename'] == 'old.py'
    assert rename['additions'] == rename['deletions'] == 1
    assert b'GIT binary patch' in patch
    assert b'new file mode 100755' in patch
    assert b'new file mode 120000' in patch
    with pytest.raises(ValueError, match='tree_hash_mismatch'):
        local_diff(*archives, [], [], '0' * 40, target_tree)


def test_missing_patch_falls_back_to_verified_archives(tmp_path):
    base, target, base_tree, target_tree, archives = git_fixture(tmp_path)
    store = Store(tmp_path / 'data')
    for sha, archive in zip((base, target), archives):
        cached = store.root / 'archives' / 'o/r' / (sha + '.tar.gz')
        cached.parent.mkdir(parents=True, exist_ok=True)
        cached.write_bytes(archive.read_bytes())
    class API:
        async def pages(self, path):
            yield {'merge_base_commit': {'sha': base}, 'commits': [{'sha': target}],
                   'total_commits': 1, 'files': [{'filename': 'binary.dat'}]}
        async def get(self, path, **params):
            if '/git/commits/' in path:
                return {'tree': {'sha': base_tree if path.endswith(base) else target_tree}}
            return {'truncated': False, 'tree': []}
    record = asyncio.run(complete_diff(API(), store, 'o/r', base, target))
    assert record['method'] == 'tree_hash_verified_archives_and_git'
    assert record['fallback_reason'] == 'compare_patch_missing'
    assert record['statistics']['changed_files'] == 4
    assert record['complete']


def test_raw_compare_diff_preserves_modes_and_cache(tmp_path):
    base, head = 'a' * 40, 'b' * 40
    patch = '@@ -1 +1 @@\n-old\n+new'
    raw = 'diff --git a/run.sh b/run.sh\nold mode 100644\nnew mode 100755\n--- a/run.sh\n+++ b/run.sh\n' + patch + '\n'
    class API:
        async def pages(self, path):
            yield {'merge_base_commit': {'sha': base}, 'commits': [{'sha': head}], 'total_commits': 1,
                   'files': [{'filename': 'run.sh', 'status': 'modified', 'patch': patch,
                              'additions': 1, 'deletions': 1, 'changes': 2}]}
        async def request(self, path, **kwargs):
            assert kwargs['accept'] == 'application/vnd.github.diff'
            return raw, {}
    store = Store(tmp_path)
    record = asyncio.run(complete_diff(API(), store, 'o/r', base, head))
    assert record['method'] == 'validated_compare_diff'
    assert (tmp_path / record['path']).read_text() == raw
    # Offline reuse of the verified diff needs no client methods.
    assert asyncio.run(complete_diff(object(), store, 'o/r', base, head)) == record


def test_force_pushed_missing_history_is_explicit(tmp_path):
    from edabench.material import materialize
    store = Store(tmp_path)
    store.put('inline', 'o/r', 1, [{'id': 1, 'original_commit_id': 'missing', 'created_at': '2024', 'user': None}])
    store.put('pr', 'o/r', 1, {'base': {'sha': 'base'}, 'head': {'sha': 'head'}})
    store.put('history', 'o/r', 1, {'missing': {'state': 'unavailable'}})
    with pytest.raises(ValueError, match='historical_revision_unavailable'):
        asyncio.run(materialize(object(), store, 'o/r', 1))


def test_base_ref_change_is_not_silently_replaced(tmp_path):
    from edabench.material import materialize
    store = Store(tmp_path)
    store.put('inline', 'o/r', 1, [{'id': 1, 'original_commit_id': 'selected', 'created_at': '2024', 'user': None}])
    store.put('pr', 'o/r', 1, {'base': {'sha': 'base'}, 'head': {'sha': 'head'}})
    store.put('history', 'o/r', 1, {'selected': {'state': 'available'}})
    store.put('events', 'o/r', 1, [{'__typename': 'BaseRefChangedEvent'}])
    with pytest.raises(ValueError, match='historical_base_ref_change'):
        asyncio.run(materialize(object(), store, 'o/r', 1))


def test_archive_validation_runs_off_event_loop(tmp_path, monkeypatch):
    import io
    import tarfile
    import threading
    import httpx
    import edabench.material as module
    content = io.BytesIO()
    with tarfile.open(fileobj=content, mode='w:gz') as archive:
        info = tarfile.TarInfo('repo/file.txt')
        info.size = 5
        archive.addfile(info, io.BytesIO(b'hello'))
    archive_bytes = content.getvalue()
    main_thread = threading.get_ident()
    original = module.validate_archive
    validated = []
    def validate(path):
        assert threading.get_ident() != main_thread
        original(path)
        validated.append(path)
    monkeypatch.setattr(module, 'validate_archive', validate)
    async def run():
        client = httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(200, content=archive_bytes)))
        monkeypatch.setattr(module.httpx, 'AsyncClient', lambda **kwargs: client)
        store = Store(tmp_path)
        path = await module.archive(store, 'o/r', 'a' * 40)
        assert path.read_bytes() == archive_bytes
        assert len(validated) == 1
        assert await module.archive(store, 'o/r', 'a' * 40) == path
    asyncio.run(run())


@pytest.mark.parametrize('archive_kind', ['outside_symlink', 'outside_hardlink', 'corrupt'])
def test_bad_archive_fails_one_task_without_stopping_pipeline(tmp_path, archive_kind):
    import io
    import tarfile
    from edabench.collect import collect_candidates
    from edabench.material import snapshot

    archive = tmp_path / 'bad.tar.gz'
    outside = tmp_path / 'outside'
    outside.mkdir()
    sentinel = outside / 'sentinel.txt'
    sentinel.write_text('unchanged')
    if archive_kind == 'corrupt':
        archive.write_bytes(b'not a tar archive')
    else:
        with tarfile.open(archive, 'w:gz') as output:
            link = tarfile.TarInfo('repo/sim/chipyard-symlink')
            link.type = tarfile.SYMTYPE if archive_kind == 'outside_symlink' else tarfile.LNKTYPE
            link.linkname = '../../outside' if archive_kind == 'outside_symlink' else str(sentinel)
            output.addfile(link)
            content = tarfile.TarInfo('repo/sim/chipyard-symlink/sentinel.txt')
            content.size = 7
            output.addfile(content, io.BytesIO(b'changed'))
    directory = tmp_path / 'snapshot'
    directory.mkdir()
    store = Store(tmp_path / 'data')
    store.task('pr:o/r#1', 'complete')
    store.task('pr:o/r#2', 'complete')

    async def material(api, store, repo, number):
        if number == 1:
            await asyncio.to_thread(snapshot, directory, archive, [], '0' * 40)
        else:
            store.put('construction', repo, number, {'state': 'ready'})

    asyncio.run(collect_candidates(None, store, [('o/r', 1), ('o/r', 2)], material))
    failed = store.task('material:o/r#1')
    assert failed['state'] == 'failed'
    assert failed['reason'].startswith('archive_error:')
    assert store.task('material:o/r#2')['state'] == 'complete'
    assert store.get('construction', 'o/r', 2) == {'state': 'ready'}
    assert not (directory / 'sim/chipyard-symlink').is_symlink()
    assert sentinel.read_text() == 'unchanged'
    assert not store.db.execute("SELECT 1 FROM tasks WHERE state='running'").fetchone()


@pytest.mark.parametrize('valid_tree', [True, False])
def test_new_fallback_archives_are_temporary_even_on_failure(tmp_path, monkeypatch, valid_tree):
    import shutil
    import edabench.material as module
    base, target, base_tree, target_tree, archives = git_fixture(tmp_path)
    store = Store(tmp_path / 'data')
    downloaded = []
    async def download(store, repo, sha, *, temporary_root):
        destination = Path(temporary_root) / (sha + '.tar.gz')
        shutil.copyfile(archives[0 if sha == base else 1], destination)
        downloaded.append(destination)
        return destination
    monkeypatch.setattr(module, 'archive', download)
    class API:
        async def pages(self, path):
            yield {'merge_base_commit': {'sha': base}, 'commits': [{'sha': target}],
                   'total_commits': 1, 'files': [{'filename': 'binary.dat'}]}
        async def get(self, path, **params):
            if '/git/commits/' in path:
                tree = base_tree if path.endswith(base) else target_tree
                return {'tree': {'sha': tree if valid_tree else '0' * 40}}
            return {'truncated': False, 'tree': []}
    if valid_tree:
        record = asyncio.run(complete_diff(API(), store, 'o/r', base, target))
        assert record['complete'] and (store.root / record['path']).is_file()
    else:
        with pytest.raises(ValueError, match='archive_tree_hash_mismatch'):
            asyncio.run(complete_diff(API(), store, 'o/r', base, target))
    assert len(downloaded) == 2
    assert all(not path.exists() for path in downloaded)
    assert not list(store.root.glob('archive-work-*'))
    assert not (store.root / 'archives').exists()

import asyncio

from edabench.collect import graph_history, compare, guarded
from edabench.github import APIError
from edabench.storage import Store


class GraphFixture:
    async def graphql(self, query, **v):
        def connection(nodes, more=False):
            return {'nodes': nodes, 'pageInfo': {'hasNextPage': more, 'endCursor': 'next'}}
        if 'node(id:' in query:
            return {'node': {'comments': connection([{'databaseId': 2}])}}
        if 'reviewThreads(' in query:
            data = connection([]) if v['cursor'] else connection([
                {'id': 'thread', 'comments': connection([{'databaseId': 1}], True)}], True)
            return {'repository': {'pullRequest': {'reviewThreads': data}}}
        data = connection([{'id': 'second'}]) if v['cursor'] else connection([{'id': 'first'}], True)
        return {'repository': {'pullRequest': {'timelineItems': data}}}


def test_graphql_nested_pagination():
    threads, events = asyncio.run(graph_history(GraphFixture(), 'o/r', 1))
    assert threads[0]['comments'] == [{'databaseId': 1}, {'databaseId': 2}]
    assert [e['id'] for e in events] == ['first', 'second']


def test_compare_pagination_and_retry_state(tmp_path):
    class API:
        async def pages(self, path):
            yield {'total_commits': 301, 'commits': list(range(100)), 'files': []}
            yield {'commits': list(range(100, 301))}
    assert len(asyncio.run(compare(API(), 'o/r', 'a', 'b'))['commits']) == 301
    store = Store(tmp_path)
    async def fail():
        raise APIError(0, 'network failure')
    async def succeed():
        store.put('raw', 'o/r', 1, {})
    asyncio.run(guarded(store, 'test', fail))
    assert store.task('test')['state'] == 'failed'
    asyncio.run(guarded(store, 'test', succeed))
    assert store.task('test')['state'] == 'complete'


def test_pr_commit_cap_and_final_file_cap(tmp_path, monkeypatch):
    import edabench.collect as module
    store = Store(tmp_path)
    store.meta('cutoff', '2025')
    commits = [{'sha': f'{i:040x}'} for i in range(301)]
    pr = {'closed_at': '2024', 'commits': 301, 'changed_files': 3001,
          'base': {'sha': commits[0]['sha']}, 'head': {'sha': commits[-1]['sha']}}
    class API:
        async def get(self, path):
            return pr
        async def listing(self, path):
            if path.endswith('/commits'):
                return commits[:250]
            if path.endswith('/files'):
                return [{}] * 3000
            return []
        async def pages(self, path):
            yield {'commits': commits[:100], 'total_commits': 301}
            yield {'commits': commits[100:]}
    async def graph(*args):
        return [], []
    monkeypatch.setattr(module, 'graph_history', graph)
    asyncio.run(module.collect_pr(API(), store, 'o/r', 1))
    assert len(store.get('commits', 'o/r', 1)) == 301
    assert not store.get('final_files_status', 'o/r', 1)['complete']
    assert len(store.get('history', 'o/r', 1)) == 301


def test_pipeline_fetches_ahead_while_four_material_workers_are_blocked(tmp_path, monkeypatch):
    import edabench.collect as module
    store = Store(tmp_path)
    candidates = [('o/r', number) for number in range(20)]
    async def run():
        all_fetched, release, four_busy = asyncio.Event(), asyncio.Event(), asyncio.Event()
        fetched, constructed = [], []
        active = 0
        async def fetch(api, store, repo, number):
            await asyncio.sleep(0)
            fetched.append(number)
            store.put('raw', repo, number, {'number': number})
            if len(fetched) == len(candidates):
                all_fetched.set()
        async def material(api, store, repo, number):
            nonlocal active
            active += 1
            assert active <= 4
            if active == 4:
                four_busy.set()
            await release.wait()
            constructed.append(number)
            active -= 1
        monkeypatch.setattr(module, 'collect_pr', fetch)
        task = asyncio.create_task(module.collect_candidates(None, store, candidates, material))
        try:
            await asyncio.wait_for(four_busy.wait(), 2)
            await asyncio.wait_for(all_fetched.wait(), 2)
            assert len(fetched) == 20 and constructed == []
            assert store.db.execute("SELECT count(*) FROM tasks WHERE key LIKE 'material:%' AND state='pending'").fetchone()[0] == 16
        finally:
            release.set()
            await asyncio.wait_for(task, 2)
        assert sorted(constructed) == list(range(20))
        assert all(store.task(f'material:o/r#{n}')['state'] == 'complete' for n in range(20))
    asyncio.run(run())


def test_pipeline_cancellation_reopens_db_and_resumes_without_refetch(tmp_path, monkeypatch):
    import edabench.collect as module
    store = Store(tmp_path)
    candidates = [('o/r', n) for n in range(8)]
    fetched, constructed = [], []
    async def fetch(api, store, repo, number):
        fetched.append(number)
        store.put('raw', repo, number, {'body': 'preserved'})
    monkeypatch.setattr(module, 'collect_pr', fetch)
    async def interrupt():
        entered = asyncio.Event()
        async def material(*args):
            entered.set()
            await asyncio.Event().wait()
        task = asyncio.create_task(module.collect_candidates(None, store, candidates, material))
        await asyncio.wait_for(entered.wait(), 2)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        assert not store.db.execute("SELECT 1 FROM tasks WHERE state='running'").fetchone()
    asyncio.run(interrupt())
    assert sorted(fetched) == list(range(8))
    store.close()
    store = Store(tmp_path)
    async def material(api, store, repo, number):
        assert store.get('raw', repo, number) == {'body': 'preserved'}
        constructed.append(number)
        await asyncio.sleep(0)
    asyncio.run(module.collect_candidates(None, store, candidates, material))
    assert sorted(fetched) == sorted(constructed) == list(range(8))
    asyncio.run(module.collect_candidates(None, store, candidates, material))
    assert len(fetched) == len(constructed) == 8


def test_pipeline_auth_failure_cancels_both_stages(tmp_path, monkeypatch):
    import pytest
    import edabench.collect as module
    from edabench.github import AuthenticationError
    store = Store(tmp_path)
    async def run():
        material_started = asyncio.Event()
        async def fetch(api, store, repo, number):
            if number == 1:
                return
            await material_started.wait()
            raise AuthenticationError(401, 'bad credentials')
        async def material(*args):
            material_started.set()
            await asyncio.Event().wait()
        monkeypatch.setattr(module, 'collect_pr', fetch)
        with pytest.raises(AuthenticationError):
            await asyncio.wait_for(module.collect_candidates(None, store, [('o/r', 1), ('o/r', 2)], material), 2)
        assert store.task('pr:o/r#2')['state'] == 'failed'
        assert store.task('material:o/r#1')['state'] == 'pending'
        assert not store.db.execute("SELECT 1 FROM tasks WHERE state='running'").fetchone()
    asyncio.run(run())


def test_pipeline_retries_failed_and_interrupted_tasks_once_and_respects_scope(tmp_path, monkeypatch):
    import edabench.collect as module
    store = Store(tmp_path)
    store.task('pr:o/r#1', 'complete')
    store.task('material:o/r#1', 'failed', 'previous_failure')
    store.task('pr:o/r#2', 'running')
    store.task('material:outside/repo#1', 'pending')
    fetched, constructed = [], []
    async def fetch(api, store, repo, number):
        fetched.append(number)
    async def material(api, store, repo, number):
        constructed.append(number)
        if number == 1:
            raise ValueError('still_unavailable')
    monkeypatch.setattr(module, 'collect_pr', fetch)
    asyncio.run(module.collect_candidates(None, store, [('o/r', 1), ('o/r', 2)], material))
    assert fetched == [2]
    assert sorted(constructed) == [1, 2]
    assert store.task('material:o/r#1')['state'] == 'failed'
    assert store.task('material:o/r#2')['state'] == 'complete'
    assert store.task('material:outside/repo#1')['state'] == 'pending'


def test_collect_candidates_still_require_closed_pr_and_nonbot_comment(tmp_path, monkeypatch):
    import edabench.collect as module
    store = Store(tmp_path)
    store.meta('input_rows', [{'full_name': 'o/r', 'duplicate': False}])
    store.task('index:o/r', 'complete')
    store.put('repository', 'o/r', 'o/r', {})
    store.put('index_progress', 'o/r', 'complete', True)
    store.put('pr_index', 'o/r', 1, {})
    store.put('pr_index', 'o/r', 3, {})
    for n in (1, 2, 3):
        store.put('comment_index', 'o/r', n, {'pull_request_url': f'https://api.github.com/repos/o/r/pulls/{n}',
                  'user': {'type': 'Bot'} if n == 3 else None})
    fetched = []
    async def fetch(api, store, repo, number):
        fetched.append((repo, number))
    monkeypatch.setattr(module, 'collect_pr', fetch)
    asyncio.run(module.collect(None, store))
    assert fetched == [('o/r', 1)]


def test_resume_does_not_redownload_archives_with_known_tree_mismatch(tmp_path):
    import edabench.collect as module
    store = Store(tmp_path)
    store.task('pr:o/r#1', 'complete')
    store.task('material:o/r#1', 'failed', 'archive_tree_hash_mismatch:export_ignored_or_unrecoverable_content')
    store.task('pr:o/r#2', 'complete')
    seen = []
    async def material(api, store, repo, number):
        seen.append(number)
    asyncio.run(module.collect_candidates(None, store, [('o/r', 1), ('o/r', 2)], material))
    assert seen == [2]
    assert store.task('material:o/r#1')['state'] == 'failed'
    assert store.task('material:o/r#1')['reason'].startswith('archive_tree_hash_mismatch:')
    assert store.task('material:o/r#2')['state'] == 'complete'

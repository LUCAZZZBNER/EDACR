import asyncio

import httpx
import pytest

from edabench.github import AuthenticationError, GitHub
from edabench.inputs import repositories
from edabench.storage import Store


def test_pagination_resume_and_idempotence(tmp_path):
    calls = []
    def handler(request):
        calls.append(str(request.url))
        if request.url.params.get('page') == '2':
            return httpx.Response(200, json=[{'id': 2}])
        return httpx.Response(200, json=[{'id': 1}], headers={
            'link': '<https://api.github.com/list?page=2>; rel="next"'})
    async def run():
        store = Store(tmp_path)
        client = GitHub(store, 'not-a-token', transport=httpx.MockTransport(handler), interval=0)
        assert await client.listing('/list') == [{'id': 1}, {'id': 2}]
        await client.close()
        store.close()
        store = Store(tmp_path)
        client = GitHub(store, 'not-a-token', transport=httpx.MockTransport(handler), interval=0)
        assert await client.listing('/list') == [{'id': 1}, {'id': 2}]
        assert len(calls) == 2
        store.put('x', 'r', 1, {'x': 1})
        store.put('x', 'r', 1, {'x': 2})
        assert len(list(store.items('x'))) == 1
        await client.close()
        store.close()
    asyncio.run(run())


def test_retry_after_and_auth(tmp_path):
    calls, waits = [], []
    def handler(request):
        calls.append(1)
        return httpx.Response(429, headers={'retry-after': '2'}) if len(calls) == 1 else httpx.Response(200, json=[])
    async def sleep(delay):
        waits.append(delay)
    async def run():
        client = GitHub(Store(tmp_path), 'secret', transport=httpx.MockTransport(handler), interval=0, sleep=sleep)
        assert await client.get('/x') == []
        assert waits == [2]
        await client.close()
        client = GitHub(Store(tmp_path), 'secret', transport=httpx.MockTransport(lambda r: httpx.Response(401)), interval=0)
        with pytest.raises(AuthenticationError, match='authentication'):
            await client.get('/auth')
        with pytest.raises(ValueError, match='credentials'):
            await client.get('https://example.org/x')
        await client.close()
    asyncio.run(run())


def test_excel_count():
    assert len([r for r in repositories('docs/final_repository.xlsx') if not r['duplicate']]) == 44


def test_concurrent_requests_share_pacing_after_acquiring_http_slot(tmp_path, monkeypatch):
    import edabench.github as module
    # Use a logical clock: assertions do not depend on machine speed.
    clock, starts, gates = [0.0], [], []
    active = [0]
    monkeypatch.setattr(module.time, 'monotonic', lambda: clock[0])
    async def sleep(delay):
        clock[0] += delay
        await asyncio.sleep(0)
    async def handler(request):
        starts.append(clock[0])
        await asyncio.sleep(0)
        return httpx.Response(200, json=[])
    async def run():
        client = GitHub(Store(tmp_path), 'secret', transport=httpx.MockTransport(handler), sleep=sleep)
        slot = asyncio.Semaphore(1)
        class Limit:
            async def __aenter__(self):
                await slot.acquire()
                active[0] += 1
            async def __aexit__(self, *args):
                active[0] -= 1
                slot.release()
        client.semaphore = Limit()
        original_gate = client.gate
        async def gate(resource):
            assert active[0] == 1
            gates.append(resource)
            await original_gate(resource)
        client.gate = gate
        try:
            await asyncio.gather(*(client.get(f'/request/{n}') for n in range(6)))
            assert gates == ['core'] * 6
            assert all(b - a >= .799 for a, b in zip(starts, starts[1:]))
        finally:
            await client.close()
    asyncio.run(run())


def test_resume_restores_persisted_quota(tmp_path):
    store = Store(tmp_path)
    quota = {'remaining': 123, 'limit': 5000, 'reset': 9999999999}
    store.meta('quota_core', quota)
    async def run():
        client = GitHub(store, 'secret')
        assert client.quota['core'] == quota
        await client.close()
    asyncio.run(run())


def test_http_concurrency_is_bounded_at_eight(tmp_path):
    async def run():
        eight_started, release = asyncio.Event(), asyncio.Event()
        active, peak = 0, 0
        async def handler(request):
            nonlocal active, peak
            active += 1
            peak = max(peak, active)
            if active == 8:
                eight_started.set()
            await release.wait()
            active -= 1
            return httpx.Response(200, json=[])
        client = GitHub(Store(tmp_path), 'secret', transport=httpx.MockTransport(handler), interval=0)
        tasks = [asyncio.create_task(client.get(f'/item/{n}')) for n in range(12)]
        try:
            await asyncio.wait_for(eight_started.wait(), 2)
            assert active == peak == 8
        finally:
            release.set()
            await asyncio.gather(*tasks)
            await client.close()
        assert peak == 8
    asyncio.run(run())

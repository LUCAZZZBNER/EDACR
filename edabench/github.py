import asyncio
import hashlib
import logging
import time
from datetime import datetime
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse

import httpx

from .storage import dumps

log = logging.getLogger(__name__)


class APIError(Exception):
    def __init__(self, status, reason):
        self.status = status
        super().__init__(f'{reason} (HTTP {status})')


class AuthenticationError(APIError):
    pass


class GitHub:
    def __init__(self, store, token, *, transport=None, interval=0.8, sleep=asyncio.sleep):
        self.store = store
        self.http = httpx.AsyncClient(
            headers={'Authorization': f'Bearer {token}', 'Accept': 'application/vnd.github+json',
                     'X-GitHub-Api-Version': '2022-11-28', 'User-Agent': 'EDABench/0.1'},
            timeout=90, transport=transport, follow_redirects=False)
        self.semaphore = asyncio.Semaphore(8)
        self.locks = {'core': asyncio.Lock(), 'graphql': asyncio.Lock()}
        self.next = {'core': 0, 'graphql': 0}
        self.quota = {resource: store.meta('quota_' + resource) or {} for resource in self.locks}
        self.blocked_until = 0
        self.interval, self.sleep = interval, sleep

    async def close(self):
        await self.http.aclose()

    async def wait(self, seconds, reason):
        if seconds > 1:
            log.info('Waiting %.0fs: %s', seconds, reason)
        while seconds > 0:
            part = min(seconds, 30)
            await self.sleep(part)
            seconds -= part

    async def gate(self, resource):
        async with self.locks[resource]:
            await self.wait(max(0, self.blocked_until - time.monotonic()), 'shared rate-limit backoff')
            q = self.quota.get(resource, {})
            if q.get('remaining', 1) <= 1 and q.get('reset', 0) > time.time():
                await self.wait(q['reset'] - time.time() + 1, f'{resource} primary limit')
            await self.wait(max(0, self.next[resource] - time.monotonic()), 'request pacing')
            interval = self.interval
            if q.get('remaining', 0) > 1:
                interval = max(interval, (q.get('reset', 0) - time.time()) / (q['remaining'] * .9))
            self.next[resource] = time.monotonic() + interval

    async def request(self, path, *, params=None, query=None, variables=None, accept=None):
        url = path if path.startswith('https://') else 'https://api.github.com' + path
        if urlparse(url).hostname != 'api.github.com':
            raise ValueError('Refusing API credentials outside api.github.com')
        payload = {'query': query, 'variables': variables or {}} if query else None
        key = hashlib.sha256(dumps([url, params, payload] if accept is None else [url, params, payload, accept]).encode()).hexdigest()
        self.store.put('api_request', '', key, {'url': url, 'params': params,
                       'method': 'POST' if query else 'GET', 'payload': payload, 'accept': accept})
        cached = self.store.cached(key)
        if cached:
            status, body, headers = cached
            if status >= 400:
                raise APIError(status, 'cached unavailable object')
            return body, headers
        resource = 'graphql' if query else 'core'
        for attempt in range(6):
            try:
                async with self.semaphore:
                    await self.gate(resource)
                    response = await self.http.request('POST' if query else 'GET', url,
                                                       params=params, json=payload,
                                                       headers={'Accept': accept} if accept else None)
            except httpx.TransportError:
                if attempt == 5:
                    raise APIError(0, 'network retries exhausted') from None
                await self.wait(2 ** attempt, 'temporary network failure')
                continue
            headers = {k: v for k, v in response.headers.items()
                       if k in {'link', 'x-ratelimit-remaining', 'x-ratelimit-reset',
                                'x-ratelimit-limit', 'retry-after', 'location'}}
            if 'x-ratelimit-remaining' in headers:
                self.quota[resource] = {k: int(headers['x-ratelimit-' + k])
                                        for k in ('remaining', 'reset', 'limit')}
                self.store.meta('quota_' + resource, self.quota[resource])
            status = response.status_code
            if status in (301, 302, 307, 308):
                return await self.request(headers['location'], params=params,
                                          query=query, variables=variables, accept=accept)
            if status == 401:
                raise AuthenticationError(status, 'GitHub authentication failed')
            if status in (403, 429):
                if status == 403 and not any(x in response.text.lower() for x in ('rate limit', 'abuse', 'secondary')) and 'retry-after' not in headers:
                    raise AuthenticationError(status, 'GitHub authorization denied')
                retry = headers.get('retry-after', '')
                if retry:
                    delay = float(retry) if retry.isdigit() else max(0, parsedate_to_datetime(retry).timestamp() - time.time())
                elif self.quota.get(resource, {}).get('remaining') == 0:
                    delay = max(1, self.quota[resource]['reset'] - time.time() + 1)
                else:
                    delay = 60 * 2 ** attempt
                deadline = max(self.blocked_until, time.monotonic() + delay)
                self.blocked_until = deadline
                await self.wait(delay, f'{resource} rate limit')
                if self.blocked_until == deadline:
                    self.blocked_until = 0
                continue
            if status >= 500:
                await self.wait(2 ** attempt, 'GitHub temporary failure')
                continue
            if status in (404, 410, 422):
                self.store.cache(key, status, {'unavailable': True}, headers)
                raise APIError(status, 'object unavailable')
            if status >= 400:
                raise APIError(status, 'GitHub request failed')
            try:
                body = response.text if accept == 'application/vnd.github.diff' else response.json()
            except ValueError:
                raise APIError(status, 'invalid API JSON') from None
            if query and body.get('errors'):
                if any(e.get('type') == 'RATE_LIMITED' for e in body['errors']):
                    await self.wait(60 * 2 ** attempt, 'GraphQL rate limit')
                    continue
                # Store error types only; never echo response bodies or credentials.
                kinds = sorted({e.get('type', 'query_error') for e in body['errors']})
                raise APIError(status, 'GraphQL errors: ' + ','.join(kinds))
            if query:
                rate = (body.get('data') or {}).get('rateLimit')
                if rate:
                    self.quota['graphql'] = {'remaining': rate['remaining'], 'limit': rate['limit'],
                                             'reset': datetime.fromisoformat(rate['resetAt'].replace('Z', '+00:00')).timestamp(),
                                             'cost': rate['cost']}
                    self.store.meta('quota_graphql', self.quota['graphql'])
            self.store.cache(key, status, body, headers)
            return body, headers
        raise APIError(0, 'retry budget exhausted; resume later')

    async def get(self, path, **params):
        return (await self.request(path, params=params or None))[0]

    async def pages(self, path, **params):
        params = {'per_page': 100, **params}
        while path:
            body, headers = await self.request(path, params=params)
            yield body
            links = httpx.Response(200, headers=headers).links
            path = links.get('next', {}).get('url')
            params = None

    async def listing(self, path, **params):
        result = []
        async for page in self.pages(path, **params):
            result.extend(page)
        return result

    async def graphql(self, query, **variables):
        return (await self.request('/graphql', query=query, variables=variables))[0]['data']

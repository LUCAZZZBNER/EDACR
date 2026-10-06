import asyncio
import logging
import re
import tarfile

from .github import APIError, AuthenticationError
from .storage import digest, now
from .revisions import is_bot

log = logging.getLogger(__name__)
THREADS = '''query($owner:String!,$name:String!,$number:Int!,$cursor:String) {
 repository(owner:$owner,name:$name) { pullRequest(number:$number) {
 reviewThreads(first:100,after:$cursor) { pageInfo { hasNextPage endCursor }
 nodes { id isResolved isOutdated path diffSide startDiffSide line startLine originalLine originalStartLine
 comments(first:100) { pageInfo { hasNextPage endCursor }
 nodes { databaseId id createdAt replyTo { databaseId } originalCommit { oid } } } } } } }
 rateLimit { cost limit remaining resetAt } }'''
THREAD_COMMENTS = '''query($id:ID!,$cursor:String) { node(id:$id) { ... on PullRequestReviewThread {
 comments(first:100,after:$cursor) { pageInfo { hasNextPage endCursor }
 nodes { databaseId id createdAt replyTo { databaseId } originalCommit { oid } } } } }
 rateLimit { cost limit remaining resetAt } }'''
EVENTS = '''query($owner:String!,$name:String!,$number:Int!,$cursor:String) {
 repository(owner:$owner,name:$name) { pullRequest(number:$number) {
 timelineItems(first:100,after:$cursor,itemTypes:[HEAD_REF_FORCE_PUSHED_EVENT,BASE_REF_FORCE_PUSHED_EVENT,BASE_REF_CHANGED_EVENT]) {
 pageInfo { hasNextPage endCursor } nodes { __typename
 ... on HeadRefForcePushedEvent { id createdAt beforeCommit { oid } afterCommit { oid } }
 ... on BaseRefForcePushedEvent { id createdAt beforeCommit { oid } afterCommit { oid } }
 ... on BaseRefChangedEvent { id createdAt previousRefName currentRefName }
 } } } } rateLimit { cost limit remaining resetAt } }'''


def initialize(store, excel):
    from .inputs import repositories
    checksum = digest(excel)
    if store.meta('excel_sha256') not in (None, checksum):
        raise ValueError('Excel differs from this collection; use a new data directory')
    if store.meta('cutoff') is None:
        store.meta('cutoff', now())
        store.meta('excel_sha256', checksum)
        store.meta('input_rows', repositories(excel))
    for row in store.meta('input_rows'):
        if not row['duplicate'] and store.task('index:' + row['full_name']) is None:
            store.task('index:' + row['full_name'], 'pending')


async def guarded(store, key, operation):
    task = store.task(key)
    if task and task['state'] == 'complete':
        return
    store.task(key, 'running')
    try:
        await operation()
    except asyncio.CancelledError:
        store.task(key, 'pending', 'interrupted')
        raise
    except AuthenticationError:
        store.task(key, 'failed', 'authentication_or_authorization')
        raise
    except (APIError, ValueError, OSError, tarfile.TarError) as exc:
        reason = str(exc)
        if isinstance(exc, tarfile.TarError):
            reason = f'archive_error:{type(exc).__name__}: {reason}'
        store.task(key, 'failed', reason)
        log.warning('%s: %s', key, reason)
    else:
        store.task(key, 'complete')


async def workers(items, operation, count=4):
    queue = asyncio.Queue()
    for item in items:
        queue.put_nowait(item)
    async def worker():
        while not queue.empty():
            item = queue.get_nowait()
            await operation(item)
    tasks = [asyncio.create_task(worker()) for _ in range(count)]
    try:
        await asyncio.gather(*tasks)
    except BaseException:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        raise


async def index_repository(api, store, original):
    metadata = await api.get(f'/repos/{original}')
    repo = metadata['full_name']
    store.put('repository', original, repo, metadata)
    cutoff = store.meta('cutoff')
    count = 0
    async for page in api.pages(f'/repos/{repo}/pulls', state='closed', sort='created', direction='asc'):
        eligible = [(pr['number'], pr) for pr in page
                    if pr['created_at'] <= cutoff and pr.get('closed_at') and pr['closed_at'] <= cutoff]
        store.put_many('pr_index', repo, eligible)
        count += len(eligible)
        store.put('index_progress', repo, 'pulls', {'count': count})
    count = 0
    async for page in api.pages(f'/repos/{repo}/pulls/comments', sort='created', direction='asc'):
        eligible = [(c['id'], c) for c in page if c['created_at'] <= cutoff]
        store.put_many('comment_index', repo, eligible)
        count += len(eligible)
        store.put('index_progress', repo, 'comments', {'count': count})
    store.put('index_progress', repo, 'complete', True)
    log.info('Indexed %s: %s inline comments', repo, count)


async def graph_history(api, repo, number):
    owner, name = repo.split('/')
    variables = {'owner': owner, 'name': name, 'number': number, 'cursor': None}
    threads, events = [], []
    while True:
        data = await api.graphql(THREADS, **variables)
        pr = (data.get('repository') or {}).get('pullRequest')
        if pr is None:
            raise ValueError('GraphQL PR unavailable')
        connection = pr['reviewThreads']
        for thread in connection['nodes']:
            comments = thread['comments']
            nodes = list(comments['nodes'])
            while comments['pageInfo']['hasNextPage']:
                extra = await api.graphql(THREAD_COMMENTS, id=thread['id'], cursor=comments['pageInfo']['endCursor'])
                comments = extra['node']['comments']
                nodes.extend(comments['nodes'])
            thread['comments'] = nodes
            threads.append(thread)
        if not connection['pageInfo']['hasNextPage']:
            break
        variables['cursor'] = connection['pageInfo']['endCursor']
    variables['cursor'] = None
    while True:
        data = await api.graphql(EVENTS, **variables)
        connection = data['repository']['pullRequest']['timelineItems']
        events.extend(connection['nodes'])
        if not connection['pageInfo']['hasNextPage']:
            break
        variables['cursor'] = connection['pageInfo']['endCursor']
    return threads, events


async def compare(api, repo, base, head):
    result, commits = None, []
    async for page in api.pages(f'/repos/{repo}/compare/{base}...{head}'):
        if result is None:
            result = dict(page)
        commits.extend(page['commits'])
    if result is None or len(commits) != result['total_commits']:
        raise ValueError('compare commit pagination incomplete')
    result['commits'] = commits
    return result


async def collect_pr(api, store, repo, number):
    prefix = f'/repos/{repo}/pulls/{number}'
    pr = await api.get(prefix)
    store.put('pr', repo, number, pr)
    cutoff = store.meta('cutoff')
    if not pr.get('closed_at') or pr['closed_at'] > cutoff:
        raise ValueError('PR state changed after index; snapshot cannot be reconstructed')
    lists = {}
    for kind, path in [('commits', prefix + '/commits'), ('files', prefix + '/files'),
                       ('reviews', prefix + '/reviews'), ('inline', prefix + '/comments'),
                       ('discussion', f'/repos/{repo}/issues/{number}/comments')]:
        values = await api.listing(path)
        if kind in ('reviews', 'inline', 'discussion'):
            values = [v for v in values if (v.get('created_at') or v.get('submitted_at') or '') <= cutoff]
        lists[kind] = values
        store.put(kind, repo, number, values)
    if len(lists['commits']) != pr['commits'] or pr['commits'] >= 250:
        compared = await compare(api, repo, pr['base']['sha'], pr['head']['sha'])
        if len(compared['commits']) != pr['commits']:
            raise ValueError('PR commit limit fallback disagrees with PR commit count')
        lists['commits'] = compared['commits']
        store.put('commits', repo, number, lists['commits'])
        store.put('commit_list_fallback', repo, number, compared)
    store.put('final_files_status', repo, number, {
        'api_count': len(lists['files']), 'expected': pr['changed_files'],
        'complete': len(lists['files']) == pr['changed_files'] and len(lists['files']) < 3000})
    threads, events = await graph_history(api, repo, number)
    store.put('threads', repo, number, threads)
    store.put('events', repo, number, events)
    refs = {pr['base']['sha'], pr['head']['sha']}
    refs.update(v['sha'] for v in lists['commits'])
    refs.update(c.get('original_commit_id') for c in lists['inline'])
    refs.update(c.get('commit_id') for c in lists['inline'])
    for event in events:
        refs.update((event.get(k) or {}).get('oid') for k in ('beforeCommit', 'afterCommit'))
    # Commit list entries already preserve reachable historical revisions. Fetch other objects explicitly.
    known = {v['sha']: v for v in lists['commits']}
    history = {}
    for sha in sorted(refs - {None}):
        if sha in known:
            history[sha] = {'state': 'available', 'origin': 'pr_commit_list'}
            store.put('revision', repo, sha, known[sha])
            continue
        try:
            commit = await api.get(f'/repos/{repo}/commits/{sha}')
        except APIError as exc:
            if exc.status not in (404, 410, 422):
                raise
            history[sha] = {'state': 'unavailable', 'reason': str(exc)}
        else:
            store.put('revision', repo, sha, commit)
            history[sha] = {'state': 'available', 'origin': 'commit_api',
                            'commit_files_may_be_capped': True}
    store.put('history', repo, number, history)
    log.info('Collected %s#%s (%s revisions)', repo, number, len(history))


async def collect_candidates(api, store, candidates, materialize):
    ready = asyncio.Event()
    collection_done = asyncio.Event()
    material_keys = {f'material:{repo}#{number}': (repo, number) for repo, number in candidates}

    def enqueue_material(repo, number):
        if materialize is None:
            return
        key = f'material:{repo}#{number}'
        task = store.task(key)
        if task and task['state'] == 'failed' and (task['reason'] or '').startswith('archive_tree_hash_mismatch:'):
            # Fixed-SHA archives already failed tree verification; unchanged inputs cannot repair them.
            return
        if not task or task['state'] != 'complete':
            store.task(key, 'pending', task['reason'] if task else None)
            ready.set()

    # SQLite is the durable backlog: slow construction never blocks API workers on queue capacity.
    remaining = []
    for repo, number in candidates:
        task = store.task(f'pr:{repo}#{number}')
        if task and task['state'] == 'complete':
            enqueue_material(repo, number)
        else:
            remaining.append((repo, number))

    async def fetch(item):
        repo, number = item
        key = f'pr:{repo}#{number}'
        await guarded(store, key, lambda: collect_pr(api, store, repo, number))
        if store.task(key)['state'] == 'complete':
            enqueue_material(repo, number)

    async def produce():
        try:
            await workers(remaining, fetch)
        finally:
            collection_done.set()
            ready.set()

    async def construct():
        while True:
            ready.clear()
            key = next((row['key'] for row in store.db.execute(
                "SELECT key FROM tasks WHERE state='pending' AND key LIKE 'material:%' ORDER BY key")
                if row['key'] in material_keys), None)
            if key is None:
                if collection_done.is_set():
                    return
                await ready.wait()
                continue
            repo, number = material_keys[key]
            # No await between selecting a pending task and guarded marking it running.
            await guarded(store, key, lambda: materialize(api, store, repo, number))
            await asyncio.sleep(0)

    tasks = [asyncio.create_task(produce())]
    if materialize is not None:
        tasks.extend(asyncio.create_task(construct()) for _ in range(4))
    log.info('Pipeline started: 4 collection workers, %s construction workers, %s PRs awaiting collection',
             4 if materialize is not None else 0, len(remaining))
    try:
        await asyncio.gather(*tasks)
    except BaseException:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        raise


async def collect(api, store, *, only=None, materialize=None):
    repos = [r['full_name'] for r in store.meta('input_rows') if not r['duplicate']]
    if only:
        repos = [r for r in repos if r.lower() in {v.lower() for v in only}]
        if not repos:
            raise ValueError('Requested repository is not in Excel')
    await workers(repos, lambda repo: guarded(store, 'index:' + repo,
                                            lambda: index_repository(api, store, repo)))
    candidates = set()
    canonical = {id for original, id, _ in store.items('repository') if original in repos}
    for repo in sorted(canonical):
        if not store.get('index_progress', repo, 'complete'):
            continue
        closed_numbers = {row['id'] for row in store.db.execute(
            "SELECT id FROM entities WHERE kind='pr_index' AND repo=?", (repo,))}
        for _, _, comment in store.items('comment_index', repo):
            if is_bot(comment):
                continue
            match = re.search(r'/pulls/(\d+)$', comment['pull_request_url'])
            if match and match[1] in closed_numbers:
                candidates.add((repo, int(match[1])))
    for repo, number in sorted(candidates):
        if store.task(f'pr:{repo}#{number}') is None:
            store.task(f'pr:{repo}#{number}', 'pending')
    await collect_candidates(api, store, sorted(candidates), materialize)

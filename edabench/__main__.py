import argparse
import asyncio
from contextlib import contextmanager
import fcntl
import json
import logging
import sys

from .build import build, status
from .collect import collect, collect_pr, guarded, initialize
from .github import AuthenticationError, GitHub
from .inputs import token
from .material import materialize
from .storage import Store, digest


@contextmanager
def writer_lock(root):
    with (root / '.writer.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError('Another collect/run/build process owns this data directory') from None
        yield


async def network(args, store):
    initialize(store, args.excel)
    before = digest(args.config)
    api = GitHub(store, token(args.config))
    try:
        if args.pr:
            if not args.repo or len(args.repo) != 1:
                raise ValueError('--pr requires exactly one --repo from Excel')
            repo = args.repo[0]
            if repo.lower() not in {r['full_name'].lower() for r in store.meta('input_rows')}:
                raise ValueError('Requested repository is not in Excel')
            repo = next(r['full_name'] for r in store.meta('input_rows') if r['full_name'].lower() == repo.lower())
            metadata = await api.get(f'/repos/{repo}')
            store.put('repository', repo, metadata['full_name'], metadata)
            repo = metadata['full_name']
            for number in args.pr:
                key = f'pr:{repo}#{number}'
                await guarded(store, key, lambda: collect_pr(api, store, repo, number))
                if store.task(key)['state'] == 'complete':
                    await guarded(store, f'material:{repo}#{number}', lambda: materialize(api, store, repo, number))
        else:
            await collect(api, store, only=args.repo, materialize=materialize)
    finally:
        await api.close()
        if digest(args.config) != before:
            raise ValueError('Credential file changed during execution')


def main():
    parser = argparse.ArgumentParser(description='Collect and rebuild raw revision-aligned EDA reviews')
    parser.add_argument('command', choices=['run', 'collect', 'build', 'status'])
    parser.add_argument('--data', default='data')
    parser.add_argument('--excel', default='docs/final_repository.xlsx')
    parser.add_argument('--config', default='config/github.yaml')
    parser.add_argument('--repo', action='append', help='Limit online validation to an Excel repository (repeatable)')
    parser.add_argument('--pr', type=int, action='append', help='Fetch only these PRs for small-sample validation; requires one --repo')
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(name)s %(message)s')
    logging.getLogger('httpx').setLevel(logging.WARNING)
    store = Store(args.data)
    try:
        if args.command == 'status':
            result = status(store)
        else:
            with writer_lock(store.root):
                if args.command in ('run', 'collect'):
                    asyncio.run(network(args, store))
                if args.command in ('run', 'build'):
                    result = build(store)
                else:
                    result = status(store)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if args.command in ('run', 'collect') and status(store)['failed_tasks']:
            return 2
        return 0
    except AuthenticationError as exc:
        print(str(exc), file=sys.stderr)
        return 3
    except (ValueError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print('Interrupted; cached pages and unfinished tasks will resume on the next run.', file=sys.stderr)
        return 130
    finally:
        store.close()


if __name__ == '__main__':
    sys.exit(main())

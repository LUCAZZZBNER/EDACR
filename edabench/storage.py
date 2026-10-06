import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def now():
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def dumps(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class Store:
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.root / 'state.sqlite3')
        self.db.row_factory = sqlite3.Row
        self.db.executescript('''
            PRAGMA journal_mode=WAL;
            PRAGMA synchronous=NORMAL;
            PRAGMA busy_timeout=30000;
            CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS responses(
                key TEXT PRIMARY KEY, status INTEGER, body TEXT, headers TEXT, fetched_at TEXT);
            CREATE TABLE IF NOT EXISTS entities(
                kind TEXT, repo TEXT, id TEXT, body TEXT,
                PRIMARY KEY(kind, repo, id));
            CREATE TABLE IF NOT EXISTS tasks(
                key TEXT PRIMARY KEY, state TEXT, reason TEXT, updated_at TEXT);
            CREATE INDEX IF NOT EXISTS tasks_state_key ON tasks(state, key);
        ''')
        self.db.commit()

    def meta(self, key, value=None):
        if value is not None:
            self.db.execute('INSERT OR REPLACE INTO meta VALUES (?,?)', (key, dumps(value)))
            self.db.commit()
        row = self.db.execute('SELECT value FROM meta WHERE key=?', (key,)).fetchone()
        return json.loads(row[0]) if row else None

    def put(self, kind, repo, id, body):
        self.db.execute('INSERT OR REPLACE INTO entities VALUES (?,?,?,?)',
                        (kind, repo, str(id), dumps(body)))
        self.db.commit()

    def put_many(self, kind, repo, records):
        self.db.executemany(
            'INSERT OR REPLACE INTO entities VALUES (?,?,?,?)',
            [(kind, repo, str(id), dumps(body)) for id, body in records])
        self.db.commit()

    def get(self, kind, repo, id):
        row = self.db.execute('SELECT body FROM entities WHERE kind=? AND repo=? AND id=?',
                              (kind, repo, str(id))).fetchone()
        return json.loads(row[0]) if row else None

    def items(self, kind, repo=None):
        sql = 'SELECT repo,id,body FROM entities WHERE kind=?'
        args = [kind]
        if repo is not None:
            sql += ' AND repo=?'
            args.append(repo)
        for row in self.db.execute(sql + ' ORDER BY repo,id', args):
            yield row['repo'], row['id'], json.loads(row['body'])

    def task(self, key, state=None, reason=None):
        if state is not None:
            self.db.execute('INSERT OR REPLACE INTO tasks VALUES (?,?,?,?)',
                            (key, state, reason, now()))
            self.db.commit()
        row = self.db.execute('SELECT * FROM tasks WHERE key=?', (key,)).fetchone()
        return dict(row) if row else None

    def cached(self, key):
        row = self.db.execute('SELECT * FROM responses WHERE key=?', (key,)).fetchone()
        if row:
            return row['status'], json.loads(row['body']), json.loads(row['headers'])

    def cache(self, key, status, body, headers):
        self.db.execute('INSERT OR REPLACE INTO responses VALUES (?,?,?,?,?)',
                        (key, status, dumps(body), dumps(headers), now()))
        self.db.commit()

    def close(self):
        self.db.close()

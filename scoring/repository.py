"""Local SQLite storage for immutable targeting and lead-scoring runs."""
import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

STORE = Path(__file__).resolve().parents[1] / 'data' / 'lead_scoring.sqlite3'


@contextmanager
def connection():
    STORE.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(STORE, timeout=15)
    try:
        db.execute('PRAGMA busy_timeout=15000')
        db.execute('CREATE TABLE IF NOT EXISTS scoring_documents (kind TEXT NOT NULL, id TEXT NOT NULL, created_at TEXT NOT NULL, payload TEXT NOT NULL, PRIMARY KEY(kind, id))')
        with db:
            yield db
    finally:
        db.close()


def save(kind, document):
    with connection() as db:
        db.execute('INSERT INTO scoring_documents VALUES (?, ?, ?, ?) ON CONFLICT(kind,id) DO UPDATE SET payload=excluded.payload',
                   (kind, document['id'], document['created_at'], json.dumps(document, ensure_ascii=False, allow_nan=False)))


def get(kind, identifier):
    with connection() as db:
        row = db.execute('SELECT payload FROM scoring_documents WHERE kind=? AND id=?', (kind, identifier)).fetchone()
    return json.loads(row[0]) if row else None


def list_runs(limit=30):
    with connection() as db:
        rows = db.execute("SELECT payload FROM scoring_documents WHERE kind='run' ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
    return [{key: value for key, value in json.loads(row[0]).items()
             if key in {'id', 'created_at', 'status', 'total', 'processed', 'matched', 'failed', 'targeting_description', 'model', 'source_list'}} for row in rows]


def list_lead_lists():
    with connection() as db:
        rows = db.execute("SELECT payload FROM scoring_documents WHERE kind='lead_list' ORDER BY created_at DESC").fetchall()
    summaries = []
    for row in rows:
        document = json.loads(row[0])
        summaries.append({key: document.get(key) for key in
                          ('id', 'name', 'version', 'created_at', 'updated_at', 'member_count', 'latest_run_id')})
    return summaries


def mutate_list(identifier, expected_version, change):
    """Serialize membership changes and preserve previous list revisions."""
    with connection() as db:
        db.execute('BEGIN IMMEDIATE')
        row = db.execute("SELECT payload FROM scoring_documents WHERE kind='lead_list' AND id=?", (identifier,)).fetchone()
        if row is None:
            raise KeyError(identifier)
        document = json.loads(row[0])
        if expected_version is not None and document['version'] != expected_version:
            raise ValueError('This list changed since you opened it. Refresh it before continuing.')
        original = json.loads(row[0])
        change(document)
        if document['version'] != original['version']:
            revision_id = identifier + ':v' + str(original['version'])
            db.execute('INSERT OR IGNORE INTO scoring_documents VALUES (?, ?, ?, ?)',
                       ('list_revision', revision_id, original['created_at'], json.dumps(original, ensure_ascii=False)))
        db.execute("UPDATE scoring_documents SET payload=? WHERE kind='lead_list' AND id=?",
                   (json.dumps(document, ensure_ascii=False, allow_nan=False), identifier))
    return document


def recover_interrupted():
    # A single local backend process owns in-process background tasks. On restart
    # unfinished items remain retryable errors, never silently become non-matches.
    with connection() as db:
        rows = db.execute("SELECT id,payload FROM scoring_documents WHERE kind='run'").fetchall()
        for identifier, payload in rows:
            run = json.loads(payload)
            if run['status'] not in {'queued', 'running'}:
                continue
            for result in run['results']:
                if result['status'] == 'pending':
                    result.update(status='failed', error='The backend restarted before this person was scored.')
            run.update(status='interrupted', processed=run['total'], failed=sum(r['status'] == 'failed' for r in run['results']))
            db.execute("UPDATE scoring_documents SET payload=? WHERE kind='run' AND id=?", (json.dumps(run, ensure_ascii=False), identifier))

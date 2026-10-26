import asyncio
from contextlib import contextmanager
import hashlib
import json
import os
import re
import sqlite3
from .policy import APIError, validate_action, validate_current_state
from .ha import UpstreamError


class Actions:
    def __init__(self, ha, options, directory, audit):
        self.ha, self.options, self.audit = ha, options, audit
        self.path = directory / 'actions.sqlite'
        with self.db() as db:
            db.execute('CREATE TABLE IF NOT EXISTS actions (key TEXT PRIMARY KEY, fingerprint TEXT, status INTEGER, response TEXT)')
        os.chmod(self.path, 0o600)
        self.lock = asyncio.Lock()

    @contextmanager
    def db(self):
        connection = sqlite3.connect(self.path)
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    async def execute(self, body, key):
        if not isinstance(key, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', key):
            raise APIError(400, 'idempotency_key_required')
        entity, service, data = validate_action(body, self.options)
        fingerprint = hashlib.sha256(json.dumps(body, sort_keys=True, allow_nan=False).encode()).hexdigest()
        async with self.lock:
            with self.db() as db:
                row = db.execute('SELECT fingerprint,status,response FROM actions WHERE key=?', (key,)).fetchone()
                if row:
                    if row[0] != fingerprint:
                        raise APIError(409, 'idempotency_conflict')
                    if row[1] is None:
                        raise APIError(409, 'action_outcome_unknown')
                    return row[1], json.loads(row[2])
                if db.execute('SELECT COUNT(*) FROM actions').fetchone()[0] >= 10000:
                    raise APIError(503, 'action_journal_full')
                db.execute('INSERT INTO actions VALUES (?,?,NULL,NULL)', (key, fingerprint))
            # Durable reservation before side effects. Interrupted requests are never repeated.
            try:
                before = await self.ha.state(entity)
                validate_current_state(service, data, before)
                self.audit.write('action', 'started')
                domain, name = service.split('.')
                result = await self.ha.service(domain, name, {**data, 'entity_id': entity})
                try:
                    after = await self.ha.state(entity)
                except UpstreamError:
                    after = None
                status, response = 200, {'accepted': True, 'before': before, 'after': after,
                                         'result': result, 'state_observed': after is not None}
                self.audit.write('action', 'accepted')
            except APIError as exc:
                status, response = exc.status, {'error': exc.code}
                self.audit.write('action', 'rejected')
            except UpstreamError:
                status, response = 502, {'error': 'upstream_unavailable', 'retry_with_new_key': False}
                self.audit.write('action', 'upstream_error')
            with self.db() as db:
                db.execute('UPDATE actions SET status=?,response=? WHERE key=?',
                           (status, json.dumps(response, allow_nan=False), key))
            return status, response

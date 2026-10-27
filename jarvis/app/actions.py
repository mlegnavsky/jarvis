import asyncio
from contextlib import contextmanager
import hashlib
import json
import os
import re
import sqlite3
import time
from .policy import APIError, validate_action, validate_current_state
from .ha import UpstreamError


class Actions:
    def __init__(self, ha, options, directory, audit, confirmation_timeout=1.2):
        self.ha, self.options, self.audit = ha, options, audit
        self.confirmation_timeout = confirmation_timeout
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
        started = time.monotonic()
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
                    return row[1], {**json.loads(row[2]), 'replayed': True}
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
                confirmation_started = time.monotonic()
                target = {'light.turn_on': 'on', 'light.turn_off': 'off'}.get(service)
                if service == 'light.turn_on' and data.get('brightness') == 0:
                    target = 'off'
                def matches(state):
                    return (state is not None and state.get('state') == target
                            and (target != 'on' or 'brightness' not in data
                                 or state.get('attributes', {}).get('brightness') == data['brightness']))
                after = None
                try:
                    if target is None:
                        after = await self.ha.state(entity)
                    else:
                        # Matter/Zigbee state reports can arrive after the service
                        # response. Confirm locally instead of another chat roundtrip.
                        async with asyncio.timeout(self.confirmation_timeout):
                            while True:
                                after = await self.ha.state(entity)
                                if matches(after):
                                    break
                                await asyncio.sleep(0.05)
                except (UpstreamError, TimeoutError):
                    pass
                status, response = 200, {'accepted': True, 'before': before, 'after': after,
                    'result': result, 'state_observed': after is not None,
                    'target_state_verified': matches(after) if target else None, 'replayed': False,
                    'confirmation_ms': round((time.monotonic()-confirmation_started)*1000),
                    'request_ms': round((time.monotonic()-started)*1000)}
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

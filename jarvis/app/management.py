"""Revision-checked editor automation changes with durable local before-images."""
import asyncio
from contextlib import contextmanager
import hashlib
import json
import os
import re
import sqlite3

from .ha import UpstreamError
from .policy import APIError

BRIDGE_SERVICES = {'jarvis.automation_save', 'jarvis.automation_delete', 'jarvis.automation_restore',
                   'jarvis.automation_get', 'jarvis.automations', 'jarvis.automation_backups', 'jarvis.diagnostics'}


def encoded(value):
    return json.dumps(value, sort_keys=True, allow_nan=False, separators=(',', ':'))


def revision(config):
    return 'missing' if config is None else hashlib.sha256(encoded(config).encode()).hexdigest()


class Management:
    def __init__(self, ha, options, directory, audit):
        self.ha, self.options, self.audit = ha, options, audit
        self.path = directory / 'management.sqlite'
        self.lock = asyncio.Lock()
        with self.db() as db:
            db.execute('CREATE TABLE IF NOT EXISTS changes (key TEXT PRIMARY KEY, fingerprint TEXT, '
                       'identifier TEXT, before_config TEXT, status INTEGER, response TEXT)')
        os.chmod(self.path, 0o600)

    @contextmanager
    def db(self):
        connection = sqlite3.connect(self.path)
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def allowed(self, write=False):
        if self.options.get('maintenance_enabled') is not True:
            raise APIError(403, 'maintenance_disabled')
        if write and self.options.get('writes_enabled') is not True:
            raise APIError(403, 'writes_disabled')

    async def get(self, identifier):
        self.allowed()
        config = await self.ha.automation('GET', identifier)
        return {'id': identifier, 'config': config, 'revision': revision(config)}

    async def diagnostics(self, check=False):
        self.allowed()
        config = await self.ha.request('GET', '/core/api/config')
        # Omit coordinates, URLs, paths, and other account-specific config.
        result = {'configuration': {key: config[key] for key in
                  ('version', 'time_zone', 'unit_system', 'state', 'safe_mode', 'components') if key in config},
                  'stream_connected': self.ha.stream_connected}
        with self.db() as db:
            used = db.execute('SELECT COUNT(*) FROM changes').fetchone()[0]
        result['management_journal'] = {'used': used, 'limit': 1000, 'remaining': max(0, 1000-used)}
        if check:
            result['validation'] = await self.ha.request('POST', '/core/api/config/core/check_config', {})
        return result

    async def list(self):
        self.allowed()
        states = await self.ha.request('GET', '/core/api/states')
        items = [{'entity_id': item['entity_id'], 'state': item.get('state'),
                          'id': item.get('attributes', {}).get('id'),
                          'name': item.get('attributes', {}).get('friendly_name')}
                         for item in states if item.get('entity_id', '').startswith('automation.')]
        return {'items': items[:500], 'total': len(items), 'truncated': len(items) > 500}

    def backups(self):
        self.allowed()
        with self.db() as db:
            rows = db.execute('SELECT key,identifier,before_config,status,response FROM changes ORDER BY rowid DESC LIMIT 100').fetchall()
        return {'items': [{'backup_id': key, 'id': identifier, 'before_revision': revision(json.loads(before)),
                           'status': status, 'result': json.loads(response) if response else None}
                          for key, identifier, before, status, response in rows]}

    async def action_bridge(self, args):
        """Compatibility transport; caller must verify BOTH control and maintain scopes."""
        service, entity, data = args['service'], args['entity_id'], args['data']
        if service not in BRIDGE_SERVICES:
            raise APIError(400, 'invalid_management_service')
        if service in {'jarvis.diagnostics', 'jarvis.automations', 'jarvis.automation_backups'}:
            if entity != 'jarvis.system' or set(data) - ({'check_config'} if service == 'jarvis.diagnostics' else set()):
                raise APIError(400, 'invalid_management_request')
            if 'check_config' in data and type(data['check_config']) is not bool:
                raise APIError(400, 'invalid_management_request')
            if service == 'jarvis.diagnostics':
                return 200, await self.diagnostics(data.get('check_config', False))
            return 200, await self.list() if service == 'jarvis.automations' else self.backups()
        if not entity.startswith('automation.'):
            raise APIError(400, 'invalid_automation_target')
        identifier = entity[len('automation.'):]
        if service == 'jarvis.automation_get':
            if data:
                raise APIError(400, 'invalid_management_request')
            return 200, await self.get(identifier)
        operation = service.removeprefix('jarvis.automation_')
        required = {'expected_revision'} | ({'config'} if operation == 'save' else set()) | ({'backup_id'} if operation == 'restore' else set())
        if set(data) != required:
            raise APIError(400, 'invalid_management_request')
        return await self.change(operation, identifier, data['expected_revision'], data.get('config', {}),
                                 args['request_id'], data.get('backup_id'))

    async def change(self, operation, identifier, expected_revision, config, key, backup_id=None):
        self.allowed(write=True)
        if (operation not in ('save', 'delete', 'restore') or not isinstance(identifier, str)
                or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', identifier)
                or not isinstance(key, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', key)
                or not isinstance(expected_revision, str)
                or not re.fullmatch(r'missing|[a-f0-9]{64}', expected_revision)
                or not isinstance(config, dict)):
            raise APIError(400, 'invalid_management_request')
        if len(encoded(config).encode()) > 12000:
            raise APIError(400, 'automation_config_too_large')
        if operation == 'save' and (config.get('initial_state') is not False
                or 'id' in config and config['id'] != identifier or not config.get('alias')):
            raise APIError(400, 'disabled_automation_required')
        if operation != 'save' and config:
            raise APIError(400, 'unexpected_automation_config')
        if operation == 'restore':
            if not isinstance(backup_id, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', backup_id):
                raise APIError(400, 'backup_id_required')
        elif backup_id is not None:
            raise APIError(400, 'unexpected_backup_id')
        fingerprint = hashlib.sha256(encoded([operation, identifier, expected_revision, config, backup_id]).encode()).hexdigest()
        async with self.lock:
            with self.db() as db:
                row = db.execute('SELECT fingerprint,status,response FROM changes WHERE key=?', (key,)).fetchone()
                if row:
                    if row[0] != fingerprint:
                        raise APIError(409, 'idempotency_conflict')
                    if row[1] is None:
                        raise APIError(409, 'management_outcome_unknown')
                    return row[1], json.loads(row[2])
                if db.execute('SELECT COUNT(*) FROM changes').fetchone()[0] >= 1000:
                    raise APIError(503, 'management_journal_full')
                desired = None if operation == 'delete' else {**config, 'id': identifier}
                if operation == 'restore':
                    backup = db.execute('SELECT identifier,before_config FROM changes WHERE key=?', (backup_id,)).fetchone()
                    if not backup or backup[0] != identifier:
                        raise APIError(404, 'backup_not_found')
                    desired = json.loads(backup[1])
                    if desired is not None:
                        desired['initial_state'] = False
            before = await self.ha.automation('GET', identifier)
            if revision(before) != expected_revision:
                raise APIError(409, 'automation_revision_conflict')
            with self.db() as db:
                db.execute('INSERT INTO changes VALUES (?,?,?,?,NULL,NULL)',
                           (key, fingerprint, identifier, encoded(before)))
            # Committed before-image and reservation precede all side effects.
            self.audit.write('automation_config', 'started')
            try:
                if desired is None:
                    if before is not None:
                        await self.ha.automation('DELETE', identifier)
                else:
                    await self.ha.automation('POST', identifier, desired)
                after = await self.ha.automation('GET', identifier)
                verified = after == desired
                status = 200 if verified else 502
                response = {'id': identifier, 'verified': verified, 'backup_id': key,
                            'revision': revision(after), 'execution_verified': False}
                if not verified:
                    response['error'] = 'automation_readback_mismatch'
            except APIError as error:
                status, response = error.status, {'error': error.code, 'verified': False, 'backup_id': key}
            except UpstreamError:
                status, response = 502, {'error': 'management_outcome_unknown', 'verified': False,
                                         'backup_id': key, 'retry_with_new_key': False}
            with self.db() as db:
                db.execute('UPDATE changes SET status=?,response=? WHERE key=?', (status, encoded(response), key))
            self.audit.write('automation_config', 'verified' if response['verified'] else 'unverified')
            return status, response

"""Explicit Supervisor and config-file operations, never a shell or URL proxy."""
import asyncio
from contextlib import contextmanager
import hashlib
import json
import os
import re
import sqlite3
from .config_files import ConfigFiles
from .ha import now
from . import diagnostics
from .ha import UpstreamError
from .policy import APIError

FIELDS = {
    'automations_reload': {'expected_revision'},
    'device_metadata': {'device_id', 'area_id', 'name_by_user', 'expected_revision'},
    'addon_install': {'slug', 'expected_version'}, 'addon_update': {'slug', 'expected_version'},
    'addon_start': {'slug', 'expected_version'}, 'addon_stop': {'slug', 'expected_version'},
    'addon_restart': {'slug', 'expected_version'},
    'addon_uninstall': {'slug', 'expected_version'},
    'repository_add': {'repository_url'},
    'addon_options_restore': {'slug', 'backup_id', 'expected_revision'},
    'addon_options': {'slug', 'expected_revision', 'changes'},
    'core_restart': set(), 'core_update': {'version'}, 'backup_create': set(),
    'backup_restore': {'backup_slug', 'target'},
    'file_write': {'path', 'content', 'expected_revision'},
    'file_delete': {'path', 'expected_revision'}, 'file_restore': {'backup_id', 'expected_revision'},
}


def encode(value):
    return json.dumps(value, sort_keys=True, allow_nan=False)


def revision(value):
    return hashlib.sha256(encode(value).encode()).hexdigest()


def slug(value):
    if not isinstance(value, str) or not re.fullmatch(r'[a-z0-9][a-z0-9_.-]{0,127}', value):
        raise APIError(400, 'invalid_admin_target')
    return value


def repository_url(value):
    if not isinstance(value, str) or not re.fullmatch(r'https://github\.com/[A-Za-z0-9][A-Za-z0-9_.-]{0,99}/[A-Za-z0-9][A-Za-z0-9_.-]{0,99}/?', value):
        raise APIError(400, 'invalid_repository_url')
    return value.rstrip('/')


def redact(value):
    if isinstance(value, dict):
        return {k: '<redacted>' if re.search(r'password|secret|token|credential|api.?key|private.?key', k, re.I)
                else redact(v) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v) for v in value]
    if isinstance(value, str) and diagnostics.SUSPECT.search(value):
        return '<redacted>'
    return value


def addon_summary(info):
    return {k: info[k] for k in ('slug', 'name', 'version', 'version_latest', 'state', 'boot', 'auto_update',
                                'installed', 'available', 'update_available', 'repository') if k in info}


class Admin:
    def __init__(self, supervisor, options, directory, audit, files=None):
        self.sup, self.options, self.audit = supervisor, options, audit
        self.files = files or ConfigFiles()
        self.path = directory / 'admin.sqlite'
        self.tasks = set()
        self.lock = asyncio.Lock()
        with self.db() as db:
            db.execute('CREATE TABLE IF NOT EXISTS jobs (key TEXT PRIMARY KEY, fingerprint TEXT, operation TEXT, '
                       'arguments TEXT, state TEXT, result TEXT, backup_slug TEXT, before_data TEXT)')
            columns = {row[1] for row in db.execute('PRAGMA table_info(jobs)')}
            for name in ('created_at', 'started_at', 'finished_at', 'summary'):
                if name not in columns:
                    db.execute('ALTER TABLE jobs ADD COLUMN '+name+' TEXT')
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

    def job(self, key):
        self.allowed()
        with self.db() as db:
            row = db.execute('SELECT operation,state,result,backup_slug,created_at,started_at,finished_at,summary FROM jobs WHERE key=?', (key,)).fetchone()
        if not row:
            raise APIError(404, 'admin_job_not_found')
        return {'id': key, 'operation': row[0], 'state': row[1],
                'result': json.loads(row[2]) if row[2] else None, 'backup_slug': row[3],
                'request_id': key, 'created_at': row[4], 'started_at': row[5], 'finished_at': row[6],
                'summary': json.loads(row[7]) if row[7] else None}

    async def read(self, query, target=''):
        self.allowed()
        if not isinstance(query, str) or not isinstance(target, str) or len(target) > 400:
            raise APIError(400, 'invalid_admin_query')
        if query == 'diagnostics':
            return await diagnostics.diagnose(self.sup)
        if query == 'device':
            devices, entities, areas = await asyncio.gather(self.sup.registry('device'), self.sup.registry('entity'), self.sup.registry('area'))
            device = next((d for d in devices if d.get('id') == target), None)
            if device is None:
                raise APIError(404, 'device_not_found')
            metadata = {k: device.get(k) for k in ('area_id', 'name_by_user')}
            return {'device': diagnostics.select(device, ('id', 'name', 'name_by_user', 'area_id', 'manufacturer', 'model')),
                    'revision': revision(metadata), 'areas': areas,
                    'entities': [diagnostics.select(e, ('id', 'entity_id', 'name', 'original_name', 'area_id', 'disabled_by')) for e in entities if e.get('device_id') == target]}
        if query == 'permission_map':
            return await diagnostics.permission_map(self.sup, self.options)
        if query in ('core_logs', 'addon_logs', 'supervisor_logs'):
            path = '/addons/'+slug(target)+'/logs' if query == 'addon_logs' else ('/core/logs' if query == 'core_logs' else '/supervisor/logs')
            return await diagnostics.stage(lambda: diagnostics.logs(self.sup, path), lambda v: v)
        if query == 'repositories':
            value = await self.sup.request('GET', '/store/repositories')
            items = value if isinstance(value, list) else value.get('repositories', [])
            return {'items': [redact(diagnostics.select(i, ('slug', 'name', 'source'))) for i in items[:100]],
                    'total': len(items), 'truncated': len(items)>100}
        if query == 'store_addon':
            value = await self.sup.request('GET', '/store/addons/'+slug(target))
            return {**addon_summary(value), **diagnostics.select(value, ('description', 'arch', 'homeassistant', 'stage', 'build'))}
        if query == 'file':
            return self.files.read(target)
        if query == 'files':
            return self.files.inventory()
        if query == 'job':
            return self.job(target)
        if query == 'jobs':
            with self.db() as db:
                keys = [r[0] for r in db.execute('SELECT key FROM jobs ORDER BY rowid DESC LIMIT 100')]
            return {'items': [self.job(key) for key in keys]}
        if query == 'config_check':
            await self.sup.request('POST', '/core/check', {})
            return {'valid': True}
        if query == 'addon':
            info = await self.sup.request('GET', '/addons/'+slug(target)+'/info')
            return {**addon_summary(info), 'options': redact(info.get('options', {})),
                    'options_revision': revision(info.get('options', {})), 'schema': info.get('schema')}
        if query in ('addons', 'store'):
            info = await self.sup.request('GET', '/addons' if query == 'addons' else '/store/addons')
            items = info.get('addons', [])
            return {'items': [addon_summary(i) for i in items[:500]], 'total': len(items), 'truncated': len(items)>500}
        if query == 'backups':
            info = await self.sup.request('GET', '/backups')
            return {'items': [{k: i[k] for k in ('slug', 'name', 'date', 'size', 'type', 'protected') if k in i}
                              for i in info.get('backups', [])[:100]]}
        if query == 'overview':
            own = await self.sup.request('GET', '/addons/self/info')
            core = await self.sup.request('GET', '/core/info')
            addons = await self.read('addons')
            return {'jarvis': addon_summary(own), 'core': {k: core[k] for k in
                    ('version', 'version_latest', 'state', 'arch', 'machine') if k in core},
                    'supervisor_api_reachable': True, 'config_mount_available': self.files.root.is_dir(),
                    'addons': addons, 'supported_changes': sorted(FIELDS)}
        raise APIError(400, 'invalid_admin_query')

    def validate(self, operation, args, key):
        if not isinstance(operation, str) or operation not in FIELDS or not isinstance(args, dict) or set(args) != FIELDS[operation]:
            raise APIError(400, 'invalid_admin_operation')
        if not isinstance(key, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', key):
            raise APIError(400, 'idempotency_key_required')
        if len(encode(args).encode()) > 400*1024:
            raise APIError(400, 'admin_request_too_large')
        for field in ('slug', 'backup_slug'):
            if field in args:
                slug(args[field])
        if 'backup_id' in args and (not isinstance(args['backup_id'], str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', args['backup_id'])):
            raise APIError(400, 'invalid_admin_backup_id')
        for field in ('expected_version', 'version'):
            if field in args and (not isinstance(args[field], str) or not re.fullmatch(r'[0-9][A-Za-z0-9._-]{0,63}', args[field])):
                raise APIError(400, 'invalid_admin_version')
        if 'expected_revision' in args and (not isinstance(args['expected_revision'], str)
                or not re.fullmatch(r'missing|[a-f0-9]{64}', args['expected_revision'])):
            raise APIError(400, 'invalid_admin_revision')
        if 'repository_url' in args:
            repository_url(args['repository_url'])
        if 'changes' in args and not isinstance(args['changes'], dict):
            raise APIError(400, 'invalid_admin_options')
        if operation == 'device_metadata':
            for field in ('device_id', 'area_id'):
                if field == 'area_id' and args[field] is None:
                    continue
                if not isinstance(args[field], str) or not re.fullmatch(r'[a-zA-Z0-9_-]{1,128}', args[field]):
                    raise APIError(400, 'invalid_device_metadata')
            name = args['name_by_user']
            if name is not None and (not isinstance(name, str) or not 1 <= len(name) <= 150 or not name.isprintable()):
                raise APIError(400, 'invalid_device_metadata')
        if 'path' in args:
            self.files.parts(args['path'])
        if operation == 'file_write':
            self.files.validate(args['path'], args['content'])
        if operation == 'backup_restore' and args['target'] != 'homeassistant':
            slug(args['target'])

    async def start(self, operation, args, key):
        self.allowed(write=True)
        self.validate(operation, args, key)
        fingerprint = revision([operation, args])
        with self.db() as db:
            row = db.execute('SELECT fingerprint FROM jobs WHERE key=?', (key,)).fetchone()
            if row:
                if row[0] != fingerprint:
                    raise APIError(409, 'idempotency_conflict')
            else:
                if db.execute('SELECT COUNT(*) FROM jobs').fetchone()[0] >= 1000:
                    raise APIError(503, 'admin_journal_full')
                summary = {'operation': operation, 'target': args.get('slug', args.get('path', args.get('target', args.get('repository_url')))),
                           'changed_fields': sorted(args.get('changes', {})),
                           'expected_version': args.get('expected_version'), 'restore_from': args.get('backup_id')}
                db.execute('INSERT INTO jobs (key,fingerprint,operation,arguments,state,created_at,summary) VALUES (?,?,?,?,?,?,?)',
                           (key, fingerprint, operation, encode(args), 'queued', now(), encode(summary)))
        if not row:
            task = asyncio.create_task(self.run(key, operation, args))
            self.tasks.add(task)
            task.add_done_callback(self.tasks.discard)
        return self.job(key)

    def remember(self, key, before):
        with self.db() as db:
            row = db.execute('SELECT summary FROM jobs WHERE key=?', (key,)).fetchone()
            summary = json.loads(row[0]) if row and row[0] else {}
            summary['before_revision'] = revision(before.get('options', before))
            db.execute('UPDATE jobs SET before_data=?,summary=? WHERE key=?', (encode(before), encode(summary), key))

    async def backup(self, key, addon=None):
        info = await self.sup.request('POST', '/backups/new/partial', {
            'name': 'Jarvis before remote administration', 'addons': [addon] if addon else [],
            'homeassistant': addon is None, 'background': False})
        backup_slug = info.get('slug')
        if not isinstance(backup_slug, str) or not backup_slug:
            raise APIError(502, 'admin_backup_not_confirmed')
        with self.db() as db:
            db.execute('UPDATE jobs SET backup_slug=? WHERE key=?', (backup_slug, key))

    async def perform(self, key, operation, args):
        self.allowed(write=True)
        if operation == 'automations_reload':
            before = self.files.read('automations.yaml')
            if before['revision'] != args['expected_revision']:
                raise APIError(409, 'config_revision_conflict')
            self.remember(key, before)
            await self.sup.request('POST', '/core/api/services/automation/reload', {})
            after = self.files.read('automations.yaml')
            return {'verified': after['revision'] == args['expected_revision'], 'revision': after['revision'],
                    'activation_performed': True}
        if operation == 'device_metadata':
            before = await self.read('device', args['device_id'])
            if before['revision'] != args['expected_revision']:
                raise APIError(409, 'device_metadata_changed')
            if args['area_id'] is not None and not any(a['area_id'] == args['area_id'] for a in before['areas']):
                raise APIError(404, 'area_not_found')
            self.remember(key, before)
            desired = {k: args[k] for k in ('area_id', 'name_by_user')}
            await diagnostics.websocket_query(self.sup, 'config/device_registry/update', {'device_id': args['device_id'], **desired})
            after = await self.read('device', args['device_id'])
            return {'verified': all(after['device'].get(k) == v for k, v in desired.items()),
                    'device': after['device'], 'revision': after['revision'], 'backup_id': key}
        if operation.startswith('file_'):
            desired = args.get('content') if operation == 'file_write' else None
            name = args.get('path')
            if operation == 'file_restore':
                with self.db() as db:
                    row = db.execute('SELECT operation,before_data FROM jobs WHERE key=?', (args['backup_id'],)).fetchone()
                if not row or not row[0].startswith('file_') or not row[1]:
                    raise APIError(404, 'admin_file_backup_not_found')
                saved = json.loads(row[1])
                name, desired = saved['path'], saved['content']
            before = self.files.read(name)
            if before['revision'] != args['expected_revision']:
                raise APIError(409, 'config_revision_conflict')
            self.remember(key, before)
            return {**self.files.write(name, desired, args['expected_revision']), 'backup_id': key,
                    'activation_performed': False}
        if operation == 'repository_add':
            url = repository_url(args['repository_url'])
            await self.sup.request('POST', '/store/repositories', {'repository': url})
            repos = await self.sup.request('GET', '/store/repositories')
            return {'verified': any(i.get('source', '').rstrip('/') == url for i in (repos if isinstance(repos, list) else repos.get('repositories', []))),
                    'repository_url': url}
        own = (await self.sup.request('GET', '/addons/self/info'))['slug']
        target = args.get('slug')
        if target == 'self':
            target = own
        if target == own and operation not in ('addon_options', 'addon_options_restore'):
            raise APIError(409, 'use_jarvis_updater_for_self')
        if operation == 'addon_stop' and target == own.rsplit('_jarvis', 1)[0]+'_jarvis_updater':
            raise APIError(409, 'updater_stop_protected')
        if operation in ('addon_uninstall', 'addon_options_restore'):
            installed = await self.sup.request('GET', '/addons')
            details = next((i for i in installed.get('addons', []) if i.get('slug') == target), {})
            protected = target in (own, own.rsplit('_jarvis', 1)[0]+'_jarvis_updater') or re.search(
                r'cloudflar|cloudflared|tunnel|tailscale|wireguard|zerotier|nginx|proxy', target+' '+str(details.get('name', '')), re.I)
            if protected:
                raise APIError(409, 'admin_connectivity_target_protected')
            if not details:
                raise APIError(404, 'admin_addon_not_installed')
        if operation.startswith('addon_'):
            if operation == 'addon_install':
                installed = await self.sup.request('GET', '/addons')
                if any(i.get('slug') == target for i in installed.get('addons', [])):
                    raise APIError(409, 'addon_already_installed')
                offered = await self.sup.request('GET', '/store/addons/'+target)
                if (offered.get('version_latest') or offered.get('version')) != args['expected_version']:
                    raise APIError(409, 'addon_version_changed')
                await self.backup(key)
                latest = await self.sup.request('GET', '/store/addons/'+target)
                if (latest.get('version_latest') or latest.get('version')) != args['expected_version']:
                    raise APIError(409, 'addon_version_changed')
                await self.sup.request('POST', '/store/addons/'+target+'/install', {'background': False})
            else:
                before = await self.sup.request('GET', '/addons/'+target+'/info')
                self.remember(key, before)
                if operation in ('addon_options', 'addon_options_restore'):
                    current = before.get('options', {})
                    if revision(current) != args['expected_revision']:
                        raise APIError(409, 'addon_options_changed')
                    if operation == 'addon_options_restore':
                        with self.db() as db:
                            row = db.execute('SELECT operation,before_data FROM jobs WHERE key=?', (args['backup_id'],)).fetchone()
                        saved = json.loads(row[1]) if row and row[1] else {}
                        if not row or row[0] not in ('addon_options', 'addon_options_restore') or saved.get('slug') != target or not isinstance(saved.get('options'), dict):
                            raise APIError(404, 'admin_options_backup_not_found')
                        desired = saved['options']
                    else:
                        desired = {**current, **args['changes']}
                    if target == own and set(args.get('changes', {})) - {'allowed_entities', 'allowed_services'}:
                        raise APIError(403, 'self_credentials_and_connection_protected')
                    validation = await self.sup.request('POST', '/addons/'+target+'/options/validate', desired)
                    if validation.get('valid') is not True:
                        raise APIError(400, 'addon_options_invalid')
                elif (before.get('version_latest') if operation == 'addon_update' else before.get('version')) != args['expected_version']:
                    raise APIError(409, 'addon_version_changed')
                await self.backup(key, target)
                latest = await self.sup.request('GET', '/addons/'+target+'/info')
                if operation in ('addon_options', 'addon_options_restore'):
                    if latest.get('options', {}) != current:
                        raise APIError(409, 'addon_options_changed')
                    await self.sup.request('POST', '/addons/'+target+'/options', {'options': desired})
                else:
                    verb = operation.removeprefix('addon_')
                    if (latest.get('version_latest') if verb == 'update' else latest.get('version')) != args['expected_version']:
                        raise APIError(409, 'addon_version_changed')
                    path = '/store/addons/'+target+'/update' if verb == 'update' else '/addons/'+target+'/'+verb
                    await self.sup.request('POST', path, {})
            if operation == 'addon_uninstall':
                installed = await self.sup.request('GET', '/addons')
                return {'verified': isinstance(installed.get('addons'), list) and not any(i.get('slug') == target for i in installed['addons']), 'slug': target,
                        'installed': any(i.get('slug') == target for i in installed.get('addons', []))}
            after = await self.sup.request('GET', '/addons/'+target+'/info')
            if operation in ('addon_options', 'addon_options_restore'):
                verified = after.get('options', {}) == desired
                if verified and target == own:
                    self.options.update(args.get('changes', {}))
                return {'verified': verified, 'addon': addon_summary(after), 'options_revision': revision(after.get('options', {})),
                        'activation_performed': target == own}
            expected_state = 'stopped' if operation == 'addon_stop' else 'started'
            verified = after.get('version') == args['expected_version']
            if operation == 'addon_update' and before.get('state') == 'started':
                verified = verified and after.get('state') == 'started'
            if operation in {'addon_start', 'addon_stop', 'addon_restart'}:
                verified = verified and after.get('state') == expected_state
            return {'verified': verified, 'addon': addon_summary(after)}
        if operation == 'backup_create':
            addons = await self.sup.request('GET', '/addons')
            info = await self.sup.request('POST', '/backups/new/partial', {'name': 'Jarvis remote system backup',
                'addons': [a['slug'] for a in addons.get('addons', [])], 'homeassistant': True, 'background': False})
            if not info.get('slug'):
                raise APIError(502, 'admin_backup_not_confirmed')
            return {'verified': True, 'backup_slug': info['slug'], 'scope': 'homeassistant_and_installed_addons'}
        if operation == 'backup_restore':
            target = args['target']
            if target == own or target == own.rsplit('_jarvis', 1)[0]+'_jarvis_updater':
                raise APIError(409, 'jarvis_recovery_requires_independent_path')
            await self.backup(key, None if target == 'homeassistant' else target)
            await self.sup.request('POST', '/backups/'+args['backup_slug']+'/restore/partial', {
                'homeassistant': target == 'homeassistant', 'addons': [] if target == 'homeassistant' else [target],
                'background': False})
            # A completed restore request alone cannot prove recovered configuration.
            return {'verified': False, 'accepted': True, 'verification_required': True, 'target': target}
        if operation in {'core_restart', 'core_update'}:
            await self.backup(key)
            await self.sup.request('POST', '/core/check', {})
            await self.sup.request('POST', '/core/'+('update' if operation == 'core_update' else 'restart'),
                                   {'version': args['version'], 'background': False} if operation == 'core_update' else {})
            info = await self.sup.request('GET', '/core/info')
            healthy = await self.sup.request('GET', '/core/api/config')
            verified = healthy.get('state') == 'RUNNING' and (operation != 'core_update' or info.get('version') == args['version'])
            return {'verified': verified, 'core_version': info.get('version'), 'core_state': healthy.get('state')}
        raise APIError(400, 'invalid_admin_operation')

    async def run(self, key, operation, args):
        async with self.lock:
            with self.db() as db:
                db.execute("UPDATE jobs SET state='running',started_at=? WHERE key=?", (now(), key))
            self.audit.write('administration', 'started')
            try:
                result = await self.perform(key, operation, args)
                state = 'verified' if result.get('verified') is True else 'unverified'
            except APIError as error:
                state, result = 'failed', {'error': error.code}
            except UpstreamError:
                state, result = 'unknown', {'error': 'admin_upstream_outcome_unknown', 'retry_with_new_key': False}
            except Exception:
                state, result = 'unknown', {'error': 'admin_internal_outcome_unknown', 'retry_with_new_key': False}
            with self.db() as db:
                db.execute('UPDATE jobs SET state=?,result=?,finished_at=? WHERE key=?', (state, encode(result), now(), key))
            self.audit.write('administration', state)

    async def recover(self):
        with self.db() as db:
            db.execute("UPDATE jobs SET state='unknown',result=?,finished_at=? WHERE state IN ('queued','running')",
                       (encode({'error': 'admin_interrupted', 'retry_with_new_key': False}), now()))

    async def close(self):
        for task in tuple(self.tasks):
            task.cancel()
        await asyncio.gather(*tuple(self.tasks), return_exceptions=True)
        await self.sup.close()

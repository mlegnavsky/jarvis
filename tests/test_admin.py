import asyncio
from pathlib import Path
import tempfile
import unittest
from app.ha import UpstreamError
from app.policy import APIError
from app.audit import Audit
from app.config_files import ConfigFiles


class AdminSupervisor:
    def __init__(self):
        self.effects = []
        self.backup_fails = False
        self.options_valid = True
        self.installed = {'core_editor': {'slug': 'core_editor', 'version': '1.0', 'version_latest': '1.2',
                         'state': 'stopped', 'options': {'password': 'private-value', 'mode': 'old'}}}
    async def request(self, method, path, body=None):
        if method == 'POST':
            self.effects.append((path, body))
        if path == '/addons/self/info':
            return {'slug': 'abc_jarvis'}
        if path == '/addons':
            return {'addons': list(self.installed.values())}
        if path == '/info':
            return {'version': 'test', 'healthy': True}
        if path == '/core/info':
            return {'version': '2026.6.4', 'state': 'started'}
        if path == '/backups/new/partial':
            if self.backup_fails:
                raise UpstreamError('backup_failed')
            return {'slug': 'testbackup'}
        if path.startswith('/store/addons/'):
            if path.endswith('/install'):
                self.installed['core_new'] = {'slug': 'core_new', 'version': '1.2', 'state': 'stopped', 'options': {}}
                return {}
            if path.endswith('/update'):
                self.installed['core_editor']['version'] = '1.2'
                return {}
            return {'slug': path.rsplit('/', 1)[1], 'version': None, 'version_latest': '1.2'}
        if path == '/store/repositories':
            if method == 'POST':
                self.repository = body['repository']
            return [{'slug': 'test', 'source': getattr(self, 'repository', 'https://github.com/a/b')}]
        if path.startswith('/addons/core_editor/'):
            verb = path.rsplit('/', 1)[1]
            if verb == 'info':
                return {**self.installed['core_editor'], 'options': dict(self.installed['core_editor']['options'])}
            if verb == 'uninstall':
                del self.installed['core_editor']
                return {}
            if verb == 'options':
                self.installed['core_editor']['options'] = body['options']
                return {}
            if verb == 'validate':
                if 'options' in body:
                    return {'valid': False}
                return {'valid': self.options_valid}
            if verb in ('start', 'stop', 'restart'):
                self.installed['core_editor']['state'] = 'stopped' if verb == 'stop' else 'started'
                return {}
        if path == '/addons/core_new/info':
            return self.installed['core_new']
        raise UpstreamError('unsupported_test_path')
    async def close(self):
        pass


class AdminTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        from app.admin import Admin
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.ha_root = self.root/'ha'
        self.ha_root.mkdir()
        self.sup = AdminSupervisor()
        self.options = {'maintenance_enabled': True, 'writes_enabled': True}
        self.worker = Admin(self.sup, self.options, self.root, Audit(self.root), ConfigFiles(self.ha_root))

    async def asyncTearDown(self):
        await self.worker.close()

    async def complete(self, operation, args, key):
        job = await self.worker.start(operation, args, key)
        await asyncio.gather(*tuple(self.worker.tasks))
        return self.worker.job(job['id'])

    async def test_install_backup_and_verified_version_with_no_replay(self):
        result = await self.complete('addon_install', {'slug': 'core_new', 'expected_version': '1.2'}, 'install')
        self.assertEqual(result['state'], 'verified', result)
        self.assertEqual(result['backup_slug'], 'testbackup')
        self.assertEqual(self.sup.effects[0][0], '/backups/new/partial')
        self.assertEqual(self.sup.effects[1][0], '/store/addons/core_new/install')
        self.assertEqual(await self.worker.start('addon_install', {'slug': 'core_new', 'expected_version': '1.2'}, 'install'), result)
        self.assertEqual(len(self.sup.effects), 2)
        with self.assertRaises(APIError):
            await self.worker.start('addon_install', {'slug': 'core_new', 'expected_version': 'different'}, 'install')

    async def test_device_metadata_revision_and_verified_readback_without_replay(self):
        device = {'id': 'dev1', 'area_id': 'hall', 'name_by_user': None}
        async def registry(kind):
            return [dict(device)] if kind == 'device' else ([{'area_id': 'living'}] if kind == 'area' else [])
        self.sup.registry = registry
        class WS:
            async def send_json(ws, value):
                self.sup.effects.append(('device_update', value))
                device.update({k: value[k] for k in ('area_id', 'name_by_user')})
            async def receive_json(ws):
                return {'id': 1, 'success': True, 'result': dict(device)}
            async def close(ws):
                pass
        async def websocket():
            return WS()
        self.sup._websocket = websocket
        self.sup.timeout = 1
        before = await self.worker.read('device', 'dev1')
        args = {'device_id': 'dev1', 'area_id': 'living', 'name_by_user': 'Voice Living', 'expected_revision': before['revision']}
        result = await self.complete('device_metadata', args, 'move-device')
        self.assertEqual(result['state'], 'verified', result)
        self.assertEqual(device['area_id'], 'living')
        self.assertEqual(device['name_by_user'], 'Voice Living')
        await self.worker.start('device_metadata', args, 'move-device')
        self.assertEqual(len(self.sup.effects), 1)
        stale = await self.complete('device_metadata', args, 'stale-move')
        self.assertEqual(stale['state'], 'failed')
        self.assertEqual(len(self.sup.effects), 1)

    async def test_automation_reload_requires_current_file_revision(self):
        async def request(method, path, body=None):
            self.sup.effects.append(path)
            self.assertEqual(path, '/core/api/services/automation/reload')
            return []
        self.sup.request = request
        self.worker.files.write('automations.yaml', '[]', 'missing')
        current = self.worker.files.read('automations.yaml')
        failed = await self.complete('automations_reload', {'expected_revision': '0'*64}, 'stale-reload')
        self.assertEqual(failed['state'], 'failed')
        self.assertEqual(self.sup.effects, [])
        result = await self.complete('automations_reload', {'expected_revision': current['revision']}, 'reload')
        self.assertEqual(result['state'], 'verified')
        self.assertEqual(len(self.sup.effects), 1)

    async def test_backup_failure_and_protected_target_prevent_side_effect(self):
        self.sup.backup_fails = True
        result = await self.complete('addon_update', {'slug': 'core_editor', 'expected_version': '1.2'}, 'fail')
        self.assertNotEqual(result['state'], 'verified')
        self.assertFalse(any(p.endswith('/update') for p, _ in self.sup.effects))
        result = await self.complete('addon_stop', {'slug': 'abc_jarvis', 'expected_version': '3.1.1'}, 'self')
        self.assertEqual(result['state'], 'failed')
        self.assertFalse(any(p.endswith('/stop') for p, _ in self.sup.effects))

    async def test_options_revision_and_redacted_readback(self):
        info = await self.worker.read('addon', 'core_editor')
        self.assertNotIn('private-value', str(info))
        result = await self.complete('addon_options', {'slug': 'core_editor', 'expected_revision': info['options_revision'],
                                    'changes': {'mode': 'new'}}, 'options')
        self.assertEqual(result['state'], 'verified', result)
        self.assertEqual(self.sup.installed['core_editor']['options']['password'], 'private-value')
        self.assertNotIn('private-value', str(result))
        stale = await self.complete('addon_options', {'slug': 'core_editor', 'expected_revision': info['options_revision'],
                                   'changes': {'mode': 'wrong'}}, 'stale')
        self.assertEqual(stale['state'], 'failed')

    async def test_file_write_edit_restore_delete_with_durable_before_image(self):
        args = {'path': 'jarvis_workspace/probe.yaml', 'content': 'probe: 1\n', 'expected_revision': 'missing'}
        saved = await self.complete('file_write', args, 'file-save')
        self.assertEqual(saved['state'], 'verified', saved)
        revision = saved['result']['revision']
        edited = await self.complete('file_write', {**args, 'content': 'probe: 2\n', 'expected_revision': revision}, 'file-edit')
        restored = await self.complete('file_restore', {'backup_id': 'file-edit', 'expected_revision': edited['result']['revision']}, 'file-restore')
        self.assertEqual(restored['state'], 'verified', restored)
        self.assertEqual(self.worker.files.read(args['path'])['content'], 'probe: 1\n')
        deleted = await self.complete('file_delete', {'path': args['path'], 'expected_revision': revision}, 'file-delete')
        self.assertEqual(deleted['state'], 'verified', deleted)
        self.assertEqual(self.worker.files.read(args['path'])['revision'], 'missing')

    async def test_permissions_invalid_operations_and_restart_unknown(self):
        self.options['maintenance_enabled'] = False
        with self.assertRaises(APIError):
            await self.worker.start('addon_start', {'slug': 'core_editor', 'expected_version': '1.0'}, 'denied')
        self.options['maintenance_enabled'] = True
        for operation, args in [('shell', {}), ([], {}), ('addon_stop', {'slug': '../x', 'expected_version': '1'}),
                                ('core_restart', {'url': 'https://evil.test'})]:
            with self.assertRaises(APIError):
                await self.worker.start(operation, args, 'bad')
        with self.worker.db() as db:
            db.execute("INSERT INTO jobs (key,fingerprint,operation,arguments,state,result,backup_slug,before_data) VALUES ('interrupted','fingerprint','core_restart','{}','running',NULL,NULL,NULL)")
        await self.worker.recover()
        self.assertEqual(self.worker.job('interrupted')['state'], 'unknown')
        self.assertEqual(self.sup.effects, [])

    async def test_invalid_options_validation_never_writes(self):
        self.sup.options_valid = False
        info = await self.worker.read('addon', 'core_editor')
        result = await self.complete('addon_options', {'slug': 'core_editor', 'expected_revision': info['options_revision'],
                                    'changes': {'mode': 'invalid'}}, 'invalid-options')
        self.assertEqual(result['state'], 'failed')
        self.assertEqual(result['result']['error'], 'addon_options_invalid')
        self.assertFalse(any(p.endswith('/options') or p == '/backups/new/partial' for p, _ in self.sup.effects))

    async def test_uninstall_backup_and_installed_readback(self):
        result = await self.complete('addon_uninstall', {'slug': 'core_editor', 'expected_version': '1.0'}, 'uninstall')
        self.assertEqual(result['state'], 'verified', result)
        self.assertEqual(self.sup.effects[0][0], '/backups/new/partial')
        self.assertEqual(self.sup.effects[0][1]['addons'], ['core_editor'])
        self.assertEqual(result['backup_slug'], 'testbackup')
        self.assertIsNotNone(result['created_at'])
        self.assertIsNotNone(result['finished_at'])
        self.assertEqual(result['request_id'], 'uninstall')
        self.assertNotIn('private-value', str(result))

    async def test_uninstall_protects_updater_and_connectivity(self):
        for target in ('self', 'abc_jarvis', 'abc_jarvis_updater', 'abc_cloudflared', 'abc_wireguard'):
            result = await self.complete('addon_uninstall', {'slug': target, 'expected_version': '1.0'}, target)
            self.assertEqual(result['state'], 'failed', result)
        self.assertEqual(self.sup.effects, [])

    async def test_repository_add_url_validation_and_readback(self):
        for url in ('http://github.com/a/b', 'https://github.com/a/b?token=secret', 'https://user:pass@github.com/a/b',
                    'https://evil.test/a/b', 'https://github.com/a/b/../../x', 'https://github.com/a/b#main'):
            with self.assertRaises(APIError):
                await self.worker.start('repository_add', {'repository_url': url}, 'invalid-repo')
        result = await self.complete('repository_add', {'repository_url': 'https://github.com/a/b'}, 'repo')
        self.assertEqual(result['state'], 'verified', result)
        self.assertEqual((await self.worker.read('repositories'))['total'], 1)

    async def test_options_restore_private_before_image(self):
        info = await self.worker.read('addon', 'core_editor')
        changed = await self.complete('addon_options', {'slug': 'core_editor', 'expected_revision': info['options_revision'],
                                       'changes': {'mode': 'new'}}, 'change')
        restored = await self.complete('addon_options_restore', {'slug': 'core_editor', 'backup_id': 'change',
                                      'expected_revision': changed['result']['options_revision']}, 'restore')
        self.assertEqual(restored['state'], 'verified', restored)
        self.assertEqual(self.sup.installed['core_editor']['options']['mode'], 'old')
        self.assertEqual(self.sup.installed['core_editor']['options']['password'], 'private-value')
        self.assertNotIn('private-value', str(restored))

    async def test_schema_migration_preserves_existing_history(self):
        import sqlite3
        from app.admin import Admin
        other = self.root/'old'
        other.mkdir()
        db = sqlite3.connect(other/'admin.sqlite')
        db.execute('CREATE TABLE jobs (key TEXT PRIMARY KEY,fingerprint TEXT,operation TEXT,arguments TEXT,state TEXT,result TEXT,backup_slug TEXT,before_data TEXT)')
        db.execute("INSERT INTO jobs VALUES ('old','fp','core_restart','{}','unknown',NULL,NULL,NULL)")
        db.commit()
        db.close()
        worker = Admin(self.sup, self.options, other, Audit(other), self.worker.files)
        self.assertEqual(worker.job('old')['state'], 'unknown')
        self.assertIsNone(worker.job('old')['created_at'])
        await worker.close()

    async def test_uninstall_missing_readback_is_unverified(self):
        original = self.sup.request
        async def request(method, path, body=None):
            if path == '/addons' and 'core_editor' not in self.sup.installed:
                return {}
            return await original(method, path, body)
        self.sup.request = request
        result = await self.complete('addon_uninstall', {'slug': 'core_editor', 'expected_version': '1.0'}, 'missing-readback')
        self.assertEqual(result['state'], 'unverified', result)

    async def test_uninstall_backup_failure_never_uninstalls(self):
        self.sup.backup_fails = True
        result = await self.complete('addon_uninstall', {'slug': 'core_editor', 'expected_version': '1.0'}, 'backup-fail')
        self.assertEqual(result['state'], 'unknown')
        self.assertFalse(any(p.endswith('/uninstall') for p, _ in self.sup.effects))

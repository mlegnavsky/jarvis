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
            return {'slug': path.rsplit('/', 1)[1], 'version': '1.2'}
        if path.startswith('/addons/core_editor/'):
            verb = path.rsplit('/', 1)[1]
            if verb == 'info':
                return {**self.installed['core_editor'], 'options': dict(self.installed['core_editor']['options'])}
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
            db.execute("INSERT INTO jobs VALUES ('interrupted','fingerprint','core_restart','{}','running',NULL,NULL,NULL)")
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

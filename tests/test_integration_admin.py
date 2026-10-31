import tempfile
import unittest
from pathlib import Path
from app.admin import Admin
from app.audit import Audit
from app.policy import APIError


class IntegrationAdminTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.calls = []
        owner = self
        class Sup:
            timeout = 1
            async def close(s):
                pass
            async def _websocket(s):
                class WS:
                    async def send_json(ws, value):
                        ws.value = value
                    async def receive_json(ws):
                        v = ws.value
                        if v['type'] == 'config_entries/get':
                            data = [{'entry_id': 'entry1', 'domain': 'test', 'title': 'Test', 'state': 'loaded', 'supports_options': True, 'data': {'password': 'secret'}}]
                        elif v['type'] == 'config_entries/subentries/list':
                            data = [{'subentry_id': 'sub1', 'subentry_type': 'conversation', 'title': 'Agent'}]
                        else:
                            data = {'pipelines': [], 'preferred_pipeline': None}
                        return {'id': 1, 'success': True, 'result': data}
                    async def close(ws):
                        pass
                return WS()
            async def request(s, method, path, body=None):
                owner.calls.append((method, path, body))
                if path == '/host/info':
                    return {'disk_free':8.0,'disk_used':20.0,'disk_total':28.0}
                if path == '/backups/new/partial':
                    return {'slug': 'safe-backup'}
                if path.endswith('/reload'):
                    return {'require_restart': False}
                if method == 'POST' and path.endswith('/flow'):
                    return {'type': 'form', 'flow_id': 'flow1', 'step_id': 'init', 'data_schema': [{'name': 'language', 'type': 'string'}]}
                if method == 'GET':
                    return {'type': 'form', 'flow_id': 'flow1', 'step_id': 'init', 'data_schema': [{'name': 'language', 'type': 'string'}]}
                return {'type': 'create_entry', 'data': {'password': 'secret'}}
        self.worker = Admin(Sup(), {'maintenance_enabled': True, 'writes_enabled': True}, Path(self.tmp.name), Audit(Path(self.tmp.name)))
        self.addAsyncCleanup(self.worker.close)

    async def complete(self, op, args, key):
        await self.worker.start(op, args, key)
        await __import__('asyncio').gather(*tuple(self.worker.tasks))
        return self.worker.job(key)

    async def test_inventory_excludes_credentials_and_reports_options_support(self):
        value = await self.worker.read('integrations')
        self.assertEqual(value['items'][0]['entry_id'], 'entry1')
        self.assertTrue(value['items'][0]['supports_options'])
        self.assertNotIn('secret', str(value))
        self.assertIn('revision', value['items'][0])

    async def test_nested_schema_defaults_and_suggestions_are_not_exposed(self):
        from app.integration_admin import public_form
        value = public_form({'type': 'form', 'data_schema': [{'name': 'nested', 'schema': [{'name': 'arbitrary', 'default': 'secret', 'description': {'suggested_value': 'secret'}}]}]})
        self.assertNotIn('secret', str(value))

    async def test_subentry_settings_use_owned_native_subentry_route(self):
        sub = (await self.worker.read('integration_subentries', 'entry1'))['items'][0]
        opened = await self.complete('integration_subentry_options_start', {'entry_id': 'entry1', 'subentry_id': 'sub1', 'expected_revision': sub['revision']}, 'sub-open')
        self.assertEqual(opened['state'], 'verified', opened)
        self.assertTrue(any(p == '/core/api/config/config_entries/subentries/flow' for _, p, _ in self.calls))
        form = await self.worker.read('integration_options', 'flow1')
        self.assertEqual(form['step_id'], 'init')
        self.assertEqual(self.calls[-1][1], '/core/api/config/config_entries/subentries/flow/flow1')

    async def test_owned_options_form_submission_is_revision_checked_and_not_repeated(self):
        item = (await self.worker.read('integrations'))['items'][0]
        opened = await self.complete('integration_options_start', {'entry_id': 'entry1', 'expected_revision': item['revision']}, 'open')
        self.assertEqual(opened['state'], 'verified', opened)
        form = opened['result']['form']
        self.assertNotIn('secret', str(form))
        args = {'flow_id': 'flow1', 'expected_revision': form['revision'], 'user_input': {'language': 'cs'}}
        saved = await self.complete('integration_options_submit', args, 'save')
        self.assertEqual(saved['state'], 'verified', saved)
        self.assertTrue(saved['result']['configuration_saved'])
        self.assertNotIn('secret', str(saved))
        count = len(self.calls)
        await self.worker.start('integration_options_submit', args, 'save')
        self.assertEqual(len(self.calls), count)
        self.assertEqual(self.calls[0][1], '/host/info')
        self.assertEqual(self.calls[1][1], '/backups/new/partial')

    async def test_foreign_flow_and_stale_entry_are_rejected_before_mutation(self):
        with self.assertRaises(APIError):
            await self.worker.read('integration_options', 'foreign')
        result = await self.complete('integration_options_start', {'entry_id': 'entry1', 'expected_revision': '0'*64}, 'stale')
        self.assertEqual(result['state'], 'failed')
        self.assertEqual(self.calls, [])

    async def test_integration_reload_requires_matching_revision_and_loaded_readback(self):
        item = (await self.worker.read('integrations'))['items'][0]
        result = await self.complete('integration_reload', {'entry_id': 'entry1', 'expected_revision': item['revision']}, 'reload')
        self.assertEqual(result['state'], 'verified', result)

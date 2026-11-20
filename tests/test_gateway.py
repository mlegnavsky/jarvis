import asyncio
import base64
import tempfile
import unittest
from pathlib import Path
from aiohttp.test_utils import TestClient, TestServer
from jarvis_updater.gateway import Gateway
from jarvis_updater.gateway.oauth import OAuth
from jarvis_updater.gateway.policy import APIError
from jarvis_updater.updater import create_updater

OPTIONS = {'mcp_enabled': True, 'oauth_public_url': 'https://jarvis.example',
    'oauth_redirect_uris': ['https://chatgpt.com/callback'], 'oauth_client_secret': 's'*32,
    'oauth_owner_secret': 'o'*32, 'writes_enabled': True, 'maintenance_enabled': True}
TOOL = {'name': 'jarvis_action', 'inputSchema': {'type': 'object', 'properties': {
    'request_id': {'type': 'string'}, 'entity_id': {'type': 'string'}, 'service': {'type': 'string'}, 'data': {'type': 'object'}},
    'required': ['request_id', 'entity_id', 'service', 'data']}, 'securitySchemes': [{'scopes': ['jarvis:control']}]}

class Supervisor:
    def __init__(self): self.calls = []
    async def request(self, method, path, body=None):
        self.calls.append((method, path, body))
        if path == '/addons/self/info': return {'slug': 'abc_jarvis_updater', 'network': {'8100/tcp': None}}
        if path.endswith('/info'): return {'state': 'started', 'options': OPTIONS, 'network': {'8099/tcp': 8099}}
        return {}

class Worker:
    def __init__(self): self.sup = Supervisor()
    async def target(self): return 'abc_jarvis'

class GatewayTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name)
        self.worker = Worker()
        self.options = {'updates_enabled': True, 'api_token': 'a'*32, 'jarvis_api_token': 'b'*32}
        async def backend(method, path, body):
            if path.endswith('catalog'): return {'tools': [TOOL]}
            raise APIError(503, 'backend_unavailable')
        self.gateway = Gateway(self.worker, self.options, self.path, backend)
        await self.gateway.prepare()
    async def asyncTearDown(self):
        await self.gateway.close()
        self.temp.cleanup()

    async def test_oauth_snapshot_preserves_access_and_refresh(self):
        original = self.gateway.oauth
        with original.db() as db: tokens = original.issue(db, ['jarvis:read'])
        self.gateway.state.update(phase='active')
        self.gateway.save()
        restored = Gateway(self.worker, self.options, self.path)
        self.assertEqual(restored.oauth.verify('Bearer '+tokens['access_token'])['scopes'], ['jarvis:read'])
        app = create_updater(self.worker, self.options, restored)
        async with TestClient(TestServer(app)) as client:
            response = await client.post('/oauth/token', data={'grant_type': 'refresh_token',
                'refresh_token': tokens['refresh_token'], 'client_id': 'jarvis-chatgpt', 'client_secret': 's'*32})
            self.assertEqual(response.status, 200)
            self.assertIn('access_token', await response.json())

    async def test_backend_down_reports_rescue_without_old_home_state(self):
        value = await self.gateway.invoke('jarvis_inventory', {}, ['jarvis:read'])
        self.assertTrue(value['isError'])
        self.assertTrue(value['structuredContent']['recovery_available'])
        self.assertNotIn('items', value['structuredContent'])
        status = await self.gateway.invoke('jarvis_status', {}, ['jarvis:read'])
        self.assertFalse(status['structuredContent']['backend_connected'])

    async def test_rescue_operation_is_durable_and_not_replayed(self):
        args = {'action': 'restart', 'request_id': 'same'}
        first = await self.gateway.rescue(args)
        await asyncio.gather(*list(self.gateway.tasks))
        second = await self.gateway.rescue(args)
        self.assertEqual(first['id'], second['id'])
        calls = [c for c in self.worker.sup.calls if c[1].endswith('/restart')]
        self.assertEqual(len(calls), 1)
        with self.assertRaises(APIError):
            await self.gateway.rescue({'action': 'outage_test', 'request_id': 'same'})

    async def test_outage_obligation_survives_restart(self):
        self.gateway.state['operations']['outage'] = {'id': 'outage', 'state': 'restart_required', 'target': 'abc_jarvis', 'arguments': {'action': 'outage_test'}}
        self.gateway.save()
        recovered = Gateway(self.worker, self.options, self.path)
        await recovered.recover()
        await asyncio.gather(*list(recovered.tasks))
        self.assertEqual(recovered.state['operations']['outage']['state'], 'verified')
        self.assertTrue(any(c[1].endswith('/start') for c in self.worker.sup.calls))

    async def test_rescue_requires_both_scopes(self):
        self.gateway.state['phase'] = 'active'
        with self.gateway.oauth.db() as db: tokens = self.gateway.oauth.issue(db, ['jarvis:control'])
        app = create_updater(self.worker, self.options, self.gateway)
        async with TestClient(TestServer(app)) as client:
            response = await client.post('/mcp', headers={'Authorization': 'Bearer '+tokens['access_token'], 'Accept': 'application/json, text/event-stream'},
                json={'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call', 'params': {'name': 'jarvis_action', 'arguments': {
                    'request_id': 'x', 'entity_id': 'jarvis.system', 'service': 'jarvis.rescue', 'data': {'action': 'restart'}}}})
            value = await response.json()
            self.assertEqual(value['result']['structuredContent']['error'], 'insufficient_scope')
        self.assertFalse(any(c[1].endswith('/restart') for c in self.worker.sup.calls))

    async def test_rollback_releases_gateway_before_sibling_rebind(self):
        await self.gateway.rollback('test')
        self.assertEqual(self.gateway.state['phase'], 'rollback_release')
        self.assertFalse(any(c[1] == '/addons/abc_jarvis/restart' for c in self.worker.sup.calls))
        await self.gateway.recover()
        await asyncio.gather(*list(self.gateway.tasks))
        self.assertTrue(any(c[1] == '/addons/abc_jarvis/restart' for c in self.worker.sup.calls))

    async def test_handover_import_and_boot_gated_commit(self):
        with self.gateway.oauth.db() as db:
            tokens = self.gateway.oauth.issue(db, ['jarvis:read'])
        raw = (self.path / 'oauth.sqlite').read_bytes()
        calls = []
        async def backend(method, path, body):
            calls.append(path)
            if path.endswith('bootstrap'): return {'oauth_database': base64.b64encode(raw).decode()}
            if path.endswith('watchdog'): return {'armed': True}
            if path.endswith('catalog'): return {'tools': [TOOL]}
            return {'committed': True}
        self.gateway.backend_override = backend
        self.gateway.routes_ready = True
        await self.gateway.activate('migration')
        # Wait only the handover, not its subsequently launched deadline watcher.
        await asyncio.gather(*list(self.gateway.tasks))
        self.assertEqual(self.gateway.state['phase'], 'awaiting_external')
        self.assertIn('/v1/gateway/watchdog', calls)
        app = create_updater(self.worker, self.options, self.gateway)
        async with TestClient(TestServer(app)) as client:
            response = await client.post('/oauth/token', data={})
            self.assertEqual(response.status, 401)
            response = await client.post('/mcp', headers={'Authorization': 'Bearer '+tokens['access_token'], 'Accept': 'application/json, text/event-stream'},
                json={'jsonrpc': '2.0', 'id': 1, 'method': 'ping'})
            self.assertEqual(response.status, 503)
        self.assertNotIn('/v1/gateway/commit', calls)
        restarted = Gateway(self.worker, self.options, self.path, backend)
        original_request = self.worker.sup.request
        async def mapped(method, path, body=None):
            value = await original_request(method, path, body)
            if path == '/addons/self/info': value['network'] = {'8100/tcp': 8099}
            return value
        self.worker.sup.request = mapped
        app = create_updater(self.worker, self.options, restarted)
        async with TestClient(TestServer(app)) as client:
            response = await client.post('/mcp', headers={'Authorization': 'Bearer '+tokens['access_token'], 'Accept': 'application/json, text/event-stream'},
                json={'jsonrpc': '2.0', 'id': 1, 'method': 'ping'})
            self.assertEqual(response.status, 200)
        self.assertIn('/v1/gateway/commit', calls)
        self.assertEqual(restarted.state['phase'], 'active')

    async def test_first_refresh_commits_before_rotation(self):
        with self.gateway.oauth.db() as db:
            tokens = self.gateway.oauth.issue(db, ['jarvis:read'])
        self.gateway.state.update(phase='awaiting_external', activation_boot_id='old-boot')
        self.gateway.save()
        events = []
        async def backend(method, path, body):
            if path.endswith('/commit'):
                # Refresh token has not rotated before main authority commits.
                with self.gateway.oauth.db() as db:
                    self.assertFalse(self.gateway.oauth.load(db, 'refresh', tokens['refresh_token']).get('used'))
                events.append('committed')
            return {}
        self.gateway.backend_override = backend
        original = self.worker.sup.request
        async def mapped(method, path, body=None):
            value = await original(method, path, body)
            if path == '/addons/self/info': value['network'] = {'8100/tcp': 8099}
            return value
        self.worker.sup.request = mapped
        app = create_updater(self.worker, self.options, self.gateway)
        async with TestClient(TestServer(app)) as client:
            response = await client.post('/oauth/token', data={'grant_type': 'refresh_token',
                'refresh_token': tokens['refresh_token'], 'client_id': 'jarvis-chatgpt', 'client_secret': 's'*32})
            self.assertEqual(response.status, 200)
            fresh = await response.json()
            self.assertIn('access_token', fresh)
        self.assertEqual(events, ['committed'])
        self.assertEqual(self.gateway.state['phase'], 'active')

    async def test_commit_and_rollback_are_serialized(self):
        self.gateway.state.update(phase='awaiting_external', activation_boot_id='old')
        entered, release = asyncio.Event(), asyncio.Event()
        original = self.worker.sup.request
        async def request(method, path, body=None):
            value = await original(method, path, body)
            if path == '/addons/self/info':
                entered.set()
                await release.wait()
                value['network'] = {'8100/tcp': 8099}
            return value
        async def backend(method, path, body): return {}
        self.worker.sup.request = request
        self.gateway.backend_override = backend
        committing = asyncio.create_task(self.gateway.commit())
        await entered.wait()
        rolling = asyncio.create_task(self.gateway.rollback('deadline'))
        release.set()
        await asyncio.gather(committing, rolling)
        self.assertEqual(self.gateway.state['phase'], 'active')
        self.assertFalse(any(c[1].endswith('/options') for c in self.worker.sup.calls))

    async def test_large_admin_write_is_proxied(self):
        tool = {'name': 'jarvis_admin_change', 'inputSchema': {'properties': {'operation': {'type': 'string'},
            'arguments': {'type': 'object'}, 'request_id': {'type': 'string'}}, 'required': ['operation', 'arguments', 'request_id']},
            'securitySchemes': [{'scopes': ['jarvis:maintain']}]}
        self.gateway.catalog = [tool]
        self.gateway.state['phase'] = 'active'
        received = []
        async def backend(method, path, body):
            received.append(body)
            return {'content': [], 'structuredContent': {'state': 'queued'}, 'isError': False}
        self.gateway.backend_override = backend
        with self.gateway.oauth.db() as db: tokens = self.gateway.oauth.issue(db, ['jarvis:maintain'])
        app = create_updater(self.worker, self.options, self.gateway)
        async with TestClient(TestServer(app)) as client:
            response = await client.post('/mcp', headers={'Authorization': 'Bearer '+tokens['access_token'], 'Accept': 'application/json, text/event-stream'},
                json={'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call', 'params': {'name': 'jarvis_admin_change', 'arguments': {
                    'operation': 'file_write', 'request_id': 'large', 'arguments': {'content': 'x'*20000}}}})
            self.assertEqual(response.status, 200)
        self.assertEqual(len(received[0]['arguments']['arguments']['content']), 20000)

    async def test_semantic_backend_rejection_is_not_an_outage(self):
        async def backend(method, path, body): raise APIError(403, 'writes_disabled')
        self.gateway.backend_override = backend
        value = await self.gateway.invoke('jarvis_action', {'service': 'light.turn_on'}, ['jarvis:control'])
        self.assertEqual(value['structuredContent'], {'error': 'writes_disabled', 'backend_connected': True})

    async def test_failed_restore_repairs_topology_and_credentials_without_replay(self):
        self.gateway.state['phase'] = 'active'
        original = self.worker.sup.request
        async def request(method, path, body=None):
            if '/restore/partial' in path:
                self.worker.sup.calls.append((method, path, body))
                raise APIError(502, 'restore_start_failed')
            value = await original(method, path, body)
            if path == '/addons/abc_jarvis/info': value['options'] = {**OPTIONS, 'api_token': 'restored'*8}
            return value
        self.worker.sup.request = request
        operation = {'id': 'restore', 'target': 'abc_jarvis', 'state': 'running', 'arguments': {'action': 'restore', 'backup_slug': 'old'}}
        self.gateway.state['operations']['restore'] = operation
        await self.gateway.run_rescue(operation)
        self.assertTrue(any(c[1] == '/addons/abc_jarvis/options' and c[2]['network']['8099/tcp'] is None for c in self.worker.sup.calls))
        self.assertTrue(any(c[1] == '/addons/abc_jarvis/start' for c in self.worker.sup.calls))
        self.assertEqual(self.options['jarvis_api_token'], 'restored'*8)
        self.assertEqual(self.gateway.state['phase'], 'active')
        self.assertEqual(len([c for c in self.worker.sup.calls if '/restore/partial' in c[1]]), 1)
        self.assertTrue((self.path/'backend-credential.json').exists())

    async def test_public_disable_preserves_authenticated_rescue(self):
        self.gateway.state['phase'] = 'active'
        self.options['gateway_enabled'] = False
        app = create_updater(self.worker, self.options, self.gateway)
        async with TestClient(TestServer(app)) as client:
            for path in ('/mcp', '/oauth/authorize', '/.well-known/oauth-authorization-server'):
                response = await client.get(path)
                self.assertEqual(response.status, 503)
                self.assertEqual((await response.json())['error'], 'gateway_disabled')
            response = await client.post('/v1/rescue', headers={'Authorization': 'Bearer '+'a'*32}, json={'action': 'status'})
            self.assertEqual(response.status, 202)

    async def test_revoke_generation_preserves_zero_and_invalidates_existing_grants(self):
        with self.gateway.oauth.db() as db:
            old = self.gateway.oauth.issue(db, ['jarvis:read'])
        self.gateway.state['phase'] = 'active'
        self.gateway.save()
        zero = Gateway(self.worker, {**self.options, 'revoke_generation': 0}, self.path)
        self.assertEqual(zero.oauth.verify('Bearer '+old['access_token'])['scopes'], ['jarvis:read'])
        revoked = Gateway(self.worker, {**self.options, 'revoke_generation': 1}, self.path)
        with self.assertRaises(APIError):
            revoked.oauth.verify('Bearer '+old['access_token'])
        with revoked.oauth.db() as db:
            with self.assertRaises(APIError):
                revoked.oauth.load(db, 'refresh', old['refresh_token'])
            fresh = revoked.oauth.issue(db, ['jarvis:read'])
        again = Gateway(self.worker, {**self.options, 'revoke_generation': 1}, self.path)
        self.assertEqual(again.oauth.verify('Bearer '+fresh['access_token'])['scopes'], ['jarvis:read'])
        lowered = Gateway(self.worker, {**self.options, 'revoke_generation': 0}, self.path)
        with self.assertRaises(APIError):
            lowered.oauth.verify('Bearer '+old['access_token'])
        self.assertEqual(lowered.oauth.verify('Bearer '+fresh['access_token'])['scopes'], ['jarvis:read'])

    async def test_restart_polls_readiness_without_repeating_write(self):
        attempts = []
        async def backend(method, path, body):
            attempts.append(path)
            if len(attempts) < 3:
                raise APIError(503, 'backend_unavailable')
            return {'tools': []}
        self.gateway.backend_override = backend
        operation = {'id': 'restart', 'state': 'running', 'target': 'abc_jarvis', 'arguments': {'action': 'restart'}}
        await self.gateway.run_rescue(operation)
        self.assertEqual(operation['state'], 'verified')
        self.assertEqual(len(attempts), 3)
        self.assertEqual(len([c for c in self.worker.sup.calls if c[1].endswith('/restart')]), 1)

    async def test_unconfirmed_restore_repair_never_claims_restore_verified(self):
        self.gateway.state['phase'] = 'active'
        original = self.worker.sup.request
        async def request(method, path, body=None):
            value = await original(method, path, body)
            if path == '/addons/abc_jarvis/info': value['options'] = {**OPTIONS, 'api_token': 'restored'*8}
            return value
        self.worker.sup.request = request
        operation = {'id': 'restore', 'state': 'unknown', 'target': 'abc_jarvis',
            'repair_required': True, 'restore_confirmed': False, 'arguments': {'action': 'restore', 'backup_slug': 'old'}}
        await self.gateway.repair_restored(operation)
        self.assertEqual(operation['state'], 'unverified')
        self.assertFalse(operation['repair_required'])
        self.assertEqual(operation['error'], 'restore_outcome_unknown_backend_repaired')
        self.assertFalse(any('/restore/partial' in c[1] for c in self.worker.sup.calls))

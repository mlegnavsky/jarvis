import base64
from pathlib import Path
import sqlite3
import tempfile
import unittest
from aiohttp.test_utils import TestClient, TestServer
from app.ha import HAClient
from app.server import create_app
from app.oauth import OAuth
from tests.ha_fixture import HomeFixture
from tests import test_oauth as fixture
from app.gateway_backend import MigrationWatchdog, persist
from app.audit import Audit
from app.policy import APIError


class BackendGatewayTests(unittest.IsolatedAsyncioTestCase):
    params = fixture.OAuthTests.params
    authorize = fixture.OAuthTests.authorize
    exchange = fixture.OAuthTests.exchange

    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.directory = Path(self.tmp.name)
        self.home = HomeFixture()
        self.ha = HAClient('supervisor-test', await self.home.start())
        self.options = {**fixture.OPTIONS, 'api_token': 'a'*40, 'maintenance_enabled': True,
                        'writes_enabled': True, 'allowed_entities': ['light.test'], 'allowed_services': ['light.turn_on']}
        self.app = create_app(self.ha, self.options, self.directory, watch=False)
        self.http = TestClient(TestServer(self.app))
        await self.http.start_server()

    async def asyncTearDown(self):
        await self.http.close()
        await self.ha.close()
        await self.home.close()
        self.tmp.cleanup()

    def auth(self):
        return {'Authorization': 'Bearer '+self.options['api_token']}

    async def test_internal_invocation_validates_scope_schema_and_auth(self):
        args = {'name': 'jarvis_action', 'arguments': {'entity_id': 'light.test', 'service': 'light.turn_on',
                'data': {}, 'request_id': 'gateway-light'}, 'scopes': ['jarvis:read']}
        self.assertEqual((await self.http.post('/v1/gateway/invoke', json=args)).status, 401)
        self.assertEqual((await self.http.post('/v1/gateway/invoke', json=args, headers=self.auth())).status, 403)
        self.assertEqual(self.home.effects, [])
        args['scopes'].append('jarvis:control')
        response = await self.http.post('/v1/gateway/invoke', json=args, headers=self.auth())
        self.assertEqual(response.status, 200, await response.text())
        self.assertTrue((await response.json())['structuredContent']['target_state_verified'])
        args['arguments']['url'] = 'https://evil.test'
        self.assertEqual((await self.http.post('/v1/gateway/invoke', json=args, headers=self.auth())).status, 400)
        self.assertEqual(len(self.home.effects), 1)

    async def test_snapshot_preserves_grant_pauses_mutations_and_commit_is_irreversible(self):
        tokens = await (await self.exchange(await self.authorize())).json()
        response = await self.http.post('/v1/gateway/bootstrap', json={}, headers=self.auth())
        self.assertEqual(response.status, 200, await response.text())
        raw = base64.b64decode((await response.json())['oauth_database'])
        copied = self.directory/'copy'
        copied.mkdir()
        (copied/'oauth.sqlite').write_bytes(raw)
        clone = OAuth(dict(self.options), copied)
        self.assertTrue(clone.verify('Bearer '+tokens['access_token'], 'jarvis:read'))
        response = await self.http.post('/oauth/token', data={'grant_type': 'refresh_token',
            'refresh_token': tokens['refresh_token'], 'client_id': 'jarvis-chatgpt',
            'client_secret': self.options['oauth_client_secret']})
        self.assertEqual(response.status, 503)
        watchdog = await (await self.http.get('/v1/gateway/watchdog', headers=self.auth())).json()
        self.assertTrue(watchdog['armed'])
        self.assertEqual((await self.http.post('/v1/gateway/commit', json={}, headers=self.auth())).status, 200)
        self.assertEqual((await self.http.post('/v1/gateway/commit', json={}, headers=self.auth())).status, 200)
        self.assertEqual((await self.http.post('/v1/gateway/unpause', json={}, headers=self.auth())).status, 409)


class WatchdogTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.directory = Path(self.tmp.name)
        self.calls = []
        class Supervisor:
            async def request(inner, method, path, body=None):
                self.calls.append((method, path, body))
                return {}
        self.watchdog = MigrationWatchdog(Supervisor(), {}, self.directory, Audit(self.directory))
        self.saved = {'phase': 'armed', 'deadline': 0, 'main': 'test_jarvis', 'updater': 'test_jarvis_updater',
                      'main_network': {'8099/tcp': 8099}, 'updater_network': {'8100/tcp': None}}
        persist(self.watchdog.path, self.saved)
        async def unavailable(marker):
            raise UpstreamError('gateway_down')
        from app.ha import UpstreamError
        self.watchdog.updater_status = unavailable

    async def test_dead_gateway_is_unmapped_before_original_port_is_restored(self):
        await self.watchdog.tick()
        self.assertEqual(self.calls[0][1], '/addons/test_jarvis_updater/stop')
        self.assertEqual(self.calls[1][2], {'network': {'8100/tcp': None}})
        self.assertEqual(self.calls[2][2], {'network': {'8099/tcp': 8099}})
        self.assertEqual(self.calls[-1][1], '/addons/test_jarvis/restart')
        self.assertEqual(self.watchdog.marker()['phase'], 'rollback_ready')
        await self.watchdog.start()
        self.assertFalse(self.watchdog.path.exists())
        await self.watchdog.close()

    async def test_committed_authority_never_rolls_back_stale_oauth(self):
        await self.watchdog.commit()
        await self.watchdog.tick()
        self.assertEqual(self.calls, [])
        with self.assertRaises(APIError):
            await self.watchdog.unpause()

    async def test_rolling_back_resumes_even_if_gateway_is_stuck_commit_pending(self):
        persist(self.watchdog.path, {**self.saved, 'phase': 'rolling_back'})
        async def pending(marker):
            return {'phase': 'commit_pending'}
        self.watchdog.updater_status = pending
        await self.watchdog.tick()
        self.assertEqual(self.watchdog.marker()['phase'], 'rollback_ready')
        with self.assertRaises(APIError):
            await self.watchdog.commit()

    async def test_broken_updater_start_cannot_block_public_backend_recovery(self):
        from app.ha import UpstreamError
        original = self.watchdog.ha.request
        async def broken_start(method, path, body=None):
            result = await original(method, path, body)
            if path == '/addons/test_jarvis_updater/start':
                raise UpstreamError('broken_gateway_image')
            return result
        self.watchdog.ha.request = broken_start
        await self.watchdog.tick()
        self.assertEqual(self.calls[-1][1], '/addons/test_jarvis/restart')
        self.assertEqual(self.watchdog.marker()['phase'], 'rollback_ready')

    async def test_restart_obligation_retries_after_transient_rejection(self):
        from app.ha import UpstreamError
        original = self.watchdog.ha.request
        failures = [True]
        async def fail_once(method, path, body=None):
            result = await original(method, path, body)
            if path == '/addons/test_jarvis/restart' and failures:
                failures.pop()
                raise UpstreamError('restart_rejected')
            return result
        self.watchdog.ha.request = fail_once
        with self.assertRaises(UpstreamError):
            await self.watchdog.tick()
        self.assertEqual(self.watchdog.marker()['phase'], 'rollback_ready')
        await self.watchdog.tick()
        self.assertEqual(sum(path == '/addons/test_jarvis/restart' for _, path, _ in self.calls), 2)

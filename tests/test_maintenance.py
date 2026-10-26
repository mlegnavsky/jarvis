import asyncio
import tempfile
import unittest
from pathlib import Path
from aiohttp import web
from aiohttp.test_utils import TestServer, TestClient
from updater import Supervisor, Maintenance, create_updater
from updater import APIError


class SupervisorFixture:
    def __init__(self):
        self.effects = []
        self.backup_fails = False
        self.update_changes_version = True
        self.version = '0.1.0'
        self.latest = '0.2.0'
        self.slug = 'abc123_jarvis_updater'
        self.app = web.Application()
        self.app.router.add_route('*', '/{path:.*}', self.handle)
        self.server = TestServer(self.app)

    async def handle(self, request):
        if request.headers.get('Authorization') != 'Bearer sup-token':
            return web.json_response({}, status=401)
        path = request.path
        if request.method == 'POST':
            body = await request.json()
            self.effects.append((path, body))
        if path == '/addons/self/info':
            value = {'slug': self.slug}
        elif path == '/addons/abc123_jarvis/info':
            value = {'slug': 'abc123_jarvis', 'version': self.version, 'version_latest': self.latest, 'state': 'started'}
        elif path == '/backups/new/partial':
            if self.backup_fails:
                return web.json_response({'result': 'error', 'message': 'private diagnostic'})
            value = {'slug': 'backup123'}
        elif path == '/store/addons/abc123_jarvis/update':
            if self.update_changes_version:
                self.version = self.latest
            value = {}
        elif path == '/store/reload':
            value = {}
        else:
            return web.json_response({}, status=404)
        return web.json_response({'result': 'ok', 'data': value})


class MaintenanceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.fixture = SupervisorFixture()
        await self.fixture.server.start_server()
        self.sup = Supervisor('sup-token', str(self.fixture.server.make_url('')).rstrip('/'))
        self.health_ok = True
        async def health(slug, version):
            return self.health_ok and self.fixture.version == version
        self.health = health
        self.worker = Maintenance(self.sup, Path(self.tmp.name), health, attempts=2, interval=0.01)

    async def asyncTearDown(self):
        await self.worker.close()
        await self.sup.close()
        await self.fixture.server.close()
        self.tmp.cleanup()

    async def finished(self, job):
        for _ in range(100):
            state = self.worker.get_job(job['id'])
            if state['state'] in ('verified', 'failed'):
                return state
            await asyncio.sleep(0.01)
        self.fail('job did not finish')

    async def test_backup_precedes_update_and_only_jarvis_is_targeted(self):
        job = await self.worker.start({'version': '0.2.0'}, 'job-1')
        result = await self.finished(job)
        self.assertEqual(result['state'], 'verified')
        self.assertEqual(result['backup_slug'], 'backup123')
        paths = [e[0] for e in self.fixture.effects]
        self.assertLess(paths.index('/backups/new/partial'), paths.index('/store/addons/abc123_jarvis/update'))
        backup = next(body for path, body in self.fixture.effects if path == '/backups/new/partial')
        self.assertEqual(backup['addons'], ['abc123_jarvis'])
        self.assertFalse(backup['homeassistant'])

    async def test_backup_failure_blocks_update(self):
        self.fixture.backup_fails = True
        result = await self.finished(await self.worker.start({'version': '0.2.0'}, 'job-1'))
        self.assertEqual(result['state'], 'failed')
        self.assertNotIn('/store/addons/abc123_jarvis/update', [e[0] for e in self.fixture.effects])
        self.assertNotIn('private diagnostic', str(result))

    async def test_other_target_and_version_mismatch_rejected(self):
        for body in ({'version': '0.2.0', 'target': 'core'}, {'version': '999'}):
            with self.assertRaises(APIError):
                await self.worker.start(body, 'job-1')
        self.assertNotIn('/backups/new/partial', [e[0] for e in self.fixture.effects])

    async def test_mismatch_or_unhealthy_app_is_never_verified(self):
        self.fixture.update_changes_version = False
        result = await self.finished(await self.worker.start({'version': '0.2.0'}, 'job-1'))
        self.assertEqual(result['state'], 'failed')
        self.assertEqual(result['error'], 'post_update_verification_failed')

    async def test_restart_recovers_job_without_duplicate_update(self):
        job = await self.worker.start({'version': '0.2.0'}, 'job-1')
        await self.finished(job)
        await self.worker.close()
        self.worker = Maintenance(self.sup, Path(self.tmp.name), self.health, attempts=2, interval=0.01)
        await self.worker.recover()
        again = await self.worker.start({'version': '0.2.0'}, 'job-1')
        self.assertEqual(again['id'], job['id'])
        self.assertEqual([p for p, b in self.fixture.effects].count('/store/addons/abc123_jarvis/update'), 1)

    async def test_updater_slug_must_belong_to_same_repository(self):
        self.fixture.slug = 'core_other'
        with self.assertRaises(APIError):
            await self.worker.start({'version': '0.2.0'}, 'job-1')
        self.assertEqual(self.fixture.effects, [])

    async def test_updater_auth_and_permission_fail_closed(self):
        client = TestClient(TestServer(create_updater(self.worker, {'api_token': 'x'*32})))
        await client.start_server()
        try:
            response = await client.get('/v1/check')
            self.assertEqual(response.status, 401)
            response = await client.post('/v1/update', json={'version': '0.2.0'},
                headers={'Authorization': 'Bearer ' + 'x'*32, 'Idempotency-Key': 'test'})
            self.assertEqual(response.status, 403)
            self.assertEqual(self.fixture.effects, [])
        finally:
            await client.close()

    async def test_interrupted_update_is_only_verified_after_restart(self):
        identifier = 'a'*32
        self.worker.jobs[identifier] = {'id': identifier, 'key': 'old', 'version': '0.2.0',
            'target': 'abc123_jarvis', 'state': 'updating', 'backup_slug': 'backup123', 'error': None}
        self.worker.save()
        self.fixture.version = '0.2.0'
        await self.worker.close()
        self.worker = Maintenance(self.sup, Path(self.tmp.name), self.health, attempts=2, interval=0.01)
        await self.worker.recover()
        result = await self.finished({'id': identifier})
        self.assertEqual(result['state'], 'verified')
        self.assertEqual(self.fixture.effects, [])

    async def test_unhealthy_app_fails_even_when_version_matches(self):
        self.health_ok = False
        result = await self.finished(await self.worker.start({'version': '0.2.0'}, 'job-1'))
        self.assertEqual(result['state'], 'failed')

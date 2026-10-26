import tempfile
import asyncio
from app.actions import Actions
from app.audit import Audit
import unittest
from pathlib import Path
from aiohttp.test_utils import TestClient, TestServer
from tests.ha_fixture import HomeFixture
from app.ha import HAClient
from app.server import create_app

TOKEN = 'test-api-token-that-is-long-enough-123456'


class APITests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.fixture = HomeFixture()
        self.ha = HAClient('supervisor-test', await self.fixture.start())
        self.options = {'api_token': TOKEN, 'writes_enabled': True,
                        'allowed_entities': ['light.test'], 'allowed_services': ['light.turn_on']}
        await self.open_client()

    async def open_client(self):
        self.http = TestClient(TestServer(create_app(self.ha, self.options, Path(self.tmp.name), watch=False)))
        await self.http.start_server()

    async def asyncTearDown(self):
        await self.http.close()
        await self.ha.close()
        await self.fixture.close()
        self.tmp.cleanup()

    def headers(self, key='request-1'):
        return {'Authorization': 'Bearer ' + TOKEN, 'Idempotency-Key': key}

    async def action(self, payload=None, key='request-1'):
        return await self.http.post('/v1/actions', headers=self.headers(key), json=payload or {
            'entity_id': 'light.test', 'service': 'light.turn_on', 'data': {'brightness': 100}})

    async def test_inventory_requires_authentication(self):
        for headers in ({}, {'Authorization': 'Bearer wrong'}):
            response = await self.http.get('/v1/snapshot', headers=headers)
            self.assertEqual(response.status, 401)
            self.assertNotIn('light.test', await response.text())

    async def test_empty_token_fails_closed(self):
        await self.http.close()
        self.options['api_token'] = ''
        await self.open_client()
        response = await self.http.get('/v1/snapshot', headers=self.headers())
        self.assertEqual(response.status, 503)

    async def test_authenticated_snapshot_and_health(self):
        response = await self.http.get('/v1/snapshot', headers=self.headers())
        self.assertEqual(response.status, 200)
        self.assertEqual((await response.json())['states'][0]['state'], 'off')
        response = await self.http.get('/healthz')
        self.assertEqual(await response.json(), {'status': 'alive'})

    async def test_action_reads_before_and_after_and_survives_retry(self):
        response = await self.action()
        self.assertEqual(response.status, 200)
        result = await response.json()
        self.assertEqual(result['before']['state'], 'off')
        self.assertEqual(result['after']['state'], 'on')
        await self.http.close()
        await self.open_client()
        response = await self.action()
        self.assertEqual(response.status, 200)
        self.assertEqual(len(self.fixture.effects), 1)

    async def test_key_cannot_be_reused_for_different_payload(self):
        await self.action()
        response = await self.action({'entity_id': 'light.test', 'service': 'light.turn_on', 'data': {'brightness': 2}})
        self.assertEqual(response.status, 409)
        self.assertEqual(len(self.fixture.effects), 1)

    async def test_disallowed_entity_and_service_do_not_execute(self):
        for entity, service in [('light.other', 'light.turn_on'), ('light.test', 'homeassistant.restart'), ('light.test', 'switch.turn_on')]:
            response = await self.action({'entity_id': entity, 'service': service, 'data': {}}, key=(service+entity).replace('.', '_'))
            self.assertEqual(response.status, 403)
        self.assertEqual(self.fixture.effects, [])

    async def test_invalid_data_and_missing_idempotency_key(self):
        for data in ({'brightness': True}, {'brightness': 256}, {'entity_id': 'light.other'}, {'brightness': '100'}):
            response = await self.action({'entity_id': 'light.test', 'service': 'light.turn_on', 'data': data})
            self.assertEqual(response.status, 400)
        response = await self.http.post('/v1/actions', headers={'Authorization': 'Bearer '+TOKEN}, json={})
        self.assertEqual(response.status, 400)
        self.assertEqual(self.fixture.effects, [])

    async def test_writes_default_disabled(self):
        await self.http.close()
        self.options = {'api_token': TOKEN}
        await self.open_client()
        response = await self.action()
        self.assertEqual(response.status, 403)
        self.assertEqual(self.fixture.effects, [])

    async def test_upstream_unavailable_blocks_action_and_redacts_audit(self):
        self.fixture.unavailable = True
        response = await self.action()
        self.assertEqual(response.status, 502)
        self.assertEqual(self.fixture.effects, [])
        audit = (Path(self.tmp.name) / 'audit.jsonl').read_text()
        self.assertNotIn(TOKEN, audit)
        self.assertNotIn('supervisor-test', audit)
        self.assertNotIn('brightness', audit)

    async def test_malformed_json_returns_structured_error(self):
        response = await self.http.post('/v1/actions', headers=self.headers(), data='not json')
        self.assertEqual(response.status, 400)
        self.assertIn('error', await response.json())

    async def test_interrupted_action_is_not_replayed_after_restart(self):
        directory = Path(self.tmp.name)
        actions = Actions(self.ha, self.options, directory, Audit(directory))
        original = self.ha.service
        async def interrupted(*args):
            await original(*args)
            raise asyncio.CancelledError()
        self.ha.service = interrupted
        body = {'entity_id': 'light.test', 'service': 'light.turn_on', 'data': {}}
        with self.assertRaises(asyncio.CancelledError):
            await actions.execute(body, 'interrupted')
        self.ha.service = original
        await self.http.close()
        await self.open_client()
        response = await self.action(body, key='interrupted')
        self.assertEqual(response.status, 409)
        self.assertEqual((await response.json())['error'], 'action_outcome_unknown')
        self.assertEqual(len(self.fixture.effects), 1)

import tempfile
import unittest
from pathlib import Path
from aiohttp.test_utils import TestClient, TestServer
from tests.ha_fixture import HomeFixture
from tests import test_oauth as oauth_fixture
OPTIONS = oauth_fixture.OPTIONS
from app.ha import HAClient
from app.server import create_app

class MCPTests(unittest.IsolatedAsyncioTestCase):
    params = oauth_fixture.OAuthTests.params
    authorize = oauth_fixture.OAuthTests.authorize
    exchange = oauth_fixture.OAuthTests.exchange

    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.fixture = HomeFixture()
        self.ha = HAClient('supervisor-test', await self.fixture.start())
        self.options = {**OPTIONS, 'api_token': 'r'*40, 'writes_enabled': True,
            'allowed_entities': ['light.test'], 'allowed_services': ['light.turn_on']}
        self.http = TestClient(TestServer(create_app(self.ha, self.options, Path(self.tmp.name), watch=False)))
        await self.http.start_server()
        response = await self.exchange(await self.authorize())
        self.token = (await response.json())['access_token']

    async def asyncTearDown(self):
        await self.http.close()
        await self.ha.close()
        await self.fixture.close()
        self.tmp.cleanup()

    async def rpc(self, method, params=None, token=None, **headers):
        return await self.http.post('/mcp', json={'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params or {}},
            headers={'Authorization': 'Bearer '+(token or self.token), 'Accept': 'application/json, text/event-stream',
                     'MCP-Protocol-Version': '2025-11-25', **headers})

    async def control_token(self):
        return (await (await self.exchange(await self.authorize(scope='jarvis:read jarvis:control'))).json())['access_token']

    async def test_initialize_tools_and_live_paginated_inventory(self):
        response = await self.rpc('initialize', {'protocolVersion': '2025-11-25', 'capabilities': {}, 'clientInfo': {'name': 'test', 'version': '1'}})
        self.assertEqual(response.status, 200)
        self.assertEqual((await response.json())['result']['protocolVersion'], '2025-11-25')
        tools = (await (await self.rpc('tools/list')).json())['result']['tools']
        self.assertTrue(next(t for t in tools if t['name']=='jarvis_inventory')['annotations']['readOnlyHint'])
        response = await self.rpc('tools/call', {'name': 'jarvis_inventory', 'arguments': {'kind': 'states', 'limit': 1}})
        result = (await response.json())['result']['structuredContent']
        self.assertEqual(result['items'][0]['entity_id'], 'light.test')
        self.assertIsNotNone(result['captured_at'])
        self.fixture.states[0]['state'] = 'on'
        result = (await (await self.rpc('tools/call', {'name': 'jarvis_inventory', 'arguments': {}})).json())['result']['structuredContent']
        self.assertEqual(result['items'][0]['state'], 'on')

    async def test_read_scope_cannot_control_and_retry_is_durable(self):
        args = {'request_id': 'mcp-action-1', 'entity_id': 'light.test', 'service': 'light.turn_on', 'data': {}}
        response = await self.rpc('tools/call', {'name': 'jarvis_action', 'arguments': args})
        self.assertTrue((await response.json())['result']['isError'])
        self.assertEqual(self.fixture.effects, [])
        token = await self.control_token()
        for _ in range(2):
            response = await self.rpc('tools/call', {'name': 'jarvis_action', 'arguments': args}, token=token)
            self.assertTrue((await response.json())['result']['structuredContent']['accepted'])
        self.assertEqual(len(self.fixture.effects), 1)

    async def test_credentials_are_not_interchangeable_and_origin_rejected(self):
        response = await self.rpc('tools/list', token=self.options['api_token'])
        self.assertEqual(response.status, 401)
        self.assertIn('resource_metadata=', response.headers['WWW-Authenticate'])
        response = await self.http.get('/v1/snapshot', headers={'Authorization': 'Bearer '+self.token})
        self.assertEqual(response.status, 401)
        self.assertEqual((await self.rpc('tools/list', Origin='https://evil.test')).status, 403)

    async def test_protocol_and_argument_errors_never_execute(self):
        response = await self.rpc('tools/list', **{'MCP-Protocol-Version': 'future'})
        self.assertEqual(response.status, 400)
        response = await self.rpc('tools/call', {'name': 'jarvis_action', 'arguments': {'request_id': 'x', 'entity_id': 'light.test', 'service': 'light.turn_on', 'data': {}, 'url': 'evil'}}, token=await self.control_token())
        self.assertEqual((await response.json())['error']['code'], -32602)
        self.assertEqual(self.fixture.effects, [])
        for body in ([], None, {'jsonrpc': '2.0', 'method': 'tools/call'}):
            response = await self.http.post('/mcp', json=body, headers={'Authorization': 'Bearer '+self.token,
                'Accept': 'application/json, text/event-stream', 'Content-Type': 'application/json'})
            self.assertEqual(response.status, 400)

    async def test_get_is_not_an_anonymous_event_stream(self):
        self.assertEqual((await self.http.get('/mcp')).status, 401)
        response = await self.http.get('/mcp', headers={'Authorization': 'Bearer '+self.token})
        self.assertEqual(response.status, 405)

    async def test_unavailable_inventory_does_not_report_stale_success(self):
        self.fixture.unavailable = True
        result = (await (await self.rpc('tools/call', {'name': 'jarvis_inventory', 'arguments': {}})).json())['result']
        self.assertTrue(result['isError'])
        self.assertFalse(result['structuredContent']['connected'])

    async def test_disabled_connector_and_disabled_tools(self):
        await self.http.close()
        options = {**self.options, 'mcp_enabled': False}
        self.http = TestClient(TestServer(create_app(self.ha, options, Path(self.tmp.name), watch=False)))
        await self.http.start_server()
        self.assertEqual((await self.rpc('tools/list')).status, 503)
        await self.http.close()
        options.update(mcp_enabled=True, writes_enabled=False)
        self.http = TestClient(TestServer(create_app(self.ha, options, Path(self.tmp.name), watch=False)))
        await self.http.start_server()
        tools = (await (await self.rpc('tools/list')).json())['result']['tools']
        self.assertEqual({t['name'] for t in tools}, {'jarvis_status', 'jarvis_inventory'})

    async def test_notifications_and_media_type_checks(self):
        headers = {'Authorization': 'Bearer '+self.token, 'Accept': 'application/json, text/event-stream', 'MCP-Protocol-Version': '2025-11-25'}
        response = await self.http.post('/mcp', json={'jsonrpc': '2.0', 'method': 'notifications/initialized'}, headers=headers)
        self.assertEqual(response.status, 202)
        self.assertEqual(await response.read(), b'')
        self.assertEqual((await self.rpc('tools/list', Accept='application/json')).status, 406)

    async def test_voice_route_requires_maintain_scope_and_survives_legacy_action(self):
        # Catalog is configured at startup; use a second isolated application.
        from app.mcp import catalog
        definitions = catalog({**self.options, 'maintenance_enabled': True})
        definition = next(t for t in definitions if t['name'] == 'jarvis_voice')
        self.assertEqual(definition['securitySchemes'][0]['scopes'], ['jarvis:maintain'])
        response = await self.rpc('tools/call', {'name':'jarvis_action','arguments':{
            'request_id':'voice-read-denied','entity_id':'jarvis.system','service':'jarvis.voice','data':{'action':'status'}}})
        self.assertTrue((await response.json())['result']['isError'])

    async def test_official_sdk_can_initialize_list_and_call(self):
        from mcp.client import ClientSession
        from mcp.client.streamable_http import streamable_http_client
        import httpx2
        async with httpx2.AsyncClient(headers={'Authorization': 'Bearer '+self.token}, trust_env=False) as client:
            async with streamable_http_client(str(self.http.make_url('/mcp')), http_client=client) as (read, write):
                async with ClientSession(read, write, read_timeout_seconds=10) as session:
                    initialized = await session.initialize()
                    self.assertEqual(initialized.protocol_version, '2025-11-25')
                    tools = await session.list_tools()
                    self.assertIn('jarvis_inventory', [tool.name for tool in tools.tools])
                    result = await session.call_tool('jarvis_inventory', {'kind': 'states', 'limit': 1})
                    self.assertFalse(result.is_error)
                    self.assertEqual(result.structured_content['items'][0]['entity_id'], 'light.test')

    async def test_march_is_not_negotiated_or_accepted_as_supported(self):
        response = await self.rpc('initialize', {'protocolVersion': '2025-03-26', 'capabilities': {}, 'clientInfo': {'name': 'old', 'version': '1'}})
        self.assertEqual((await response.json())['result']['protocolVersion'], '2025-11-25')
        self.assertEqual((await self.rpc('tools/list', **{'MCP-Protocol-Version': '2025-03-26'})).status, 400)
        response = await self.http.post('/mcp', json={'jsonrpc': '2.0', 'id': 1, 'method': 'initialize',
            'params': {'protocolVersion': '2025-11-25'}}, headers={'Authorization': 'Bearer '+self.token,
            'Accept': 'application/json, text/event-stream'})
        self.assertEqual(response.status, 200)

    async def test_management_tools_require_maintain_and_write_gate(self):
        await self.http.close()
        self.options['maintenance_enabled'] = True
        self.http = TestClient(TestServer(create_app(self.ha, self.options, Path(self.tmp.name), watch=False)))
        await self.http.start_server()
        arguments = {'operation': 'save', 'id': 'jarvis_draft', 'expected_revision': 'missing',
                     'request_id': 'draft-1', 'config': {'alias': 'Draft', 'initial_state': False,
                                                       'triggers': [], 'actions': []}}
        call = {'name': 'jarvis_automation_change', 'arguments': arguments}
        result = (await (await self.rpc('tools/call', call)).json())['result']
        self.assertTrue(result['isError'])
        self.assertEqual(self.fixture.effects, [])
        token = (await (await self.exchange(await self.authorize(scope='jarvis:read jarvis:maintain'))).json())['access_token']
        result = (await (await self.rpc('tools/call', call, token=token)).json())['result']
        self.assertFalse(result['isError'])
        self.assertTrue(result['structuredContent']['verified'])
        self.assertFalse(self.fixture.automations['jarvis_draft']['initial_state'])
        result = (await (await self.rpc('tools/call', {'name': 'jarvis_diagnostics', 'arguments': {'check_config': True}}, token=token)).json())['result']
        self.assertEqual(result['structuredContent']['validation']['result'], 'valid')
        result = (await (await self.rpc('tools/call', {'name': 'jarvis_automation_backups', 'arguments': {}}, token=token)).json())['result']
        self.assertEqual(result['structuredContent']['items'][0]['backup_id'], 'draft-1')
        self.assertNotIn('config', result['structuredContent']['items'][0])
        invalid = {**arguments, 'operation': 'anything'}
        response = await self.rpc('tools/call', {'name': 'jarvis_automation_change', 'arguments': invalid}, token=token)
        self.assertEqual((await response.json())['error']['code'], -32602)
        self.assertEqual(len(self.fixture.effects), 1)

    async def test_existing_action_bridge_requires_both_scopes_and_preserves_id(self):
        await self.http.close()
        self.options['maintenance_enabled'] = True
        self.http = TestClient(TestServer(create_app(self.ha, self.options, Path(self.tmp.name), watch=False)))
        await self.http.start_server()
        args = {'entity_id': 'automation.jarvis_probe', 'service': 'jarvis.automation_save',
                'request_id': 'bridge-save', 'data': {'expected_revision': 'missing',
                'config': {'alias': 'Probe', 'initial_state': False, 'triggers': [], 'actions': []}}}
        for scopes in ('jarvis:read jarvis:control', 'jarvis:read jarvis:maintain'):
            token = (await (await self.exchange(await self.authorize(scope=scopes))).json())['access_token']
            result = (await (await self.rpc('tools/call', {'name': 'jarvis_action', 'arguments': args}, token=token)).json())['result']
            self.assertTrue(result['isError'])
            self.assertEqual(self.fixture.effects, [])
        token = (await (await self.exchange(await self.authorize(scope='jarvis:read jarvis:control jarvis:maintain'))).json())['access_token']
        for _ in range(2):
            result = (await (await self.rpc('tools/call', {'name': 'jarvis_action', 'arguments': args}, token=token)).json())['result']
            self.assertTrue(result['structuredContent']['verified'])
        self.assertEqual(self.fixture.effects, [('POST', 'jarvis_probe')])
        self.assertEqual(self.fixture.automations['jarvis_probe']['id'], 'jarvis_probe')
        invalid = {**args, 'entity_id': 'light.jarvis_probe', 'request_id': 'wrong-target'}
        result = (await (await self.rpc('tools/call', {'name': 'jarvis_action', 'arguments': invalid}, token=token)).json())['result']
        self.assertTrue(result['isError'])
        self.assertEqual(len(self.fixture.effects), 1)

    async def test_admin_bridge_and_tools_require_maintain_and_validate_operations(self):
        await self.http.close()
        self.options['maintenance_enabled'] = True
        self.http = TestClient(TestServer(create_app(self.ha, self.options, Path(self.tmp.name), watch=False)))
        await self.http.start_server()
        args = {'entity_id': 'jarvis.system', 'service': 'jarvis.admin', 'request_id': 'admin-read',
                'data': {'action': 'read', 'query': 'jobs'}}
        control = await self.control_token()
        result = (await (await self.rpc('tools/call', {'name': 'jarvis_action', 'arguments': args}, token=control)).json())['result']
        self.assertTrue(result['isError'])
        token = (await (await self.exchange(await self.authorize(scope='jarvis:read jarvis:control jarvis:maintain'))).json())['access_token']
        result = (await (await self.rpc('tools/call', {'name': 'jarvis_action', 'arguments': args}, token=token)).json())['result']
        self.assertFalse(result['isError'])
        self.assertEqual(result['structuredContent']['items'], [])
        response = await self.rpc('tools/call', {'name': 'jarvis_admin_change', 'arguments':
                                  {'operation': 'shell', 'arguments': {}, 'request_id': 'bad-admin'}}, token=token)
        self.assertEqual((await response.json())['error']['code'], -32602)
        self.assertEqual(self.fixture.effects, [])


class VoiceMCPTests(unittest.IsolatedAsyncioTestCase):
    params = MCPTests.params
    authorize = MCPTests.authorize
    exchange = MCPTests.exchange
    rpc = MCPTests.rpc
    asyncTearDown = MCPTests.asyncTearDown

    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.fixture = HomeFixture()
        self.fixture.states = [{'entity_id':'select.voice_end','state':'Default','attributes':{'options':['Default','Aggressive']}}]
        self.ha = HAClient('supervisor-test', await self.fixture.start())
        self.options = {**OPTIONS, 'api_token':'r'*40, 'writes_enabled':True, 'maintenance_enabled':True,
                        'allowed_entities':['select.voice_end'], 'allowed_services':['select.select_option']}
        self.http = TestClient(TestServer(create_app(self.ha,self.options,Path(self.tmp.name),watch=False)))
        await self.http.start_server()
        self.token = (await (await self.exchange(await self.authorize(scope='jarvis:read jarvis:control jarvis:maintain'))).json())['access_token']

    async def test_voice_tool_and_legacy_bridge_share_journal(self):
        data = {'action':'change','entity_id':'select.voice_end','service':'select.select_option','data':{'option':'Aggressive'}}
        r = await self.rpc('tools/call', {'name':'jarvis_voice','arguments':{'request_id':'voice-both','data':data}})
        result = (await r.json())['result']
        self.assertFalse(result['isError']);self.assertTrue(result['structuredContent']['target_state_verified'])
        r = await self.rpc('tools/call', {'name':'jarvis_action','arguments':{'request_id':'voice-both','service':'jarvis.voice','entity_id':'jarvis.system','data':data}})
        self.assertTrue((await r.json())['result']['structuredContent']['replayed'])
        self.assertEqual(len(self.fixture.effects),1)
        r = await self.rpc('tools/call', {'name':'jarvis_voice','arguments':{'request_id':'read-current','data':{'action':'status'}}})
        self.assertEqual((await r.json())['result']['structuredContent']['entities'][0]['state'],'Aggressive')

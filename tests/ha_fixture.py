import asyncio
from aiohttp import web
from aiohttp.test_utils import TestServer


class HomeFixture:
    def __init__(self):
        self.states = [{"entity_id": "light.test", "state": "off", "attributes": {"friendly_name": "Test"}}]
        self.unavailable = False
        self.unsupported = set()
        self.delay = 0
        self.effects = []
        self.light_update_delay = 0
        self.light_update_enabled = True
        self.automations = {}
        self.reject_automation = False
        self.automation_api_missing = False
        self.sockets = []
        self.app = web.Application()
        self.app.router.add_get('/core/websocket', self.websocket)
        self.app.router.add_route('*', '/{path:.*}', self.rest)
        self.server = TestServer(self.app)

    async def start(self):
        await self.server.start_server()
        return str(self.server.make_url('')).rstrip('/')

    async def close(self):
        for ws in self.sockets:
            await ws.close()
        await self.server.close()

    async def rest(self, request):
        if request.headers.get('Authorization') != 'Bearer supervisor-test':
            return web.json_response({}, status=401)
        await asyncio.sleep(self.delay)
        if self.unavailable:
            return web.json_response({}, status=503)
        path = request.path
        if path.startswith('/core/api/config/automation/config/'):
            if self.automation_api_missing:
                return web.Response(status=404)
            identifier = path.rsplit('/', 1)[1]
            if request.method == 'GET':
                return web.json_response(self.automations[identifier]) if identifier in self.automations else web.json_response({'message': 'Resource not found'}, status=404)
            if self.reject_automation:
                return web.json_response({'message': 'Message malformed'}, status=400)
            self.effects.append((request.method, identifier))
            if request.method == 'POST':
                self.automations[identifier] = {'id': identifier, **await request.json()}
            elif request.method == 'DELETE':
                self.automations.pop(identifier, None)
            return web.json_response({'result': 'ok'})
        if path == '/core/api/config/core/check_config':
            return web.json_response({'result': 'valid', 'errors': None})
        if path == '/core/api/states':
            return web.json_response(self.states)
        if path.startswith('/core/api/states/'):
            state = next((s for s in self.states if s['entity_id'] == path.rsplit('/', 1)[1]), None)
            return web.json_response(state or {}, status=200 if state else 404)
        if path == '/core/api/services':
            return web.json_response([{'domain': 'light', 'services': {'turn_on': {}, 'turn_off': {}}}])
        if path == '/core/api/config':
            return web.json_response({'version': '2026.6.4', 'time_zone': 'Europe/Prague'})
        if path.startswith('/core/api/services/'):
            body = await request.json()
            self.effects.append((path, body))
            target = next(s for s in self.states if s['entity_id'] == body['entity_id'])
            state = 'locked' if path == '/core/api/services/lock/lock' else 'off' if path.endswith('/turn_off') else 'on'
            updated = {'state': state}
            if 'brightness' in body:
                updated['state'] = 'on' if body['brightness'] else 'off'
                updated['attributes'] = {**target['attributes'], 'brightness': body['brightness']}
            if path.startswith('/core/api/services/light/') and self.light_update_delay:
                if self.light_update_enabled:
                    asyncio.get_running_loop().call_later(self.light_update_delay, target.update, updated)
            elif self.light_update_enabled or not path.startswith('/core/api/services/light/'):
                target.update(updated)
            return web.json_response(self.states)
        if path == '/info':
            return web.json_response({'result': 'ok', 'data': {'arch': 'aarch64'}})
        if path == '/addons/self/info':
            return web.json_response({'result': 'ok', 'data': {'slug': 'fixture_jarvis', 'network': {'8099/tcp': 8099}}})
        if path == '/addons/fixture_jarvis_updater/info':
            return web.json_response({'result': 'ok', 'data': {'slug': 'fixture_jarvis_updater', 'network': {'8100/tcp': None}}})
        return web.json_response({}, status=404)

    async def websocket(self, request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        self.sockets.append(ws)
        await ws.send_json({'type': 'auth_required', 'ha_version': '2026.6.4'})
        auth = await ws.receive_json()
        if auth.get('access_token') != 'supervisor-test':
            await ws.send_json({'type': 'auth_invalid'})
            return ws
        await ws.send_json({'type': 'auth_ok', 'ha_version': '2026.6.4'})
        async for msg in ws:
            cmd = msg.json()
            if cmd['type'] in self.unsupported:
                await ws.send_json({'id': cmd['id'], 'type': 'result', 'success': False, 'error': {'code': 'unknown_command', 'message': 'Unsupported'}})
            else:
                values = {
                    'config/area_registry/list': [{'area_id': 'test', 'name': 'Test room'}],
                    'config/device_registry/list': [{'id': 'device-test', 'area_id': 'test'}],
                    'config/entity_registry/list': [{'entity_id': 'light.test', 'device_id': 'device-test'}],
                    'subscribe_events': None,
                }
                await ws.send_json({'id': cmd['id'], 'type': 'result', 'success': True, 'result': values[cmd['type']]})
        return ws


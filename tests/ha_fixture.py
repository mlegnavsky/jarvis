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
            target['state'] = 'locked' if path == '/core/api/services/lock/lock' else 'on'
            return web.json_response(self.states)
        if path == '/info':
            return web.json_response({'result': 'ok', 'data': {'arch': 'aarch64'}})
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


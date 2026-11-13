import unittest
from app.diagnostics import bounded_logs

class LogTests(unittest.TestCase):
    def test_redacts_suspect_lines_and_bounds(self):
        value = bounded_logs('safe\nAuthorization: Bearer abc\nhttps://user:pass@example.test\nlast', max_lines=3)
        self.assertNotIn('abc', str(value))
        self.assertNotIn('user:pass', str(value))
        self.assertEqual(value['omitted_lines'], 1)
        self.assertEqual(value['redacted_lines'], 2)

class DiagnosticsTests(unittest.IsolatedAsyncioTestCase):
    async def test_stages_report_unavailable_separately_from_empty_errors(self):
        from app.diagnostics import diagnose
        class Sup:
            timeout = 1
            async def request(self, method, path):
                if path == '/host/info':
                    raise ValueError('private diagnostic failure')
                return {'version': '1', 'memory_usage': 100, 'disk_free': 200, 'token': 'private'}
            async def _websocket(self):
                class WS:
                    async def send_json(self, value):
                        self.command = value['type']
                    async def receive_json(self):
                        return {'id': 1, 'success': True, 'result': {'issues': []} if self.command == 'repairs/list_issues' else []}
                    async def close(self):
                        pass
                return WS()
        value = await diagnose(Sup())
        self.assertTrue(value['partial'])
        self.assertEqual(value['stages']['host']['status'], 'unavailable')
        self.assertEqual(value['stages']['repairs']['data']['issues'], [])
        self.assertEqual(value['stages']['core_resources']['data']['memory_usage'], 100)
        self.assertNotIn('private', str(value))
        self.assertTrue(all('duration_ms' in stage for stage in value['stages'].values()))

    async def test_permission_map_uses_explicit_allowlist_without_state_attributes(self):
        from app.diagnostics import permission_map
        class Sup:
            async def request(self, method, path):
                return [{'entity_id': 'light.a', 'state': 'on', 'attributes': {'token': 'private'}},
                        {'entity_id': 'light.b', 'state': 'unavailable'}]
            async def registry(self, kind):
                return [{'entity_id': 'light.a', 'device_id': 'dev', 'area_id': 'room'},
                        {'entity_id': 'light.disabled', 'device_id': 'dev', 'disabled_by': 'user'}] if kind == 'entity' else []
        value = await permission_map(Sup(), {'allowed_entities': ['light.a'], 'allowed_services': ['light.turn_on']})
        entities = value['map']['data']['entities']
        self.assertTrue(entities[0]['allowed'])
        self.assertFalse(entities[1]['allowed'])
        self.assertEqual(value['map']['data']['entity_total'], 3)
        disabled = next(i for i in entities if i['entity_id'] == 'light.disabled')
        self.assertEqual(disabled['disabled_by'], 'user')
        self.assertEqual(disabled['state_status'], 'missing')
        self.assertIsNone(disabled['state_available'])
        self.assertEqual(disabled['device_id'], 'dev')
        self.assertNotIn('private', str(value))
        empty = await permission_map(Sup(), {})
        self.assertFalse(empty['map']['data']['entities'][0]['allowed'])

    async def test_log_transport_is_bounded_and_does_not_return_auth(self):
        from app.diagnostics import logs
        class Content:
            async def read(self, limit):
                self.limit = limit
                data = getattr(self, 'data', b'token=private\nsafe')
                self.data = b''
                return data
        class Response:
            status = 200
            content = Content()
            async def __aenter__(self):
                return self
            async def __aexit__(self, *args):
                pass
        class Session:
            def get(self, url, **kwargs):
                self.url, self.kwargs = url, kwargs
                return Response()
        class Sup:
            base, token, timeout = 'http://supervisor', 'private-auth', 1
            session = Session()
            async def _session(self):
                return self.session
        sup = Sup()
        value = await logs(sup, '/core/logs')
        self.assertNotIn('private', str(value))
        self.assertEqual(sup.session.url, 'http://supervisor/core/logs')
        self.assertFalse(sup.session.kwargs['allow_redirects'])
        self.assertEqual(value['lines'][-1], 'safe')

    async def test_chunked_log_http_reads_to_eof_or_limit(self):
        import asyncio
        from aiohttp import web
        from aiohttp.test_utils import TestServer
        from app.ha import HAClient
        from app.diagnostics import logs
        async def handler(request):
            response = web.StreamResponse()
            await response.prepare(request)
            try:
                if request.match_info['kind'] == 'small':
                    for number in range(20):
                        await response.write(('line %s\n' % number).encode())
                        await asyncio.sleep(0.001)
                    await response.write(b'last line\n')
                else:
                    for _ in range(70):
                        await response.write(b'ordinary line\n' * 80)
                        await asyncio.sleep(0.001)
                await response.write_eof()
            except ConnectionResetError:
                pass  # Bounded reader intentionally closes a larger response.
            return response
        app = web.Application()
        app.router.add_get('/{kind}', handler)
        async with TestServer(app) as server:
            client = HAClient('private', base=str(server.make_url('')).rstrip('/'))
            try:
                small = await logs(client, '/small')
                self.assertEqual(small['lines'][-1], 'last line')
                self.assertEqual(len(small['lines']), 21)
                self.assertFalse(small['source_truncated'])
                large = await logs(client, '/large')
                self.assertTrue(large['source_truncated'])
                self.assertLessEqual(len(large['lines']), 100)
            finally:
                await client.close()

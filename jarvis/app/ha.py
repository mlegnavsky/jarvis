"""Bounded internal Home Assistant API access. Never returns stale snapshots."""
import asyncio
from datetime import datetime, timezone
from urllib.parse import quote

import aiohttp


def now():
    return datetime.now(timezone.utc).isoformat()


class UpstreamError(Exception):
    pass


class HAClient:
    def __init__(self, token, base='http://supervisor', timeout=15):
        self.token = token
        self.base = base.rstrip('/')
        self.timeout = timeout
        self.session = None
        self.stream_connected = False
        self.last_event = None

    async def _session(self):
        if self.session is None:
            self.session = aiohttp.ClientSession()
        return self.session

    async def close(self):
        if self.session:
            await self.session.close()

    async def request(self, method, path, body=None):
        session = await self._session()
        try:
            async with session.request(method, self.base + path, json=body,
                    headers={'Authorization': 'Bearer ' + self.token},
                    timeout=aiohttp.ClientTimeout(total=self.timeout), allow_redirects=False) as response:
                if response.status != 200:
                    raise UpstreamError('upstream_http_' + str(response.status))
                value = await response.json()
                if path.startswith('/core/api/'):
                    return value
                if not isinstance(value, dict) or value.get('result') != 'ok':
                    raise UpstreamError('upstream_rejected')
                return value.get('data', {})
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as exc:
            raise UpstreamError('upstream_unavailable') from exc

    async def _websocket(self):
        session = await self._session()
        ws = None
        try:
            async with asyncio.timeout(self.timeout):
                ws = await session.ws_connect(self.base + '/core/websocket', heartbeat=30, max_msg_size=16*1024*1024)
                hello = await ws.receive_json()
                if hello.get('type') != 'auth_required':
                    raise UpstreamError('websocket_protocol')
                await ws.send_json({'type': 'auth', 'access_token': self.token})
                if (await ws.receive_json()).get('type') != 'auth_ok':
                    raise UpstreamError('websocket_auth')
            return ws
        except BaseException:
            if ws:
                await ws.close()
            raise

    async def registry(self, kind):
        ws = None
        try:
            async with asyncio.timeout(self.timeout):
                ws = await self._websocket()
                await ws.send_json({'id': 1, 'type': 'config/' + kind + '_registry/list'})
                result = await ws.receive_json()
                if result.get('id') != 1 or not result.get('success') or not isinstance(result.get('result'), list):
                    raise UpstreamError('registry_unavailable')
                return result['result']
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError, TypeError) as exc:
            raise UpstreamError('registry_unavailable') from exc
        finally:
            if ws:
                await ws.close()

    async def snapshot(self):
        attempted = now()
        jobs = {
            'states': self.request('GET', '/core/api/states'),
            'services': self.request('GET', '/core/api/services'),
            'core': self.request('GET', '/core/api/config'),
            'supervisor': self.request('GET', '/info'),
            'areas': self.registry('area'),
            'devices': self.registry('device'),
            'entities': self.registry('entity'),
        }
        values = await asyncio.gather(*jobs.values(), return_exceptions=True)
        data, errors = {}, {}
        for name, value in zip(jobs, values):
            expected = dict if name in ('core', 'supervisor') else list
            if isinstance(value, BaseException) or not isinstance(value, expected):
                errors[name] = 'unavailable'
                data[name] = None
            else:
                data[name] = value
        return {
            'attempted_at': attempted, 'captured_at': now() if data['states'] is not None else None,
            'connected': data['states'] is not None, 'partial': bool(errors),
            'states': data['states'], 'services': data['services'],
            'registries': {k: data[k] for k in ('areas', 'devices', 'entities')},
            'system': {k: data[k] for k in ('core', 'supervisor')}, 'errors': errors,
            'stream_connected': self.stream_connected,
        }

    async def state(self, entity_id):
        return await self.request('GET', '/core/api/states/' + quote(entity_id, safe=''))

    async def service(self, domain, service, data):
        return await self.request('POST', '/core/api/services/' + domain + '/' + service, data)

    async def watch(self, retry_delay=5):
        while True:
            ws = None
            try:
                ws = await self._websocket()
                await ws.send_json({'id': 1, 'type': 'subscribe_events', 'event_type': 'state_changed'})
                async with asyncio.timeout(self.timeout):
                    result = await ws.receive_json()
                    if not result.get('success'):
                        raise UpstreamError('subscription_rejected')
                self.stream_connected = True
                async for message in ws:
                    if message.type == aiohttp.WSMsgType.TEXT:
                        event = message.json()
                        if event.get('type') == 'event':
                            data = event.get('event', {}).get('data', {})
                            self.last_event = {'entity_id': data.get('entity_id'), 'received_at': now()}
            except (aiohttp.ClientError, UpstreamError, asyncio.TimeoutError, ValueError, TypeError):
                pass
            finally:
                self.stream_connected = False
                if ws:
                    await ws.close()
            await asyncio.sleep(retry_delay)

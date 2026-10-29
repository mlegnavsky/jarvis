"""Private Device Builder 1.25 transport through authenticated Supervisor ingress."""
import asyncio
import re
import uuid

import aiohttp

from .ha import UpstreamError


class FirmwareClient:
    COMMANDS = frozenset({'devices/list', 'devices/get_config', 'firmware/compile',
                          'firmware/install', 'firmware/upload', 'firmware/get_job',
                          'firmware/get_jobs'})

    def __init__(self, supervisor, slug='5c53de3b_esphome', timeout=20):
        self.supervisor, self.slug = supervisor, slug
        self.timeout = min(float(timeout), 20)

    async def call(self, command, args=None):
        if command not in self.COMMANDS or (args is not None and not isinstance(args, dict)):
            raise UpstreamError('firmware_unavailable')
        core = builder = None
        try:
            async with asyncio.timeout(self.timeout):
                core = await self.supervisor._websocket()
                # Core 2026.6.4 injects its authenticated user's identity and
                # forwards this using Core's own Supervisor credential.
                await core.send_json({'id': 1, 'type': 'supervisor/api',
                                      'endpoint': '/ingress/session', 'method': 'post', 'data': {}})
                reply = await self._receive(core, 'id', 1)
                session_token = reply.get('result', {}).get('session') if reply.get('success') is True else None
                if not isinstance(session_token, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,256}', session_token):
                    raise UpstreamError('firmware_unavailable')
                await core.close()
                core = None
                if not re.fullmatch(r'[a-z0-9_]{1,100}', self.slug):
                    raise UpstreamError('firmware_unavailable')
                info = await self.supervisor.request('GET', '/addons/' + self.slug + '/info')
                match = re.fullmatch(r'/api/hassio_ingress/([A-Za-z0-9_-]{1,256})/?', info.get('ingress_url', ''))
                if not match or info.get('state') != 'started':
                    raise UpstreamError('firmware_unavailable')
                session = await self.supervisor._session()
                builder = await session.ws_connect(
                    self.supervisor.base + '/ingress/' + match[1] + '/ws',
                    headers={'Cookie': 'ingress_session=' + session_token},
                    heartbeat=20, max_msg_size=2 * 1024 * 1024)
                hello = await builder.receive_json()
                if not isinstance(hello, dict) or hello.get('requires_auth') is not False:
                    raise UpstreamError('firmware_unavailable')
                message_id = uuid.uuid4().hex
                await builder.send_json({'command': command, 'message_id': message_id, 'args': args or {}})
                reply = await self._receive(builder, 'message_id', message_id)
                if 'error_code' in reply or 'result' not in reply:
                    raise UpstreamError('firmware_unavailable')
                return reply['result']
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError, TypeError, AttributeError,
                KeyError, IndexError, UpstreamError):
            raise UpstreamError('firmware_unavailable') from None
        finally:
            for websocket in (builder, core):
                if websocket is not None:
                    try:
                        async with asyncio.timeout(2):
                            await websocket.close()
                    except (aiohttp.ClientError, asyncio.TimeoutError):
                        pass

    @staticmethod
    async def _receive(websocket, field, expected):
        for _ in range(64):
            message = await websocket.receive_json()
            if not isinstance(message, dict):
                raise UpstreamError('firmware_unavailable')
            if message.get(field) == expected:
                return message
        raise UpstreamError('firmware_unavailable')

"""Exercise the Core-private transport against a real local WebSocket server."""
import ast
import asyncio
import re
import time
import unittest
import uuid
from pathlib import Path
from types import SimpleNamespace
import aiohttp
from aiohttp import web
from aiohttp.test_utils import TestServer

class TransportTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.commands=[];self.core_commands=[];self.closed=False
        async def handle(request):
            if request.cookies.get('ingress_session')!='private-session':return web.Response(status=401)
            ws=web.WebSocketResponse();await ws.prepare(request)
            await ws.send_json({'server_version':'1.25.0','requires_auth':False})
            async for message in ws:
                command=message.json();self.commands.append(command)
                await ws.send_json({'message_id':command['message_id'],'result':{'configured':[],'importable':[]}})
            self.closed=True
            return ws
        app=web.Application();app.router.add_get('/ingress/opaque/ws',handle)
        self.server=TestServer(app);await self.server.start_server()
        self.session=aiohttp.ClientSession()
        async def send_command(path,**kwargs):
            self.core_commands.append((path,kwargs))
            data={'session':'private-session'} if path=='/ingress/session' else {'state':'started','ingress_url':'/api/hassio_ingress/opaque'}
            return {'result':'ok','data':data}
        supervisor=SimpleNamespace(base_url=self.server.make_url('/'),send_command=send_command)
        self.hass=SimpleNamespace(data={'hassio':supervisor,'jarvis_firmware_bridge':{'sessions':{}}})
        # Isolate the transport function from HA-only registration imports;
        # its networking executes unchanged against aiohttp above.
        source=ast.parse((Path(__file__).parents[1]/'__init__.py').read_text())
        fn=next(n for n in source.body if isinstance(n,ast.AsyncFunctionDef) and n.name=='_native_call')
        env={'asyncio':asyncio,'aiohttp':aiohttp,'re':re,'time':time,'uuid':uuid,'DATA_COMPONENT':'hassio','DOMAIN':'jarvis_firmware_bridge','ADDON':'5c53de3b_esphome','async_get_clientsession':lambda hass:self.session}
        exec(compile(ast.Module(body=[fn],type_ignores=[]),'<native transport>','exec'),env)
        self.native=env['_native_call']
    async def asyncTearDown(self):
        await self.session.close();await self.server.close()
    async def test_core_authority_and_internal_cookie_and_cache(self):
        for _ in range(2):
            result=await self.native(self.hass,'admin-id','devices/list',{})
            self.assertEqual(result,{'configured':[],'importable':[]})
        self.assertEqual(len(self.core_commands),2)
        self.assertEqual(self.core_commands[0],('/ingress/session',{'method':'post','payload':{'user_id':'admin-id'},'source':'jarvis_firmware_bridge'}))
        self.assertEqual([c['command'] for c in self.commands],['devices/list','devices/list'])
        self.assertNotIn('private-session',str(result))

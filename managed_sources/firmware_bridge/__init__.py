"""Admin-only, target-scoped ESPHome firmware capability installed in HA Core."""
import asyncio
import re
import time
import uuid

import aiohttp
import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.components.hassio.const import DATA_COMPONENT
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .policy import COMMANDS, authorize, redact_result, valid_target

DOMAIN='jarvis_firmware_bridge'
ADDON='5c53de3b_esphome'
CONFIG_SCHEMA=vol.Schema({DOMAIN:vol.Schema({vol.Required('targets'):vol.All(cv.ensure_list,[vol.All(cv.string,vol.Match(r'^[A-Za-z0-9_-]+\.yaml$'))])})},extra=vol.ALLOW_EXTRA)

async def async_setup(hass,config):
    targets=tuple(config[DOMAIN]['targets'])
    if not targets or not all(valid_target(t) for t in targets):return False
    hass.data[DOMAIN]={'targets':targets,'sessions':{}}
    websocket_api.async_register_command(hass,websocket_request)
    return True

@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required('type'):DOMAIN+'/request',vol.Required('command'):vol.In(COMMANDS),vol.Optional('args',default=dict):dict})
@websocket_api.async_response
async def websocket_request(hass,connection,msg):
    try:
        state=hass.data[DOMAIN]
        args=authorize(msg['command'],msg.get('args',{}),state['targets'])
        async with asyncio.timeout(20):
            value=await _native_call(hass,connection.user.id,msg['command'],args)
        result=redact_result(msg['command'],value,state['targets'],args)
    except Exception:
        # Never expose credentials, YAML, firmware output, or remote diagnostics.
        connection.send_error(msg['id'],'firmware_unavailable','Firmware request unavailable')
        return
    connection.send_result(msg['id'],result)

async def _native_call(hass,user_id,command,args):
    supervisor=hass.data[DATA_COMPONENT]
    cache=hass.data[DOMAIN]['sessions']
    entry=cache.get(user_id)
    if entry is None or entry['expires']<=time.monotonic():
        # Core is the explicitly configured integration's authority. The
        # requesting administrator's identity remains attached to ingress.
        response=await supervisor.send_command('/ingress/session',method='post',payload={'user_id':user_id},source=DOMAIN)
        token=response.get('data',{}).get('session') if response.get('result')=='ok' else None
        response=await supervisor.send_command('/addons/'+ADDON+'/info',method='get',source=DOMAIN)
        info=response.get('data',{}) if response.get('result')=='ok' else {}
        match=re.fullmatch(r'/api/hassio_ingress/([A-Za-z0-9_-]{1,256})/?',info.get('ingress_url',''))
        if not isinstance(token,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,256}',token) or not match or info.get('state')!='started':raise ValueError('unavailable')
        entry={'token':token,'path':'/ingress/'+match[1]+'/ws','expires':time.monotonic()+300}
        cache[user_id]=entry
    ws=None
    try:
        session=async_get_clientsession(hass)
        ws=await session.ws_connect(str(supervisor.base_url).rstrip('/')+entry['path'],headers={'Cookie':'ingress_session='+entry['token']},heartbeat=20,max_msg_size=2*1024*1024)
        hello=await ws.receive_json()
        if not isinstance(hello,dict) or hello.get('requires_auth') is not False:raise ValueError('unavailable')
        message_id=uuid.uuid4().hex
        await ws.send_json({'command':command,'message_id':message_id,'args':args})
        for _ in range(64):
            reply=await ws.receive_json()
            if not isinstance(reply,dict):raise ValueError('unavailable')
            if reply.get('message_id')==message_id:
                if 'error_code' in reply or 'result' not in reply:raise ValueError('unavailable')
                return reply['result']
        raise ValueError('unavailable')
    except Exception:
        cache.pop(user_id,None)
        raise
    finally:
        if ws is not None:
            try:
                async with asyncio.timeout(2):await ws.close()
            except (aiohttp.ClientError,asyncio.TimeoutError):pass

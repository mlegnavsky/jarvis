"""Invoke the explicitly installed, target-scoped native HA firmware capability.

Supervisor intentionally excludes its own command prefix from addon Core
WebSocket proxies. This client uses a dedicated HA integration instead; it never
requests Supervisor sessions or credentials from the addon.
"""
import asyncio
import aiohttp
from .ha import UpstreamError

class FirmwareClient:
 COMMANDS=frozenset({'devices/list','firmware/compile','firmware/install','firmware/get_job','firmware/get_jobs'})
 def __init__(self,supervisor,timeout=20):self.supervisor=supervisor;self.timeout=min(float(timeout),20)
 async def call(self,command,args=None):
  if command not in self.COMMANDS or (args is not None and not isinstance(args,dict)):raise UpstreamError('firmware_unavailable')
  ws=None
  try:
   async with asyncio.timeout(self.timeout):
    ws=await self.supervisor._websocket()
    await ws.send_json({'id':1,'type':'jarvis_firmware_bridge/request','command':command,'args':args or {}})
    for _ in range(64):
     reply=await ws.receive_json()
     if not isinstance(reply,dict):raise UpstreamError('firmware_unavailable')
     if reply.get('id')!=1:continue
     if reply.get('success') is not True:raise UpstreamError('firmware_unavailable')
     return reply.get('result')
    raise UpstreamError('firmware_unavailable')
  except (aiohttp.ClientError,asyncio.TimeoutError,ValueError,TypeError,AttributeError,KeyError,IndexError,UpstreamError):
   self.last_failure_stage='native_ha_capability'
   raise UpstreamError('firmware_unavailable') from None
  finally:
   if ws is not None:
    try:
     async with asyncio.timeout(2):await ws.close()
    except (aiohttp.ClientError,asyncio.TimeoutError):pass

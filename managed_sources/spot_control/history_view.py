"""Authenticated, bounded and read-only access to permanent energy history."""
from functools import partial
import json
import math
import sqlite3
import time
from aiohttp import web
from homeassistant.components.http import HomeAssistantView

try:
    from .diagnostics import redact,diagnostic_snapshot
except ImportError:
    from diagnostics import redact,diagnostic_snapshot


class HistoryView(HomeAssistantView):
    url='/api/jarvis_spot_control/sales/history'
    name='api:jarvis_spot_control:sales:history'
    requires_auth=True

    def __init__(self,hass,journal,snapshot):
        self.hass,self.journal,self.snapshot=hass,journal,snapshot

    async def get(self,request):
        user=request.get('hass_user')
        if not user or not user.is_admin:
            return web.json_response({'error':'admin_required'},status=403)
        query=getattr(request,'query',{})
        allowed={'after','limit','since','until','kind','sale_id','until_id'}
        try:
            if set(query)-allowed:raise ValueError('Unknown query parameter')
            if hasattr(query,'getall') and any(len(query.getall(key))!=1 for key in query):
                raise ValueError('Duplicate query parameter')
            options={}
            for key in query:
                raw=query[key]
                if len(raw)>256:raise ValueError('Oversized query parameter')
                if key in ('after','limit','until_id'):
                    if not raw.isdecimal():raise ValueError('Invalid integer')
                    options[key]=int(raw)
                elif key in ('since','until'):
                    value=float(raw)
                    if not math.isfinite(value):raise ValueError('Invalid time')
                    options[key]=value
                else:options[key]=raw
            if query:
                body=await self.hass.async_add_executor_job(partial(self.journal.page,**options))
            else:
                body={'events':await self.hass.async_add_executor_job(self.journal.recent,1000),'retention':'permanent'}
            status=self.snapshot()
            return self.json(redact({**body,'status':status,'diagnostics':diagnostic_snapshot(status,time.time())}))
        except (OSError,sqlite3.Error,json.JSONDecodeError):
            return web.json_response({'error':'history_unavailable','retention':'permanent'},status=503)
        except (ValueError,TypeError,OverflowError):
            return web.json_response({'error':'invalid_history_query'},status=400)


class DiagnosticsView(HomeAssistantView):
    url='/api/jarvis_spot_control/sales/diagnostics'
    name='api:jarvis_spot_control:sales:diagnostics'
    requires_auth=True

    def __init__(self,snapshot):self.snapshot=snapshot

    async def get(self,request):
        user=request.get('hass_user')
        if not user or not user.is_admin:return web.json_response({'error':'admin_required'},status=403)
        return self.json(diagnostic_snapshot(self.snapshot(),time.time()))

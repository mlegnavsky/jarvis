"""Authenticated read-only journal API; legacy recent-history response is retained."""
import functools,time
from homeassistant.components.http import HomeAssistantView
from aiohttp import web
from .diagnostics import build_diagnostics

def register_history(hass,journal,snapshot):
 class History(HomeAssistantView):
  url='/api/jarvis_spot_control/sales/history';name='api:jarvis_spot_control:sales:history';requires_auth=True
  async def get(self,request):
   user=request.get('hass_user')
   if not user or not user.is_admin:return web.json_response({'error':'admin_required'},status=403)
   params=request.query
   if not params:return self.json({'events':await hass.async_add_executor_job(journal.recent,1000),'retention':'permanent','status':snapshot()})
   try:
    if set(params)-{'after','limit','until_id','kind','sale_id'}:raise ValueError('Unknown query')
    args={'after':int(params.get('after','0')),'limit':int(params.get('limit','100'))}
    if 'until_id' in params:args['until_id']=int(params['until_id'])
    for key in ('kind','sale_id'):
     if key in params:args[key]=params[key]
    result=await hass.async_add_executor_job(functools.partial(journal.page,**args))
   except (TypeError,ValueError):return web.json_response({'error':'invalid_history_query'},status=400)
   return self.json(result)
 class Diagnostics(HomeAssistantView):
  url='/api/jarvis_spot_control/sales/diagnostics';name='api:jarvis_spot_control:sales:diagnostics';requires_auth=True
  async def get(self,request):
   user=request.get('hass_user')
   if not user or not user.is_admin:return web.json_response({'error':'admin_required'},status=403)
   return self.json(build_diagnostics(snapshot(),time.time()))
 hass.http.register_view(History());hass.http.register_view(Diagnostics())

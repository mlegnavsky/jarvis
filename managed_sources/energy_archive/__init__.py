"""Private server archive. Credentials never reach browser/state/log output."""
import asyncio
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo
import aiohttp
import voluptuous as vol
from homeassistant.components.http import HomeAssistantView
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_time_interval
from .store import Outbox
DOMAIN='jarvis_energy_archive'
CONFIG_SCHEMA=vol.Schema({vol.Optional(DOMAIN):vol.Schema({})},extra=vol.ALLOW_EXTRA)
URL='https://laborator.odladeni.cz/energy-archive/index.php'
IDS=['sensor.inverter_pv_power','sensor.inverter_load_power','sensor.inverter_grid_power','sensor.inverter_battery','sensor.jarvis_spot_ote','sensor.jarvis_vykon_baterie','sensor.inverter_power_losses','sensor.inverter_today_production','sensor.inverter_today_load_consumption','sensor.inverter_today_energy_import','sensor.inverter_today_energy_export','sensor.inverter_total_production','sensor.inverter_total_load_consumption','sensor.inverter_total_energy_import','sensor.inverter_total_energy_export']
TZ=ZoneInfo('Europe/Prague')
async def async_setup(hass,config):
 session=async_get_clientsession(hass);lock=asyncio.Lock();seen={};last_ack=None;remote={}
 path=Path(hass.config.path('.storage','jarvis_energy_archive_outbox.sqlite'))
 queue=await hass.async_add_executor_job(Outbox,path)
 def auth():
  entries=[e for e in hass.config_entries.async_entries('webdav') if urlsplit(e.data.get('url','')).hostname=='laborator.odladeni.cz' and e.data.get('username')=='jarvis-backup']
  if len(entries)!=1:raise RuntimeError('Private WebDAV destination is missing or ambiguous')
  data=entries[0].data
  return aiohttp.BasicAuth(data['username'],data['password'])
 async def request(method,**kwargs):
  async with session.request(method,URL,auth=auth(),allow_redirects=False,timeout=aiohttp.ClientTimeout(total=30),**kwargs) as response:
   if response.status!=200:raise RuntimeError('Archive server returned HTTP '+str(response.status))
   return await response.json()
 async def state(status,error=None):
  count=await hass.async_add_executor_job(queue.count)
  attrs={'friendly_name':'Trvalý energetický archiv','version':'1.0.0','queued_records':count,'last_ack':last_ack,'interval_seconds':10,'server':remote,'retention':'permanent','notice':'Weather rows are issued forecasts, not measured weather. Samples retain source update timestamps.'}
  if error:attrs['error']=error
  hass.states.async_set('sensor.jarvis_energy_archive',status,attrs)
 async def capture(_now=None):
  now=datetime.now(timezone.utc);values={}
  for id in IDS:
   entity=hass.states.get(id)
   if entity is None:values[id]={'value':None,'source_updated':None};continue
   value=entity.state
   values[id]={'value':None if value in ('unknown','unavailable','') else value,'source_updated':entity.last_updated.isoformat()}
  try:
   await hass.async_add_executor_job(queue.append,{'kind':'sample','t':now.timestamp(),'values':values})
   for kind,id in [('spot','sensor.jarvis_spot_ote'),('weather','sensor.jarvis_pocasi_zitenice')]:
    entity=hass.states.get(id)
    if entity is None or entity.state in ('unknown','unavailable'):continue
    issued=entity.attributes.get('fetched_at')
    if not issued or seen.get(kind)==issued:continue
    record={'kind':kind,'t':now.timestamp(),'issued_at':issued,'attributes':dict(entity.attributes)}
    await hass.async_add_executor_job(queue.append,record);seen[kind]=issued
  except Exception as exc:await state('error',type(exc).__name__+': capture paused; existing queue preserved')
 async def flush(_now=None):
  nonlocal last_ack,remote
  if lock.locked():return
  async with lock:
   try:
    for _ in range(24):
     batch=await hass.async_add_executor_job(queue.batch)
     if batch is None:break
     key,body=batch
     result=await request('POST',data=body.encode(),headers={'Content-Type':'application/json','X-Batch-SHA256':key})
     await hass.async_add_executor_job(queue.ack,key,result.get('ack'));last_ack=datetime.now(timezone.utc).isoformat()
    remote=await request('GET',params={'op':'status'})
    first,last=remote.get('first'),remote.get('last')
    if first is not None and last is not None and float(last)-float(first)>=3600:
     remote['estimated_database_bytes_per_year']=round(remote['database_bytes']*31557600/(float(last)-float(first)))
    await state('ready' if await hass.async_add_executor_job(queue.count)==0 else 'uploading')
   except Exception as exc:await state('retrying',type(exc).__name__+': archive not acknowledged; durable queue retained')
 class ArchiveDay(HomeAssistantView):
  url='/api/jarvis_energy_archive/day';name='api:jarvis_energy_archive:day';requires_auth=True
  async def get(self,request_):
   from aiohttp import web
   try:
    date=datetime.strptime(request_.query.get('date',''),'%Y-%m-%d').replace(tzinfo=TZ)
    end=date+timedelta(days=1)
    data=await request('GET',params={'op':'day','start':date.timestamp(),'end':end.timestamp()})
    rows={id:[] for id in IDS}
    for sample in data['samples']:
     for id,value in sample.get('values',{}).items():
      if id in rows:rows[id].append({'t':round(sample['t']*1000),'v':value.get('value'),'source_updated':value.get('source_updated')})
    pub=data.get('publications',{})
    return self.json({'rows':rows,'weather':pub.get('weather',{}).get('attributes',{}).get('rows',[]),'spot':pub.get('spot',{}).get('attributes',{}).get('rows',[]),'forecast_issued_at':pub.get('weather',{}).get('issued_at'),'source':'private_server_archive','resolution_seconds':10})
   except ValueError:return web.json_response({'error':'invalid_date'},status=400)
   except Exception:return web.json_response({'error':'archive_unavailable'},status=503)
 hass.http.register_view(ArchiveDay())
 async def start(_event=None):
  await capture();await flush()
 async_track_time_interval(hass,capture,timedelta(seconds=10))
 async_track_time_interval(hass,flush,timedelta(seconds=60))
 if hass.is_running:hass.async_create_task(start())
 else:hass.bus.async_listen_once('homeassistant_started',start)
 return True

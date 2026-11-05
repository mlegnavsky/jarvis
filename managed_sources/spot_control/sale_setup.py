"""Home Assistant adapter for export. Credentials never enter sales history."""
import asyncio
from datetime import datetime,timedelta,timezone
import json
from pathlib import Path
import time
import voluptuous as vol
from homeassistant.helpers import discovery
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.service import async_register_admin_service
from homeassistant.helpers.storage import Store
from homeassistant.components.http import HomeAssistantView
from .sales import decide,price_at,market_rows,number,after_stop
from .sale_controller import SaleController
from .journal import Journal

DOMAIN='jarvis_spot_control'
KEY=DOMAIN+'_sales'
VERSION='0.4.0'

async def async_setup_sales(hass,config,charge_controller):
 store=Store(hass,1,KEY);saved=await store.async_load() or {}
 prefs={'automatic':False,'power_w':500,'minutes':3,'source':'pv','pv_verified':False,'battery_verified':False,**saved.get('settings',{})}
 journal=await hass.async_add_executor_job(Journal,Path(hass.config.path('.storage','jarvis_energy_sales.sqlite')))
 lock=asyncio.Lock();history_lock=asyncio.Lock();ready=False;last_reason='Připravuji měření.';last_decision=None;last_report=0
 archive_error='';runtime_error='';commission_requested=bool((config.get(DOMAIN) or {}).get('commission_pv_test',False))
 async def save_record(record):
  await store.async_save({'settings':dict(prefs),'transaction':record})
 async def persist_settings():await save_record(c.record)
 async def flush_history():
  nonlocal archive_error
  archive=hass.data.get('jarvis_energy_archive',{})
  append=archive.get('append_event') if isinstance(archive,dict) else None
  if append is None or history_lock.locked():return
  async with history_lock:
   try:
    rows=await hass.async_add_executor_job(journal.after,int(prefs.get('archived_event_id',0)),100)
    for row in rows:
     await append(row)
     prefs['archived_event_id']=row['id']
    if rows:await persist_settings()
    archive_error=''
   except Exception:archive_error='Odesílání historie čeká; trvalé místní záznamy jsou zachované.'
 async def event(kind,payload):
  nonlocal archive_error
  stamp=time.time()
  await hass.async_add_executor_job(journal.append,kind,payload,stamp)
  await flush_history()
 def read():return {s.entity_id:s.state for s in hass.states.async_all() if '.inverter_' in s.entity_id}
 def current_price():
  entity=hass.states.get('sensor.jarvis_spot_ote')
  if entity is None or entity.state in ('unknown','unavailable'):return None
  a=entity.attributes
  try:
   issued=datetime.fromisoformat(a['fetched_at']).timestamp()
   if not 0<=time.time()-issued<=2100:return None
   return price_at(a.get('rows',[]),time.time(),a.get('rate'))
  except (KeyError,TypeError,ValueError):return None
 def healthy():
  if charge_controller.active:return False
  ids=('sensor.inverter_battery','sensor.inverter_pv_power','sensor.inverter_battery_power','sensor.inverter_grid_power','sensor.inverter_battery_temperature')
  now=time.time()
  for entity_id in ids:
   state=hass.states.get(entity_id)
   reported=(getattr(state,'last_reported',None) or state.last_updated) if state else None
   if state is None or number(state.state) is None or reported is None or not 0<=now-reported.timestamp()<30:return False
  states=read();temp=number(states.get('sensor.inverter_battery_temperature'))
  if temp is None or not 0<=temp<45:return False
  if states.get('sensor.inverter_device_state')!='Normal' or states.get('sensor.inverter_device_alarm')!='OK' or states.get('sensor.inverter_device_fault')!='OK':return False
  for entity_id in ('sensor.inverter_device_state','sensor.inverter_device_alarm','sensor.inverter_device_fault','binary_sensor.inverter_battery_alarm','binary_sensor.inverter_battery_fault'):
   state=hass.states.get(entity_id)
   if state is None or entity_id.startswith('binary_sensor.') and state.state!='off':return False
   stamp=(getattr(state,'last_reported',None) or state.last_updated).timestamp()
   if not 0<=now-stamp<=60:return False
  return True
 def reported():
  stamps=[]
  for entity_id in ('sensor.inverter_grid_power','sensor.inverter_battery_power','sensor.inverter_pv_power'):
   state=hass.states.get(entity_id)
   if state is None:return None
   stamps.append((getattr(state,'last_reported',None) or state.last_updated).timestamp())
  return min(stamps) if max(stamps)-min(stamps)<=10 else None
 async def write(entity,value):
  domain=entity.split('.')[0]
  if domain=='number':service='set_value';data={'value':float(value)}
  elif domain=='select':service='select_option';data={'option':value}
  elif domain=='time':service='set_value';data={'time':value}
  else:service='turn_on' if value=='on' else 'turn_off';data={}
  issued=datetime.now(timezone.utc)
  async with asyncio.timeout(40):await hass.services.async_call(domain,service,{'entity_id':entity,**data},blocking=True)
  for _ in range(35):
   await asyncio.sleep(1)
   state=hass.states.get(entity)
   reported=(getattr(state,'last_reported',None) or state.last_updated) if state else None
   same=state is not None and (state.state==str(value) or number(state.state) is not None and number(state.state)==number(value))
   if same and reported is not None and reported>issued:return
  raise RuntimeError('Měnič nepotvrdil '+entity)
 c=SaleController(read,write,save_record,event,healthy=healthy,price=lambda:(current_price() or {}).get('net'),saved=saved.get('transaction'),reported=reported)
 async def handle_stop():
  if c.active or not c.last_stop or prefs.get('handled_stop_id')==c.last_stop['id']:return
  result=after_stop(prefs,c.last_stop);prefs.clear();prefs.update(result);await persist_settings()
 async def configure(changes):
  async with lock:
   before=dict(prefs);prefs.update(changes)
   try:await persist_settings();await event('settings_changed',{'before':before,'after':dict(prefs)})
   except Exception:prefs.clear();prefs.update(before);raise
 async def start_sale(data):
  nonlocal last_reason
  async with lock:
   if not ready:raise ValueError('Čekám na obnovu řízení.')
   mode=data.get('mode',prefs['source'])
   if mode=='battery' and not prefs['battery_verified']:
    raise ValueError('Bateriový prodej čeká na ověření nativního časového programu; přebytky panelů lze prodávat.')
   if charge_controller.active:raise ValueError('Nejprve ukonči nabíjecí test.')
   power=data.get('power_w',prefs['power_w']);minutes=data.get('duration_minutes',prefs['minutes'])
   purpose='manual'
   if not prefs['pv_verified']:
    if mode!='pv' or power>500 or minutes>3:raise ValueError('Nejprve ověřovací prodej panelů: nejvýše 500 W a 3 minuty.')
    purpose='commission'
   prefs['inhibited']=False
   await c.start(mode,power,minutes,purpose=purpose)
   last_reason='Ruční prodej · čekám na potvrzení dodávky.'
 async def stop_sale():
  changes={'automatic':False,'commission_cancelled':True,'commission_attempted':True}
  try:await configure(changes)
  except Exception:prefs.update(changes)
  await c.stop('manual');await handle_stop()
  if c.active:raise ValueError(c.error)
 def snapshot():
  p=current_price();entity=hass.states.get('sensor.inverter_battery')
  return {'version':VERSION,'ready':ready,'active':c.active,'observed':c.observed,'phase':c.record.get('phase','idle'),
   'settings':dict(prefs),'reason':last_reason,'error':c.error or runtime_error,'price':p,
   'mode':c.record.get('mode'),'power_w':c.record.get('power_w'),'deadline':c.record.get('deadline'),
   'healthy':healthy(),'battery_soc':number(entity.state) if entity else None,
   'history_error':archive_error,'notice':'Časové ukončení vyžaduje běžící řízení; při jeho výpadku může pokračovat PV export pod nativním limitem.'}
 def write_report(body):
  path=Path(hass.config.path('jarvis_workspace','sales-runtime.json'));path.parent.mkdir(exist_ok=True)
  temp=path.with_suffix('.tmp');temp.write_text(json.dumps(body,ensure_ascii=False,allow_nan=False));temp.replace(path)
 async def report():
  nonlocal last_report
  body=snapshot();hass.states.async_set('sensor.jarvis_energy_sales',body['phase'],{'friendly_name':'Prodej elektřiny',**body})
  states=read();source_ok=prefs['source']=='pv' or prefs['battery_verified']
  base_ok=states.get('select.inverter_work_mode')=='Zero Export To CT' and states.get('switch.inverter_export_surplus')=='off' and number(states.get('number.inverter_export_surplus_power')) is not None
  hass.states.async_set('binary_sensor.jarvis_sales_ready','on' if ready and not c.active and healthy() and source_ok and base_ok and current_price() and current_price()['net']>0 else 'off',{'friendly_name':'Prodej připraven'})
  hass.bus.async_fire('jarvis_sales_settings')
  if time.time()-last_report>=10:
   telemetry={}
   for entity_id in ('sensor.inverter_pv_power','sensor.inverter_grid_power','sensor.inverter_battery','sensor.inverter_battery_power','sensor.inverter_battery_current','sensor.inverter_temperature','sensor.inverter_battery_temperature','sensor.inverter_total_energy_export'):
    state=hass.states.get(entity_id)
    if state:telemetry[entity_id]={'state':state.state,'source_reported':(getattr(state,'last_reported',None) or state.last_updated).isoformat()}
   recent=await hass.async_add_executor_job(journal.recent,20)
   try:await hass.async_add_executor_job(write_report,{'captured_at':datetime.now(timezone.utc).isoformat(),**body,'telemetry':telemetry,'events':recent})
   except OSError:pass
   last_report=time.time()
 async def tick(_now=None):
  nonlocal ready,last_reason,last_decision,runtime_error
  if lock.locked() or c.lock.locked():return
  async with lock:
   try:
    if not ready:
     if c.active:await c.stop('recovery');await handle_stop()
     ready=not c.active
    was_active=c.active
    if c.active:await c.tick();await handle_stop()
    if was_active:return
    if not c.active and ready and healthy():
     p=current_price();entity=hass.states.get('sensor.inverter_battery');soc=number(entity.state) if entity else None
     ote=hass.states.get('sensor.jarvis_spot_ote');a=ote.attributes if ote else {}
     future=market_rows(a.get('rows',[]),a.get('rate'))
     decision=decide(soc,p,future,time.time())
     signature=(decision['mode'],decision['reason'],p['start'] if p else None,prefs['automatic'])
     if signature!=last_decision:
      await event('decision',{'decision':decision,'price':p,'automatic':prefs['automatic']});last_decision=signature
     last_reason=decision['reason']
     if commission_requested and not prefs.get('commission_cancelled') and not prefs.get('inhibited') and not prefs.get('commission_attempted') and p and p['net']>0 and soc is not None and soc>=98:
      prefs['commission_attempted']=True;await persist_settings()
      await c.start('pv',500,3,purpose='commission',promote_auto=True)
      last_reason='První ověřovací prodej přebytků · nejvýše 500 W / 3 minuty.'
     elif prefs['automatic'] and not prefs.get('inhibited') and prefs['pv_verified'] and decision['mode'] in ('pv','battery'):
      # Until battery hardware expiry is verified, release only PV headroom.
      mode=decision['mode'] if prefs['battery_verified'] else 'pv'
      if decision['mode']=='battery' and not prefs['battery_verified']:last_reason='Výhodná cena · zatím prodávám přebytky panelů; baterie čeká na ověření.'
      if mode=='pv' and soc<98:last_reason='Baterii ponechávám; čekám na přebytky panelů.'
      else:await c.start(mode,decision['power_w'],15,decision['minimum_soc'])
   except Exception as exc:
    runtime_error=str(exc)
    try:await event('controller_error',{'error':runtime_error})
    except Exception:pass
    prefs['automatic']=False;prefs['inhibited']=True
    if c.active:await c.stop('error');await handle_stop()
   finally:
    await flush_history()
    await report()
 async def service_start(call):await start_sale(dict(call.data));await report()
 async def service_stop(call):await stop_sale();await report()
 async def service_auto(call):
  if call.data['enabled']:await configure({'automatic':True,'inhibited':False,'commission_cancelled':False,'commission_attempted':False if not prefs['pv_verified'] else True})
  else:await stop_sale()
  await report()
 async_register_admin_service(hass,DOMAIN,'start_sale',service_start,vol.Schema({vol.Optional('mode'):vol.In(['pv','battery']),vol.Optional('power_w'):vol.All(vol.Coerce(float),vol.Range(min=100,max=9300)),vol.Optional('duration_minutes'):vol.All(vol.Coerce(float),vol.Range(min=1,max=60))}))
 async_register_admin_service(hass,DOMAIN,'stop_sale',service_stop,vol.Schema({}))
 async_register_admin_service(hass,DOMAIN,'set_sales_automatic',service_auto,vol.Schema({vol.Required('enabled'):bool}))
 class History(HomeAssistantView):
  url='/api/jarvis_spot_control/sales/history';name='api:jarvis_spot_control:sales:history';requires_auth=True
  async def get(self,request):
   user=request.get('hass_user')
   if not user or not user.is_admin:
    from aiohttp import web
    return web.json_response({'error':'admin_required'},status=403)
   return self.json({'events':await hass.async_add_executor_job(journal.recent,1000),'retention':'permanent','status':snapshot()})
 hass.http.register_view(History())
 hass.data[KEY]={'controller':c,'settings':prefs,'configure':configure,'report':report,'journal':journal,'start':start_sale,'stop':stop_sale}
 for platform in ('number','select','switch'):hass.async_create_task(discovery.async_load_platform(hass,platform,DOMAIN,{},config))
 async_track_time_interval(hass,tick,timedelta(seconds=5))
 if hass.is_running:hass.async_create_task(tick())
 else:hass.bus.async_listen_once('homeassistant_started',tick)
 await report()
 return c

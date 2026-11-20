"""Solar heating approved by the homeowner; actual device state stays authoritative."""
import asyncio
from datetime import datetime, timezone, timedelta
import logging
import hashlib
import json
import time
import voluptuous as vol
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED, EVENT_HOMEASSISTANT_STOP
from homeassistant.core import Context, callback
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_interval
from homeassistant.helpers.storage import Store
from .engine import Controller, ROOMS, numeric
from .resource_bridge import refresh_resource
from .grid_guard import check as grid_check, ENTITIES as GRID_ENTITIES
from .charge_link import ChargeLink

DOMAIN='jarvis_solar_heating'
VERSION='1.3.3'
AUTOMATION='automation.jarvis_solarni_topeni'
SWITCHES={'child':'switch.aqara_smart_plug_eu','living':'switch.aqara_smart_plug_eu_2'}
SENSORS={'temp':'sensor.aqara_temp_humidity_sensor_t1_teplota','pv':'sensor.inverter_pv_power','soc':'sensor.inverter_battery','discharge':'sensor.inverter_battery_power','load':'sensor.inverter_load_power'}
NAMES={'child':'Dětský pokoj','living':'Obývák'}
LOGGER=logging.getLogger(__name__)
CONFIG_SCHEMA=vol.Schema({vol.Optional(DOMAIN):vol.Schema({})},extra=vol.ALLOW_EXTRA)

async def async_setup(hass,config):
 store=Store(hass,1,DOMAIN+'.state');saved=await store.async_load() or {}
 controller=Controller(saved)
 lock=asyncio.Lock();own_contexts=set();pending_commands={};ready=False
 charge_link=ChargeLink(hass);intent_generation={r:0 for r in ROOMS};preparing={};charge_operations=asyncio.Lock()
 charge_members={r for r in ROOMS if controller.grid_manual[r]}
 last_error={r:None for r in ROOMS};resource_status={'status':'starting'}
 hass.data[DOMAIN]={'controller':controller,'version':VERSION}
 def value(key):
  state=hass.states.get(SENSORS[key])
  try:
   n=float(state.state) if state else None
   return n if numeric(n) else None
  except (ValueError,TypeError):return None
 def is_on(room):
  state=hass.states.get(SWITCHES[room]);return bool(state and state.state=='on')
 def persist():store.async_delay_save(controller.dump,2)
 def charge_count():
  charge_members.difference_update(r for r in tuple(charge_members) if not controller.grid_manual[r] and r not in preparing and not is_on(r))
  return len({r for r in ROOMS if controller.grid_manual[r] or r in preparing or r in charge_members and is_on(r)})
 async def cleanup_charge():
  if preparing:return
  async with charge_operations:
   if not preparing:
    count=charge_count()
    try:
     if count:await charge_link.resize(count)
     else:await charge_link.stop()
    except Exception:LOGGER.warning('Heating charge restoration remains pending')
 async def evaluate(_call=None):
  if not ready:return
  async with lock:
   now=time.time();inputs={key:value(key) for key in SENSORS}
   states={r:hass.states.get(SWITCHES[r]) for r in ROOMS}
   # Existing on-state after reload/restart retains persisted classification.
   for r,state in states.items():
    if state and state.state=='on' and not controller.on_since[r]:
     controller.on_since[r]=state.last_changed.timestamp()
   grid_ready,grid_reason=grid_check(hass.states.get,now)
   if any(controller.grid_manual.values()) and charge_link.ready():
    c=charge_link.controller() if callable(getattr(charge_link,'controller',None)) else None
    if callable(getattr(c,'connection_grace',None)) and c.connection_grace():grid_ready=True;grid_reason='Výpadek spojení · tolerance 3 min'
   if any(controller.grid_manual.values()) and not charge_link.ready():grid_ready=False;grid_reason='Dobíjení baterie není potvrzené'
   temp_state=hass.states.get(SENSORS['temp'])
   temp_stamp=(getattr(temp_state,'last_reported',None) or getattr(temp_state,'last_updated',None)) if temp_state else None
   if temp_stamp is None or not 0<=now-temp_stamp.timestamp()<=7200:
    grid_ready=False;grid_reason='Čeká na aktuální teplotu dětského pokoje'
   result=controller.evaluate(now,**inputs,grid_ready=grid_ready,grid_reason=grid_reason,**{r:is_on(r) for r in ROOMS})
   auto=hass.states.get(AUTOMATION);auto_enabled=auto is not None and auto.state=='on'
   for room in ROOMS:
    decision=result[room];state=states[room]
    if room in preparing and not controller.grid_manual[room]:decision.update(on=False,reason='Připravuji topení a dobíjení 1 kW')
    if not auto_enabled and not controller.manual[room] and not controller.grid_manual[room] and now>=controller.manual_off_until[room]:
     decision.update(on=False,reason='Automatika vypnutá')
    if state is None or state.state not in ('on','off'):
     decision.update(reason='Zásuvka offline');last_error[room]='switch_unavailable'
    elif (state.state=='on')!=decision['on']:
     pending=pending_commands.get(room)
     retry=not pending or pending['on']!=decision['on'] or now-pending.get('last_attempt',0)>=15
     if retry:
      issued=pending.get('issued_at',now) if pending and pending['on']==decision['on'] else now
      context=Context();own_contexts.add(context.id)
      if len(own_contexts)>256:own_contexts.clear();own_contexts.add(context.id)
      try:
       pending_commands[room]={'on':decision['on'],'issued_at':issued,'last_attempt':now}
       await hass.services.async_call('switch','turn_on' if decision['on'] else 'turn_off',{'entity_id':SWITCHES[room]},blocking=True,context=context)
       last_error[room]=None
      except Exception:
       last_error[room]='switch_service_failed';LOGGER.warning('Heating switch command failed for %s',room)
    actual=hass.states.get(SWITCHES[room]);on=actual is not None and actual.state=='on'
    if actual and actual.state in ('on','off') and on!=decision['on']:
     pending=pending_commands.get(room)
     waiting=pending and pending['on']==decision['on'] and 0<=time.time()-pending.get('issued_at',0)<15
     if last_error[room]!='switch_service_failed':last_error[room]=None if waiting else 'switch_state_not_confirmed'
    elif actual and actual.state in ('on','off') and on==decision['on']:
     # Reconcile delayed device reports and errors from earlier requests.
     last_error[room]=None
    label=decision['reason']
    if last_error[room]:label='Chyba ovládání' if last_error[room]!='switch_unavailable' else 'Zásuvka offline'
    elif on and not decision['on']:label='Čeká na vypnutí'
    elif not on and decision['on']:label='Čeká na zapnutí'
    hass.states.async_set('sensor.jarvis_topeni_'+room,label,{
     'friendly_name':'Topení – '+NAMES[room], 'icon':'mdi:radiator',
     'mode':'manual_off' if now<controller.manual_off_until[room] else 'grid_manual' if controller.grid_manual[room] else 'manual' if controller.manual[room] else 'auto','switch':SWITCHES[room],
     'grid_ready':grid_ready,'grid_reason':grid_reason,'manual_grid_target_c':24,
     'last_grid_stop':controller.grid_stop[room],'grid_discharge_since':controller.grid_discharge_since[room],
     'actual_state':actual.state if actual else 'unavailable','requested_on':decision['on'],
     'temperature':inputs['temp'],'battery_soc':inputs['soc'],'pv_mean_5m_w':result['average'],
     'full_battery_exception':result['full_battery'],'off_until':controller.off_until[room],
     'resource_status':dict(resource_status),'manual_off_until':controller.manual_off_until[room],'last_error':last_error[room],'settings':dict(controller.settings),'settings_revision':hashlib.sha256(json.dumps(controller.settings,sort_keys=True,allow_nan=False).encode()).hexdigest(),'version':VERSION,'updated_at':datetime.now(timezone.utc).isoformat()})
   hass.states.async_set('sensor.jarvis_topeni_solar_prumer',result['average'] if result['average'] is not None else 'unavailable',{
    'friendly_name':'Topení – solár průměr 5 minut','unit_of_measurement':'W','device_class':'power',
    'state_class':'measurement','coverage_seconds':result['coverage_seconds'],'window_seconds':300})
   persist()
   if hasattr(hass,'config'):
    payload={'version':VERSION,'updated_at':datetime.now(timezone.utc).isoformat(),'grid_ready':grid_ready,'grid_reason':grid_reason,'charging':charge_link.status(),'rooms':{r:{'state':hass.states.get('sensor.jarvis_topeni_'+r).state,'attributes':dict(hass.states.get('sensor.jarvis_topeni_'+r).attributes)} for r in ROOMS}}
    def write_report():
     from pathlib import Path
     path=Path(hass.config.path('jarvis_workspace','heating-runtime.json'));path.parent.mkdir(exist_ok=True)
     tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(payload,ensure_ascii=False,allow_nan=False));tmp.replace(path)
    try:await hass.async_add_executor_job(write_report)
    except Exception:LOGGER.warning('Heating diagnostic report could not be saved')
  await cleanup_charge()
 @callback
 def changed(event):
  if not ready:return
  entity=event.data.get('entity_id');old=event.data.get('old_state');new=event.data.get('new_state')
  if entity in SWITCHES.values() and new and new.state in ('on','off'):
   room=next(r for r,e in SWITCHES.items() if e==entity)
   if old and old.state in ('on','off') and old.state!=new.state:
    pending=pending_commands.get(room)
    explicit_owner=bool(getattr(new.context,'user_id',None))
    if not explicit_owner and (new.context.id in own_contexts or pending and pending['on']==(new.state=='on')):
     pending_commands.pop(room,None)
     if new.state=='on':controller.on_since[room]=time.time()
     else:controller.off_until[room]=time.time()+controller.settings['min_off_s'];controller.on_since[room]=0
    else:
     pending_commands.pop(room,None)
     intent_generation[room]+=1;preparing.pop(room,None)
     controller.external(room,new.state=='on',time.time())
    persist()
  hass.async_create_task(evaluate())
 @callback
 def service_called(event):
  if not ready or event.context.id in own_contexts:return
  data=event.data
  if data.get('domain') not in ('switch','homeassistant') or data.get('service') not in ('turn_on','turn_off','toggle'):return
  selected=data.get('service_data',{}).get('entity_id',[])
  if isinstance(selected,str):selected=[selected]
  for room,entity in SWITCHES.items():
   if entity in selected:
    on=data['service']=='turn_on' or (data['service']=='toggle' and not is_on(room))
    pending_commands.pop(room,None)
    intent_generation[room]+=1;preparing.pop(room,None)
    controller.external(room,on,time.time());persist()
    hass.async_create_task(evaluate())
 async def mode_service(call):
  room=call.data['room'];mode=call.data['mode']
  intent_generation[room]+=1;generation=intent_generation[room]
  keys=('manual','grid_manual','grid_stop','grid_discharge_since','manual_off_until','off_until','on_since')
  if mode=='grid_manual':
   async with lock:
    ok,reason=grid_check(hass.states.get,time.time());temp=value('temp')
    if not ok:raise ValueError(reason)
    if not numeric(temp) or temp>=24:raise ValueError('Teplota musí být nižší než 24 °C')
    preparing[room]=generation
    hass.states.async_set('sensor.jarvis_topeni_'+room,'Připravuji topení a dobíjení 1 kW',{'friendly_name':'Topení – '+NAMES[room],'version':VERSION})
   try:
    async with charge_operations:
     if generation!=intent_generation[room]:return
     count=charge_count()
     await charge_link.start(heaters=count)
    async with lock:
     if generation!=intent_generation[room]:return
     ok,reason=grid_check(hass.states.get,time.time());temp=value('temp')
     if not ok:raise ValueError(reason)
     if not numeric(temp) or temp>=24:raise ValueError('Teplota dosáhla 24 °C')
     previous={key:dict(getattr(controller,key)) for key in keys}
     pending_commands.pop(room,None);controller.request_grid(room,time.time())
     try:await store.async_save(controller.dump())
     except Exception:
      for key,v in previous.items():setattr(controller,key,v)
      raise
     charge_members.add(room)
   finally:
    if preparing.get(room)==generation:preparing.pop(room,None)
    await cleanup_charge()
   await evaluate();return
  preparing.pop(room,None);save_error=None
  async with lock:
   previous={key:dict(getattr(controller,key)) for key in keys}
   pending_commands.pop(room,None)
   if mode=='auto':controller.manual[room]=False;controller.grid_manual[room]=False;controller.manual_off_until[room]=0
   else:controller.external(room,mode=='manual',time.time())
   try:await store.async_save(controller.dump())
   except Exception as exc:
    if mode=='off':save_error=exc
    else:
     for key,v in previous.items():setattr(controller,key,v)
     raise
  await evaluate()
  if save_error:raise save_error
 async def configure(call):
  async with lock:
   expected=call.data.get('expected_revision')
   current=hashlib.sha256(json.dumps(controller.settings,sort_keys=True,allow_nan=False).encode()).hexdigest()
   if expected is not None and expected!=current:raise ValueError('heating_settings_changed')
   previous=dict(controller.settings)
   controller.configure(call.data['settings'])
   try:
    await store.async_save(controller.dump())
   except Exception:
    controller.settings=previous
    raise
  await evaluate()
 async def start(_event=None):
  nonlocal ready
  ready=True
  await evaluate()
  try:resource_status.update(await refresh_resource(hass))
  except Exception:resource_status.update(status='error');LOGGER.warning('Home-status resource update failed')
  hass.states.async_set('sensor.jarvis_heating_ui',resource_status['status'],{'friendly_name':'Ovládání radiátorů v přehledu','version':VERSION,**resource_status})
 async def stop(_event):await store.async_save(controller.dump())
 hass.services.async_register(DOMAIN,'configure',configure,schema=vol.Schema({vol.Required('settings'):dict,vol.Optional('expected_revision'):str}))
 hass.services.async_register(DOMAIN,'evaluate',evaluate,schema=vol.Schema({}))
 hass.services.async_register(DOMAIN,'set_mode',mode_service,schema=vol.Schema({vol.Required('room'):vol.In(ROOMS),vol.Required('mode'):vol.In(('auto','manual','off','grid_manual'))}))
 async_track_state_change_event(hass,list(set(SENSORS.values())|set(GRID_ENTITIES)|set(SWITCHES.values())|{AUTOMATION}),changed)
 async_track_time_interval(hass,evaluate,timedelta(seconds=15))
 hass.bus.async_listen('call_service',service_called)
 hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP,stop)
 if hass.is_running:await start()
 else:hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED,start)
 return True

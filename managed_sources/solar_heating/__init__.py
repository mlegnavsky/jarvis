"""Solar heating approved by the homeowner; actual device state stays authoritative."""
import asyncio
from datetime import datetime, timezone
import logging
import hashlib
import json
import time
import voluptuous as vol
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED, EVENT_HOMEASSISTANT_STOP
from homeassistant.core import Context, callback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.storage import Store
from .engine import Controller, ROOMS, numeric

DOMAIN='jarvis_solar_heating'
VERSION='1.2.0'
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
 last_error={r:None for r in ROOMS}
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
 async def evaluate(_call=None):
  if not ready:return
  async with lock:
   now=time.time();inputs={key:value(key) for key in SENSORS}
   states={r:hass.states.get(SWITCHES[r]) for r in ROOMS}
   # Existing on-state after reload/restart retains persisted classification.
   for r,state in states.items():
    if state and state.state=='on' and not controller.on_since[r]:
     controller.on_since[r]=state.last_changed.timestamp()
   result=controller.evaluate(now,**inputs,**{r:is_on(r) for r in ROOMS})
   auto=hass.states.get(AUTOMATION);auto_enabled=auto is not None and auto.state=='on'
   for room in ROOMS:
    decision=result[room];state=states[room]
    if not auto_enabled and not controller.manual[room]:
     decision.update(on=False,reason='Automatika vypnutá')
    if state is None or state.state not in ('on','off'):
     decision.update(reason='Zásuvka offline');last_error[room]='switch_unavailable'
    elif (state.state=='on')!=decision['on']:
     context=Context();own_contexts.add(context.id)
     if len(own_contexts)>256:own_contexts.clear();own_contexts.add(context.id)
     try:
      pending_commands[room]={'on':decision['on']}
      await hass.services.async_call('switch','turn_on' if decision['on'] else 'turn_off',{'entity_id':SWITCHES[room]},blocking=True,context=context)
      last_error[room]=None
     except Exception:
      last_error[room]='switch_service_failed';LOGGER.warning('Heating switch command failed for %s',room)
    actual=hass.states.get(SWITCHES[room]);on=actual is not None and actual.state=='on'
    if actual and actual.state in ('on','off') and on!=decision['on']:
     last_error[room]='switch_state_not_confirmed'
    elif actual and actual.state in ('on','off') and on==decision['on']:
     # Reconcile delayed device reports and errors from earlier requests.
     last_error[room]=None
    label=decision['reason']
    if last_error[room]:label='Chyba ovládání' if last_error[room]!='switch_unavailable' else 'Zásuvka offline'
    elif on and not decision['on']:label='Čeká na vypnutí'
    elif not on and decision['on']:label='Čeká na zapnutí'
    hass.states.async_set('sensor.jarvis_topeni_'+room,label,{
     'friendly_name':'Topení – '+NAMES[room], 'icon':'mdi:radiator',
     'mode':'manual_off' if now<controller.manual_off_until[room] else 'manual' if controller.manual[room] else 'auto','switch':SWITCHES[room],
     'actual_state':actual.state if actual else 'unavailable','requested_on':decision['on'],
     'temperature':inputs['temp'],'battery_soc':inputs['soc'],'pv_mean_5m_w':result['average'],
     'full_battery_exception':result['full_battery'],'off_until':controller.off_until[room],
     'manual_off_until':controller.manual_off_until[room],'last_error':last_error[room],'settings':dict(controller.settings),'version':VERSION,'updated_at':datetime.now(timezone.utc).isoformat()})
   hass.states.async_set('sensor.jarvis_topeni_solar_prumer',result['average'] if result['average'] is not None else 'unavailable',{
    'friendly_name':'Topení – solár průměr 5 minut','unit_of_measurement':'W','device_class':'power',
    'state_class':'measurement','coverage_seconds':result['coverage_seconds'],'window_seconds':300})
   persist()
 @callback
 def changed(event):
  if not ready:return
  entity=event.data.get('entity_id');old=event.data.get('old_state');new=event.data.get('new_state')
  if entity in SWITCHES.values() and new and new.state in ('on','off'):
   room=next(r for r,e in SWITCHES.items() if e==entity)
   if old and old.state in ('on','off') and old.state!=new.state:
    pending=pending_commands.get(room)
    if new.context.id in own_contexts or pending and pending['on']==(new.state=='on'):
     pending_commands.pop(room,None)
     if new.state=='on':controller.on_since[room]=time.time()
     else:controller.off_until[room]=time.time()+controller.settings['min_off_s'];controller.on_since[room]=0
    else:
     pending_commands.pop(room,None)
     controller.external(room,new.state=='on',time.time())
    persist()
  hass.async_create_task(evaluate())
 @callback
 def service_called(event):
  if not ready or event.context.id in own_contexts:return
  data=event.data
  if data.get('domain')!='switch' or data.get('service') not in ('turn_on','turn_off','toggle'):return
  selected=data.get('service_data',{}).get('entity_id',[])
  if isinstance(selected,str):selected=[selected]
  for room,entity in SWITCHES.items():
   if entity in selected:
    on=data['service']=='turn_on' or (data['service']=='toggle' and not is_on(room))
    pending_commands.pop(room,None)
    controller.external(room,on,time.time());persist()
 async def mode_service(call):
  room=call.data['room'];mode=call.data['mode']
  if mode=='auto':controller.manual[room]=False;controller.manual_off_until[room]=0
  elif mode=='manual':controller.external(room,True,time.time())
  elif mode=='off':
   controller.external(room,False,time.time())
   context=Context();own_contexts.add(context.id)
   await hass.services.async_call('switch','turn_off',{'entity_id':SWITCHES[room]},blocking=True,context=context)
  await evaluate()
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
 async def stop(_event):await store.async_save(controller.dump())
 hass.services.async_register(DOMAIN,'configure',configure,schema=vol.Schema({vol.Required('settings'):dict,vol.Optional('expected_revision'):str}))
 hass.services.async_register(DOMAIN,'evaluate',evaluate,schema=vol.Schema({}))
 hass.services.async_register(DOMAIN,'set_mode',mode_service,schema=vol.Schema({vol.Required('room'):vol.In(ROOMS),vol.Required('mode'):vol.In(('auto','manual','off'))}))
 async_track_state_change_event(hass,list(SENSORS.values())+list(SWITCHES.values())+[AUTOMATION],changed)
 hass.bus.async_listen('call_service',service_called)
 hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP,stop)
 if hass.is_running:await start()
 else:hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED,start)
 return True

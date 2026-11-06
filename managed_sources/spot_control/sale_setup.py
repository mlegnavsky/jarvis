"""Home Assistant adapter for export. Credentials never enter sales history."""
import asyncio
from datetime import datetime,timedelta,timezone
import json
from pathlib import Path
import time
from zoneinfo import ZoneInfo
import voluptuous as vol
from homeassistant.helpers import discovery
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.service import async_register_admin_service
from homeassistant.helpers.storage import Store
from homeassistant.components.http import HomeAssistantView
from .sales import decide,price_at,market_rows,number,after_stop,restore_measurement_intent
from .sale_controller import SaleController
from .journal import Journal
from .native_window import NativeWindow,WRITABLE
from .planning_setup import async_setup_planning
from .simple_sales import choose_daily_block,size_sale
from .battery_native import BatterySaleController,WRITABLE as BATTERY_WRITABLE
from .native_clock import sync_native_clock
from .native_snapshot import read_snapshot
from .native_plan import native_clock_acceptable, next_native_start
from .native_zero_target import set_zero_target, GRID_TARGET_W
from .solar_inputs import capacity_basis, house_power, cycle_acceptance
from .supervision import Supervisor
from .autonomous_verification import candidate as verification_candidate,finish as finish_verification
from .recovery_watchdog import recoverable_stop
from .daily_override import today_override
from .telemetry_health import evaluate_health, recoverable_battery_stop, MEASUREMENTS, STATUS
from .owner_settings import DEFAULTS as POLICY_DEFAULTS,validate as validate_policy,revision as policy_revision

DOMAIN='jarvis_spot_control'
KEY=DOMAIN+'_sales'
VERSION='0.9.3'
AUTO_EXPORT_LIMIT=9300

async def async_setup_sales(hass,config,charge_controller):
 store=Store(hass,1,KEY);saved=await store.async_load() or {}
 prefs={'automatic':False,'power_w':500,'minutes':3,'source':'pv','pv_verified':False,'battery_verified':False,'bias_verified':False,'bias_enabled':True,'auto_verification_enabled':False,'verification_resume_auto':False,**saved.get('settings',{})}
 prefs.setdefault('policy',dict(POLICY_DEFAULTS))
 def policy():return {**POLICY_DEFAULTS,**prefs.get('policy',{})}
 def cap():return policy()['max_w']
 def home_floor():return policy()['home_soc']
 prefs['auto_verification_enabled']=False  # Owner requests production only; no automatic commissioning.
 prefs.setdefault('requested_automatic',bool(prefs.get('automatic') or prefs.get('verification_resume_auto')))
 if not prefs['requested_automatic']:prefs['automatic']=False
 elif recoverable_battery_stop(prefs.get('battery_sale_proof') or {}):
  proof=prefs['battery_sale_proof']
  if prefs.get('handled_battery_stop_id')==proof.get('id') and not prefs.get('automatic'):
   prefs['measurement_recovery']={'pending':True,'stop_id':proof['id'],'source':'battery','stable_seconds':30}
 if cycle_acceptance(prefs.get('battery_sale_proof'))['failed']:
  prefs.update(automatic=False,battery_verified=False,inhibited=True)
 journal=await hass.async_add_executor_job(Journal,Path(hass.config.path('.storage','jarvis_energy_sales.sqlite')))
 try:prefs=restore_measurement_intent(prefs,await hass.async_add_executor_job(journal.recent,1000))
 except Exception:pass
 lock=asyncio.Lock();command_lock=asyncio.Lock();history_lock=asyncio.Lock();report_lock=asyncio.Lock();ready=False;last_reason='Připravuji měření.';last_decision=None;last_report=0;native_program={};window=None;battery=None;last_native_read=0;planning=None;last_power_adjust=0;low_pv_since=None;measurement_healthy_since=None;house_profile_confirmed=False
 supervisor=Supervisor(hass)
 archive_error='';runtime_error='';commission_requested=bool((config.get(DOMAIN) or {}).get('commission_pv_test',False))
 def home_plan():
  try:
   result=planning['snapshot']() if planning else {}
   reserve=number(result.get('required_soc'))
   if reserve is None or not 60<=reserve<=100 or result.get('quality') not in ('insufficient','conservative','calibrated','energy_only') or not isinstance(result.get('reason'),str):raise ValueError('Invalid optional plan')
   json.dumps(result,allow_nan=False)
   return result
  except Exception:
   return {'required_soc':100,'quality':'insufficient','reason':'Plán rezervy není dostupný; baterii ponechávám domu.','estimated_house_kwh':None,'credited_pv_kwh':None,'history_error':'Výpočet rezervy čeká.','feasible':False}
 async def save_record(record):
  await store.async_save({'settings':dict(prefs),'transaction':record,'native_window':window.record if window else saved.get('native_window',{}),'battery_sale':battery.record if battery else saved.get('battery_sale',{})})
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
 native_control_values={}
 def read():
  result={s.entity_id:s.state for s in hass.states.async_all() if '.inverter_' in s.entity_id}
  for entity,proof in native_control_values.items():
   actual=result.get(entity)
   same=lambda a,b:a==str(b) or number(a) is not None and number(a)==number(b)
   if 0<=time.time()-proof['verified_at']<30 and (same(actual,proof['before']) or same(actual,proof['value'])):
    result[entity]=str(proof['value'])
  return result
 def current_price():
  entity=hass.states.get('sensor.jarvis_spot_ote')
  if entity is None or entity.state in ('unknown','unavailable'):return None
  a=entity.attributes
  try:
   issued=datetime.fromisoformat(a['fetched_at']).timestamp()
   if not 0<=time.time()-issued<=2100:return None
   return price_at(a.get('rows',[]),time.time(),a.get('rate'),policy()['sale_fee'])
  except (KeyError,TypeError,ValueError):return None
 def fresh_number(entity_id,max_age=30):
  state=hass.states.get(entity_id)
  if state is None:return None
  stamp=(getattr(state,'last_reported',None) or state.last_updated).timestamp()
  return number(state.state) if 0<=time.time()-stamp<max_age else None
 def quotes():
  entity=hass.states.get('sensor.jarvis_spot_ote')
  if entity is None or entity.state in ('unknown','unavailable'):return []
  try:
   issued=datetime.fromisoformat(entity.attributes['fetched_at'])
   if issued.tzinfo is None or not 0<=time.time()-issued.timestamp()<=2100:return []
   return market_rows(entity.attributes.get('rows',[]),entity.attributes.get('rate'),policy()['sale_fee'])
  except (KeyError,TypeError,ValueError,OverflowError):return []
 def read_today_override():
  path=Path(hass.config.path('jarvis_workspace','sales-today-override.json'))
  if not path.exists():return None
  with path.open('rb') as stream:raw=stream.read(4097)
  if len(raw)>4096:raise ValueError('One-day override is too large')
  return json.loads(raw)
 async def select_block(rows):
  now=time.time()
  override=today_override(await hass.async_add_executor_job(read_today_override),rows,now)
  if override:
   previous=prefs.get('selected_block') or {}
   if not previous.get('one_day_override') or any(override[k]!=previous.get(k) for k in ('day','start','end')):
    prefs['selected_block']=override;await persist_settings()
    await event('daily_block_override',override)
   return prefs['selected_block']
  selected=prefs.get('selected_block')
  if isinstance(selected,dict):
   start=number(selected.get('start'));end=number(selected.get('end'))
   if start is not None and end is not None and end-start==policy()['block_minutes']*60 and now<end:
    valid=True
    for offset in range(int(policy()['block_minutes']/15)):
     matches=[row for row in rows if row['start']==start+offset*900]
     if len(matches)!=1 or matches[0]['net']<=0:valid=False;break
    if valid:return selected
  local=datetime.fromtimestamp(now,ZoneInfo('Europe/Prague'))
  selected=choose_daily_block(rows,local.date().isoformat(),now,policy()['block_minutes'])
  if selected is None:selected=choose_daily_block(rows,(local.date()+timedelta(days=1)).isoformat(),now,policy()['block_minutes'])
  if selected!=prefs.get('selected_block'):
   prefs['selected_block']=selected;await persist_settings()
   await event('daily_block_selected',{'selected_block':selected,'policy':'simple_daily_block','block_minutes':policy()['block_minutes'],'minimum_soc':policy()['sale_soc']})
  return selected
 def capacity():
  reported=hass.states.get('sensor.inverter_battery_capacity')
  return capacity_basis(fresh_number('number.inverter_battery_capacity',600),fresh_number('sensor.inverter_battery'),reported.state if reported else None)
 def house():
  mode=hass.states.get('select.inverter_work_mode')
  return house_power(fresh_number('sensor.jarvis_spotreba_domu'),fresh_number('sensor.inverter_load_power'),mode.state if mode else None)
 def battery_size(block,maximum_power_w=AUTO_EXPORT_LIMIT):
  return size_sale(fresh_number('sensor.inverter_battery'),capacity()['capacity_kwh'],block['start'],block['end'],time.time(),house(),max_export_w=min(cap(),maximum_power_w),minimum_soc=policy()['sale_soc'])
 def automatic_window_end(block):
  now=time.time();local=datetime.fromtimestamp(now,ZoneInfo('Europe/Prague'))
  cutoff=local.replace(hour=23,minute=40,second=0,microsecond=0).timestamp()
  end=min(block['end'],cutoff)
  return end if end-now>=10 else None
 def daylight_pv(pv):
  sun=hass.states.get('sun.sun')
  return pv is not None and pv>30 or sun is not None and sun.state=='above_horizon'
 def bias_profile_ready(states):
  return all(number(states.get(f'number.inverter_program_{i}_soc'))==home_floor() and (number(states.get(f'number.inverter_program_{i}_power')) or 0)>=500 and states.get(f'select.inverter_program_{i}_charging')=='Disabled' for i in range(1,7))
 def sale_decision(block,p,soc,pv):
  hold={'mode':'hold','power_w':0,'minimum_soc':policy()['sale_soc'],'reason':'Čekám na cenový blok, přebytky nebo ověřený malý přetok.'}
  if soc is None:return hold
  if p and p['net']>0:
   if soc>policy()['sale_soc'] and block and block['start']<=time.time()<block['end']-10 and automatic_window_end(block) is not None:
    return {'mode':'battery','power_w':cap(),'minimum_soc':policy()['sale_soc'],'reason':f"Prodej podle plánu · baterie nad {policy()['sale_soc']:g} %."}
   if prefs['pv_verified'] and soc>=policy()['pv_soc'] and daylight_pv(pv) and time.time()>=float(prefs.get('cooldown_until',0)):
    return {'mode':'pv','power_w':cap(),'minimum_soc':policy()['sale_soc'],'reason':'Baterie je téměř plná · dostupné přebytky.'}
  if p and prefs.get('bias_enabled') and prefs.get('bias_verified') and soc>=policy()['resume_soc'] and bias_profile_ready(read()):
   return {'mode':'bias','power_w':policy()['bias_w'],'minimum_soc':home_floor(),'reason':f"Malý trvalý přetok · cíl {policy()['bias_w']:g} W, rezerva {home_floor():g} %."}
  return hold
 def health_report():
  samples={}
  for entity_id in (*MEASUREMENTS,*STATUS):
   state=hass.states.get(entity_id)
   if state:
    reported=getattr(state,'last_reported',None) or state.last_updated
    samples[entity_id]={'state':state.state,'reported_at':reported.timestamp() if reported else None}
  return evaluate_health(samples,time.time(),charging=charge_controller.active)
 def healthy():return health_report()['healthy']
 def reported():
  stamps=[]
  for entity_id in ('sensor.inverter_grid_power','sensor.inverter_battery_power','sensor.inverter_pv_power'):
   state=hass.states.get(entity_id)
   if state is None:return None
   stamps.append((getattr(state,'last_reported',None) or state.last_updated).timestamp())
  return min(stamps) if max(stamps)-min(stamps)<=10 else None
 async def native_readback(entity,value,required=True,ha_before=None):
  if ha_before is None:
   initial=hass.states.get(entity);ha_before=initial.state if initial else None
  # This installation uses the verified deye_p3 register map. Never treat the
  # Solarman optimistic HA update as a physical setting readback.
  mapping={'number.inverter_export_surplus_power':(143,1),
   'select.inverter_work_mode':(142,1),'switch.inverter_export_surplus':(145,1),'number.inverter_zero_export_power':(104,1),
   'number.inverter_battery_max_discharging_current':(109,1)}
  mapping.update({f'number.inverter_program_{i}_soc':(165+i,1) for i in range(1,7)})
  if entity not in mapping:return
  entries=hass.config_entries.async_entries('solarman')
  if len(entries)!=1:raise RuntimeError('Nelze jednoznačně ověřit registr měniče.')
  device=entries[0].runtime_data.device;address,scale=mapping[entity];offset=0
  if entity=='number.inverter_zero_export_power':
   try:
    definitions=device.profile.parser.get_entity_descriptions('number')
    matches=[d for d in definitions if str(d.get('name','')).casefold()=='zero export power']
    if len(matches)==1:
     definition=matches[0];prefs['zero_export_definition']={k:definition[k] for k in ('name','registers','scale','offset','rule','write') if k in definition}
     address=min(definition['registers']);scale=number(definition.get('scale',1)) or 1;offset=number(definition.get('offset',0)) or 0
   except Exception:pass
  expected={'Zero Export To CT':2,'Export First':0,'Zero Export To Load':1,'on':1,'off':0}.get(value,value)
  expected=int(float(expected)/scale+offset)
  async with asyncio.timeout(15):raw=await device.execute(3,address,count=1)
  actual=raw[0] if isinstance(raw,list) and len(raw)==1 else None
  bulk_start,count=(166,6) if 166<=address<=171 else (142,4) if address in (142,143,145) else (98,14)
  async with asyncio.timeout(15):bulk=await device.execute(3,bulk_start,count=count)
  bulk_actual=bulk[address-bulk_start] if isinstance(bulk,list) and len(bulk)==count else None
  if bulk_actual!=actual:actual=None
  if actual==expected:
   native_control_values[entity]={'value':value,'before':ha_before,'verified_at':time.time()}
  await event('native_register_readback',{'entity':entity,'address':address,'expected':expected,'actual':actual,'sale_id':c.record.get('id')})
  if entity=='number.inverter_zero_export_power':prefs['native_grid_target_w']=(actual-offset)*scale if actual is not None else None
  if required and actual!=expected:raise RuntimeError(f'Měnič nepotvrdil registr {address}: požadováno {expected}, naměřeno {actual}.')
  return actual
 async def refresh_sale_controls():
  required=('select.inverter_work_mode','number.inverter_export_surplus_power','switch.inverter_export_surplus')
  if all(0<=time.time()-native_control_values.get(entity,{}).get('verified_at',-999)<15 for entity in required):return
  baseline={state.entity_id:state.state for state in hass.states.async_all() if '.inverter_' in state.entity_id}
  async with asyncio.timeout(15):raw=await native_device().execute(3,142,count=36)
  if not isinstance(raw,list) or len(raw)!=36 or any(type(v) is not int for v in raw):raise ValueError('Chybí úplné fyzické potvrzení režimu měniče.')
  if raw[0] not in (0,1,2) or raw[3] not in (0,1):raise ValueError('Měnič hlásí neznámý provozní režim.')
  values={'select.inverter_work_mode':{0:'Export First',1:'Zero Export To Load',2:'Zero Export To CT'}[raw[0]],'number.inverter_export_surplus_power':raw[1],'switch.inverter_export_surplus':'on' if raw[3] else 'off'}
  values.update({f'number.inverter_program_{i}_soc':raw[23+i] for i in range(1,7)})
  for entity,value in values.items():
   state=hass.states.get(entity);ha=state.state if state else None;old=native_control_values.get(entity)
   same=lambda a,b:a==str(b) or number(a) is not None and number(a)==number(b)
   # Preserve a distinct pending owner edit visible in HA; do not project over it.
   if old and same(value,old['value']) and not same(ha,old['before']) and not same(ha,old['value']):continue
   native_control_values[entity]={'value':value,'before':baseline.get(entity),'verified_at':time.time()}
 async def verify_baseline():
  await native_readback('select.inverter_work_mode','Zero Export To CT')
  await native_readback('switch.inverter_export_surplus','off')
  await native_readback('number.inverter_zero_export_power',GRID_TARGET_W,required=False)
 async def read_native_program():
  nonlocal native_program
  try:
   entries=hass.config_entries.async_entries('solarman')
   if len(entries)!=1:raise ValueError('Ambiguous inverter')
   device=entries[0].runtime_data.device
   async with asyncio.timeout(20):
    program=await device.execute(3,146,count=32)
    pv=await device.execute(3,340,count=1)
    bms=await device.execute(3,212,count=8)
    controls=await device.execute(3,98,count=14)
    clock=await device.execute(3,62,count=3)
   if len(clock)!=3 or len(program)!=32 or len(pv)!=1 or len(bms)!=8 or not isinstance(controls,list) or len(controls)!=14 or any(type(v) is not int for v in controls):raise ValueError('Incomplete native read')
   date=datetime(2000+(clock[0]>>8),clock[0]&255,clock[1]>>8,clock[1]&255,clock[2]>>8,clock[2]&255,tzinfo=ZoneInfo('Europe/Prague'))
   native_program={'captured_at':datetime.now(timezone.utc).isoformat(),'clock_local':date.isoformat(),'clock_error_seconds':date.timestamp()-time.time(),'clock_registers':clock,'registers_146_177':program,'max_pv_power_raw':pv[0],'bms_discharge_limit_a':bms[1],'bms_max_discharge_limit_a':bms[7],
    'register_104':controls[6],'register_109':controls[11],'native_grid_target_w':controls[6],'configured_discharge_current_a':controls[11]}
   prefs['native_grid_target_w']=controls[6]
  except Exception as exc:native_program={'error':type(exc).__name__+': '+str(exc)[:120]}
 async def write(entity,value,readback_required=True):
  initial=hass.states.get(entity);write_before=initial.state if initial else None
  domain=entity.split('.')[0]
  if domain=='number':service='set_value';data={'value':float(value)}
  elif domain=='select':service='select_option';data={'option':value}
  elif domain=='time':service='set_value';data={'time':value}
  else:service='turn_on' if value=='on' else 'turn_off';data={}
  issued=datetime.now(timezone.utc);issued_epoch=time.time();service_error=None
  try:
   async with asyncio.timeout(40):await hass.services.async_call(domain,service,{'entity_id':entity,**data},blocking=True)
  except Exception as exc:service_error=exc
  native=(entity in ('number.inverter_export_surplus_power','select.inverter_work_mode','switch.inverter_export_surplus','number.inverter_zero_export_power','number.inverter_battery_max_discharging_current') or entity.startswith('number.inverter_program_') and entity.endswith('_soc'))
  if native:
   # A fresh physical read confirms an unchanged setting too. HA config fields
   # can be sampled only every300s; their timestamps are not device ACKs.
   for delay in (0,1,2):
    if delay:await asyncio.sleep(delay)
    try:
     result=await native_readback(entity,value,required=readback_required,ha_before=write_before)
     if service_error is not None and (native_control_values.get(entity,{}).get('verified_at',-1)<issued_epoch):raise service_error
     if service_error is not None:await event('write_ack_reconciled',{'entity':entity,'value':value,'service_error':type(service_error).__name__})
     return result
    except Exception:
     if delay==2:raise
   return
  if service_error is not None:raise service_error
  for _ in range(35):
   await asyncio.sleep(1)
   state=hass.states.get(entity)
   reported=(getattr(state,'last_reported',None) or state.last_updated) if state else None
   same=state is not None and (state.state==str(value) or number(state.state) is not None and number(state.state)==number(value))
   if same and reported is not None and reported>issued:return
  raise RuntimeError('Měnič nepotvrdil '+entity)
 c=SaleController(read,write,save_record,event,healthy=healthy,price=lambda:(current_price() or {}).get('net'),saved=saved.get('transaction'),reported=reported)
 c.policy=policy
 def native_device():
  entries=hass.config_entries.async_entries('solarman')
  if len(entries)!=1:raise ValueError('Inverter interface is ambiguous')
  runtime=getattr(entries[0],'runtime_data',None)
  if runtime is None:raise ValueError('Inverter is not ready')
  return runtime.device
 async def native_test_read():
  return await read_snapshot(native_device())
 async def native_test_write(address,value):
  if address not in WRITABLE|BATTERY_WRITABLE:raise ValueError('Native register is outside commissioning scope')
  device=native_device()
  if address==109 or 166<=address<=171:
   entity='number.inverter_battery_max_discharging_current' if address==109 else f'number.inverter_program_{address-165}_soc'
   record=battery.record if battery and battery.active and battery.record.get('pending',{}).get(str(address),{}).get('value')==value else None
   phase=record.get('phase') if record else None
   conflicts=json.dumps(record.get('conflicts',{}),sort_keys=True) if record else None
   def confirmation_guard():
    if record is None:return
    if battery.record is not record or not battery.active or record.get('phase')!=phase or record.get('pending',{}).get(str(address),{}).get('value')!=value or json.dumps(record.get('conflicts',{}),sort_keys=True)!=conflicts:
     raise ValueError('Native numeric confirmation owner changed')
    if phase=='preparing':
     if time.time()>=record['arm_until']:raise ValueError('Native numeric confirmation arming deadline expired')
     battery._sample()
    elif phase=='stopping' and not battery._stopped():raise ValueError('Native cleanup confirmation needs fresh stopped grid')
   confirmation_guard()
   # Exactly one HA write. Later attempts only read; never overwrite a possible
   # owner change while waiting for the inverter's delayed physical update.
   await write(entity,value,readback_required=False)
   bulk_start,count=(98,14) if address==109 else (166,6)
   async with asyncio.timeout(25):
    for attempt,delay in enumerate((2,3,5),1):
     await asyncio.sleep(delay);confirmation_guard()
     raw=await device.execute(3,bulk_start,count=count)
     actual=raw[address-bulk_start] if isinstance(raw,list) and len(raw)==count and all(type(v) is int for v in raw) else None
     single=await native_readback(entity,value,required=False)
     await event('native_bulk_readback',{'entity':entity,'address':address,'bulk_start':bulk_start,'count':count,'expected':value,'actual':actual,'single_actual':single,'confirmation_attempt':attempt})
     confirmation_guard()
     if actual==value and single==value:return
   raise ValueError(f'Native bulk/single register {address} did not confirm {value}; bulk={actual}, single={single}')
  async with asyncio.timeout(20):
   await device.execute(16,address,data=[value])
   await asyncio.sleep(1) # Give the inverter configuration write time to settle.
   actual=await device.execute(3,address,count=1)
  if actual!=[value]:raise ValueError(f'Native commissioning register {address} did not confirm {value}')
 async def save_window(record):await store.async_save({'settings':dict(prefs),'transaction':c.record,'native_window':record,'battery_sale':battery.record if battery else saved.get('battery_sale',{})})
 async def save_battery(record):await store.async_save({'settings':dict(prefs),'transaction':c.record,'native_window':window.record if window else saved.get('native_window',{}),'battery_sale':record})
 def window_telemetry():
  states=read();health=health_report()
  voltage=hass.states.get('sensor.inverter_battery_voltage');current=hass.states.get('sensor.inverter_battery_current')
  stamp=lambda state:(getattr(state,'last_reported',None) or state.last_updated).timestamp() if state else None
  return {'soc':number(states.get('sensor.inverter_battery')),'grid_w':number(states.get('sensor.inverter_grid_power')),'battery_w':number(states.get('sensor.inverter_battery_power')),'pv_w':number(states.get('sensor.inverter_pv_power')),'healthy':health['healthy'],'health':health,'reported_at':reported(),'net_price':(current_price() or {}).get('net'),
   'voltage_v':number(voltage.state) if voltage else None,'current_a':number(current.state) if current else None,'voltage_reported_at':stamp(voltage),'current_reported_at':stamp(current)}
 window=NativeWindow(native_test_read,native_test_write,window_telemetry,save_window,event,saved=saved.get('native_window'))
 battery=BatterySaleController(native_test_read,native_test_write,window_telemetry,save_battery,event,saved=saved.get('battery_sale'))
 def active():return c.active or window.active or battery.active
 def clock_idle_profile(r):
  socs=[r.get(166+i) for i in range(6)];powers=[r.get(154+i) for i in range(6)]
  if (active() or charge_controller.active or not healthy() or r.get(0) not in (5,1280)
   or (r.get(98),r.get(111),r.get(130),r.get(142),r.get(145),r.get(146))!=(1,1,0,2,0,255)
   or len(set(socs))!=1 or socs[0] is None or not 0<socs[0]<60
   or len(set(powers))!=1 or powers[0] is None or powers[0]<500
   or any(r.get(172+i)!=0 for i in range(6))):raise ValueError('Hodiny lze udržovat jen v ověřeném neaktivním domácím režimu.')
  return True
 async def ensure_house_profile(recovering=False):
  nonlocal house_profile_confirmed
  # Owner explicitly wants the house supplied by battery down to30%, also
  # outside export windows. Migrate only the known old30/100% profile.
  if house_profile_confirmed and all(number(read().get(f'number.inverter_program_{i}_soc'))==home_floor() for i in range(1,7)):return True
  house_profile_confirmed=False
  async def admission():
   r=(await native_test_read())['registers']
   socs=[r.get(166+i) for i in range(6)];powers=[r.get(154+i) for i in range(6)]
   if (active() or charge_controller.active or not ((prefs.get('automatic') and not prefs.get('inhibited')) or (recovering and prefs.get('requested_automatic') and (prefs.get('measurement_recovery') or {}).get('pending'))) or not healthy()
    or r.get(0) not in (5,1280) or (r.get(98),r.get(111),r.get(130),r.get(142),r.get(145),r.get(146))!=(1,1,0,2,0,255)
    or any(v not in (home_floor(),prefs.get('previous_home_soc',30),30,100) for v in socs) or len(set(powers))!=1 or powers[0] is None or powers[0]<500
    or any(r.get(172+i)!=0 for i in range(6)) or (fresh_number('sensor.inverter_grid_power') is None or fresh_number('sensor.inverter_grid_power') < -100)):
    raise ValueError('Obnova domácí rezervy čeká na potvrzený neaktivní program bez nabíjení a přetoků.')
   return r
  r=await admission()
  if all(r.get(166+i)==home_floor() for i in range(6)):
   if (prefs.get('house_profile_write') or {}).get('pending'):
    await asyncio.sleep(3);r=await admission()
    if any(r.get(166+i)!=home_floor() for i in range(6)):return False
   house_profile_confirmed=all(number(read().get(f'number.inverter_program_{i}_soc'))==home_floor() for i in range(1,7))
   if house_profile_confirmed and (prefs.get('house_profile_write') or {}).get('pending'):
    prefs['house_profile_write']['pending']=False;await persist_settings()
   return house_profile_confirmed
  intent=prefs.get('house_profile_write')
  if intent and intent.get('pending'):
   raise ValueError('Čekám na potvrzení jednorázového skupinového zápisu domácí rezervy.')
  prefs['house_profile_write']={'pending':True,'before':[r[166+i] for i in range(6)],'target':[home_floor()]*6,'issued_at':time.time()}
  await persist_settings();await event('house_reserve_intent',dict(prefs['house_profile_write']))
  r=await admission()
  for i in range(1,7):
   ha=number(read().get(f'number.inverter_program_{i}_soc'))
   if ha not in (r[165+i],home_floor()):raise ValueError('Domácí rezervu mezitím změnil jiný držitel řízení.')
  async with asyncio.timeout(20):await native_device().execute(16,166,data=[int(home_floor())]*6)
  stable=0
  for delay in (2,3,5,10):
   await asyncio.sleep(delay);r=await admission()
   actual=[r.get(166+i) for i in range(6)]
   await event('house_reserve_bulk_readback',{'expected':[home_floor()]*6,'actual':actual})
   stable=stable+1 if actual==[home_floor()]*6 else 0
   if stable>=2:break
  if stable<2:raise ValueError(f'Měnič nepotvrdil domácí rezervu {home_floor():g} % ve dvou skupinových čteních.')
  prefs['house_profile_write']['pending']=False
  prefs['house_reserve_soc']=home_floor()
  house_profile_confirmed=all(number(read().get(f'number.inverter_program_{i}_soc'))==home_floor() for i in range(1,7))
  await persist_settings();await event('house_reserve_confirmed',{'minimum_soc':home_floor(),'registers':actual,'stable_reads':stable})
  return house_profile_confirmed
 async def clock_admission(get_response):
  registers={}
  for address,count in ((0,1),(98,14),(130,1),(142,36)):
   raw=await get_response(3,address,count=count)
   if not isinstance(raw,list) or len(raw)!=count or any(type(value) is not int for value in raw):raise ValueError('Nativní profil pro údržbu hodin není úplný.')
   registers.update({address+i:value for i,value in enumerate(raw)})
  return clock_idle_profile(registers)
 async def ensure_native_clock():
  data=await native_test_read()
  if native_clock_acceptable(data['clock'],time.time()):return
  if time.time()-float(prefs.get('clock_sync_attempt_at',0))<60:raise ValueError('Synchronizace hodin čeká na další povolený pokus.')
  clock_idle_profile(data['registers'])
  prefs['clock_sync_attempt_at']=time.time();await persist_settings()
  await event('native_clock_sync_intent',{'clock':data['clock'].isoformat(),'error_seconds':data['clock'].timestamp()-time.time()})
  clock_idle_profile((await native_test_read())['registers'])
  api=hass.data.get(KEY,{})
  api['clock_sync_active']=True
  try:result=await sync_native_clock(native_device(),admit=clock_admission)
  finally:api['clock_sync_active']=False
  prefs['native_clock_sync']=result;await persist_settings();await event('native_clock_sync_result',result)
  if result.get('verified') is not True:raise ValueError('Hodiny měniče nejsou po údržbě ověřené.')
  fresh=await native_test_read()
  if not native_clock_acceptable(fresh['clock'],time.time()):raise ValueError('Čerstvé hodiny měniče překračují povolenou provozní odchylku.')
 async def zero_import_target(valid_until=None):
  async with lock:
   def admission():
    return ready and not active() and not charge_controller.active and healthy() and not hass.data.get(KEY,{}).get('clock_sync_active') and (valid_until is None or time.time()<=valid_until)
   if not admission():raise ValueError('Cíl odběru 1 W vyžaduje čerstvá měření a neaktivní řízení.')
   result=await set_zero_target(native_device(),admission,event)
   prefs['zero_target_proof']=result;prefs['native_grid_target_w']=result.get('actual_w') if result.get('verified') is True else None
   await persist_settings();await event('native_zero_target_result',result)
   if result.get('verified') is not True:raise ValueError('Měnič nativně nepotvrdil cíl odběru 1 W: '+str(result.get('actual_w'))+' W.')
 async def commission_window(valid_until=None,solar_sell=False,selling_first=False):
  async with lock:
   if not ready or active() or charge_controller.active:raise ValueError('Nejprve ukonči současný test nebo prodej.')
   prefs.update(automatic=False,commission_cancelled=True,inhibited=False);await persist_settings()
   await ensure_native_clock()
   await window.start(valid_until,solar_sell=solar_sell,selling_first=selling_first)
 async def _bias_probe_locked(valid_until=None,autonomous=False):
  if not ready or active() or charge_controller.active or not healthy():raise ValueError('Malý přetok čeká na čerstvé měření a klid měniče.')
  if valid_until is not None and time.time()>valid_until:raise ValueError('Povel vypršel.')
  prefs.update(automatic=False,inhibited=True,bias_verified=False,commission_cancelled=True,verification_resume_auto=bool(autonomous));await persist_settings()
  await verify_baseline()
  await c.start('bias',2,3,minimum_soc=30,purpose='bias_probe')
  prefs['inhibited']=False;await persist_settings()
 async def bias_probe(valid_until=None):
  async with lock:
   resume=bool(prefs.get('requested_automatic'))
   if resume:prefs['auto_verification']={**(prefs.get('auto_verification') or {}),'kind':'bias'}
   await _bias_probe_locked(valid_until,autonomous=resume)
 async def _commission_battery_locked(valid_until=None,minimum_soc=90,power_w=500,autonomous=False):
  if valid_until is not None and time.time()>valid_until:raise ValueError('Povel před provedením vypršel.')
  if not ready or active() or charge_controller.active or not healthy():raise ValueError('Nejprve ukonči současný test nebo prodej a ověř měření.')
  if type(minimum_soc) is not int or minimum_soc not in (60,90):raise ValueError('Ověřovací rezerva musí být60 nebo90 %.')
  if type(power_w) is not int or power_w not in (500,2000):raise ValueError('Ověřovací výkon musí být500 nebo2000 W.')
  soc=fresh_number('sensor.inverter_battery')
  if soc is None or soc<minimum_soc+3:raise ValueError('Ověřovací test vyžaduje nejméně3 procentní body nad rezervou.')
  prefs.update(automatic=False,commission_cancelled=True,inhibited=False,verification_resume_auto=bool(autonomous));await persist_settings()
  await verify_baseline();await ensure_native_clock()
  await battery.start(power_w,5,minimum_soc,quotes(),valid_until=valid_until,purpose='commission',maximum_power_w=power_w)
 async def commission_battery(valid_until=None,minimum_soc=90,power_w=500):
  async with lock:
   resume=bool(prefs.get('requested_automatic'))
   if resume:prefs['auto_verification']={**(prefs.get('auto_verification') or {}),'kind':'battery'}
   await _commission_battery_locked(valid_until,minimum_soc,power_w,autonomous=resume)
 async def handle_native_stops():
  proof=getattr(window,'last_stop',None)
  if proof and proof.get('stop_verified') is True and prefs.get('native_window_proof',{}).get('id')!=proof.get('id'):
   prefs['native_window_proof']=dict(proof);await persist_settings()
  proof=battery.last_stop
  if battery.active or not proof or prefs.get('handled_battery_stop_id')==proof.get('id'):return
  prefs['handled_battery_stop_id']=proof.get('id');prefs['battery_sale_proof']=dict(proof)
  prefs['last_diagnostic_stop']={**proof,'mode':'battery','stopped_at':time.time()}
  accepted=(all(proof.get(key) is True for key in ('observed','native_expiry_observed','stop_verified'))
   and proof.get('reason')=='deadline' and proof.get('purpose')=='commission' and type(proof.get('power_w')) is int and proof.get('power_w') in (500,2000)
   and type(proof.get('minimum_soc')) is int and proof.get('minimum_soc') in (60,90) and proof.get('native_power_fence') is True and proof.get('phase')=='complete' and not proof.get('conflicts'))
  if proof.get('purpose')=='commission':
   prefs['automatic']=False
   prefs['battery_verified']=accepted
   if accepted:await event('battery_native_acceptance',dict(proof))
  normal=proof.get('reason') in ('deadline','manual','price','reserve','budget','energy_budget') or proof.get('reason')=='recovery' and proof.get('purpose')=='automatic' and proof.get('stop_verified') is True
  if cycle_acceptance(proof)['failed']:
   prefs['battery_verified']=False;normal=False
  if proof.get('conflicts'):normal=False
  if not normal:prefs.update(automatic=False,inhibited=True)
  if prefs.get('requested_automatic') and recoverable_battery_stop(proof):
   prefs['measurement_recovery']={'pending':True,'stop_id':proof['id'],'source':'battery','stable_seconds':30}
  if proof.get('purpose')=='commission' and prefs.get('auto_verification',{}).get('kind')=='battery':
   result=finish_verification(prefs,proof,accepted,time.time());prefs.clear();prefs.update(result)
  await persist_settings()
 async def handle_stop():
  if c.active and c.record.get('inhibited') and (prefs.get('automatic') or not prefs.get('inhibited')):
   prefs.update(automatic=False,inhibited=True);await persist_settings()
  if c.active or not c.last_stop or prefs.get('handled_stop_id')==c.last_stop['id']:return
  result=after_stop(prefs,c.last_stop)
  result['last_diagnostic_stop']={**c.last_stop,'stopped_at':time.time()}
  if c.last_stop.get('mode')=='bias' and c.last_stop.get('purpose')=='bias_probe' and result.get('auto_verification',{}).get('kind')=='bias':
   result=finish_verification(result,c.last_stop,result.get('bias_verified') is True,time.time())
  prefs.clear();prefs.update(result);await persist_settings()
 async def _configure_locked(changes,valid_until=None):
  if valid_until is not None and time.time()>valid_until:raise ValueError('Povel před provedením vypršel.')
  if changes.get('automatic') is True and any(getattr(controller,'active',False) and getattr(controller,'record',{}).get('phase')=='stopping' for controller in (window,battery,c)):
   raise ValueError('Čekám na potvrzené ukončení předchozího prodeje.')
  if 'automatic' in changes and 'requested_automatic' not in changes:changes={**changes,'requested_automatic':bool(changes['automatic'])}
  if changes.get('automatic') is False:changes={**changes,'verification_resume_auto':False,'measurement_recovery':{}}
  if changes.get('automatic') is True:changes={**changes,'measurement_recovery':{}}
  before=dict(prefs);prefs.update(changes)
  try:await persist_settings();await event('settings_changed',{'before':before,'after':dict(prefs)})
  except Exception:prefs.clear();prefs.update(before);raise
 async def configure(changes,valid_until=None):
  async with lock:
   await _configure_locked(changes,valid_until)
 async def configure_policy(changes,expected_revision):
  async with lock:
   current=policy()
   if expected_revision!=policy_revision(current):raise ValueError('Nastavení mezitím změnil jiný uživatel. Obnovte hodnoty a zkuste to znovu.')
   candidate=validate_policy(current,changes)
   if candidate==current:return
   if active() or charge_controller.active:raise ValueError('Nejdřív ručně zastavte prodej nebo nabíjení. Nastavení běžícího prodeje se nemění.')
   before=dict(prefs)
   if candidate['home_soc']!=current['home_soc']:prefs['previous_home_soc']=current['home_soc']
   prefs['policy']=candidate
   if candidate['block_minutes']!=current['block_minutes'] or candidate['sale_fee']!=current['sale_fee']:prefs.pop('selected_block',None)
   if any(candidate[k]!=current[k] for k in ('sale_fee','purchase_rate')):
    prefs['rate_history']=[*(prefs.get('rate_history') or []),{'at':time.time(),'purchase_rate':candidate['purchase_rate'],'sale_fee':candidate['sale_fee']}]
   try:await persist_settings()
   except Exception:prefs.clear();prefs.update(before);raise
  await event('owner_policy_saved',{'changes':changes,'revision':policy_revision(candidate)})
  await report()
 async def service_policy(call):await configure_policy(call.data['changes'],call.data['expected_revision'])
 async def start_sale(data,valid_until=None):
  nonlocal last_reason
  async with lock:
   if valid_until is not None and time.time()>valid_until:raise ValueError('Povel před provedením vypršel.')
   if not ready:raise ValueError('Čekám na obnovu řízení.')
   if active():raise ValueError('Nejprve ukonči současný prodej nebo ověření časového programu měniče.')
   mode=data.get('mode',prefs['source'])
   if mode not in ('pv','battery'):raise ValueError('Neplatný zdroj prodeje.')
   if mode=='battery' and not prefs['battery_verified']:
    raise ValueError('Bateriový prodej čeká na ověření nativního časového programu; přebytky panelů lze prodávat.')
   if charge_controller.active:raise ValueError('Nejprve ukonči nabíjecí test.')
   power=data.get('power_w',prefs['power_w']);minutes=data.get('duration_minutes',prefs['minutes'])
   if mode=='battery':
    if number(minutes) is None or not 5<=float(minutes)<=60:raise ValueError('Bateriový segment vyžaduje5 až60 minut.')
    end=time.time()+float(minutes)*60
    sizing=size_sale(fresh_number('sensor.inverter_battery'),capacity()['capacity_kwh'],time.time(),end,time.time(),house(),max_export_w=min(AUTO_EXPORT_LIMIT,float(power)),minimum_soc=60)
    if sizing['power_w']<100:raise ValueError(sizing['reason'])
    await verify_baseline();await ensure_native_clock()
    prefs['inhibited']=False
    await battery.start(sizing['power_w'],float(minutes),60,quotes(),valid_until=valid_until,purpose='manual',maximum_power_w=min(AUTO_EXPORT_LIMIT,float(power)))
    last_reason='Ruční bateriový prodej čeká na nativní začátek.'
    return
   purpose='manual'
   if not prefs['pv_verified']:
    if mode!='pv' or power>500 or minutes>3:raise ValueError('Nejprve ověřovací prodej panelů: nejvýše 500 W a 3 minuty.')
    purpose='commission'
   prefs['inhibited']=False
   await verify_baseline()
   if valid_until is not None and time.time()>valid_until:raise ValueError('Povel před provedením vypršel.')
   await c.start('pv',power,minutes,minimum_soc=60,purpose=purpose)
   last_reason='Ruční prodej · čekám na potvrzení dodávky.'
 async def stop_sale(requested_off=True):
  changes={'automatic':False,'requested_automatic':False if requested_off else prefs.get('requested_automatic',False),'verification_resume_auto':False,'commission_cancelled':True,'commission_attempted':True}
  async with lock:
   # Keep the disable and the physical cleanup in one control transaction.
   # A newer enable must not overtake an older stop waiting for this lock.
   try:await _configure_locked(changes)
   except Exception:prefs.update(changes)
   if window.active:await window.stop('manual')
   if battery.active:await battery.stop('manual')
   await c.stop('manual');await handle_stop()
   await handle_native_stops()
  if active():raise ValueError(c.error or window.error or battery.error or 'Čekám na potvrzení ukončení.')
 def snapshot():
  p=current_price();entity=hass.states.get('sensor.inverter_battery')
  return {'version':VERSION,'ready':ready,'active':active(),'observed':bool(window.record.get('observed')) if window.active else battery.observed if battery.active else c.observed,'phase':'native_test' if window.active else battery.record.get('phase','idle') if battery.active else c.record.get('phase','idle'),'native_program':native_program,'native_test':{k:v for k,v in window.record.items() if k!='before'},'native_test_error':window.error,
   'battery_sale':{k:v for k,v in battery.record.items() if k not in ('before','expected','pending')},'battery_sale_error':battery.error,'native_start':battery.record.get('start'),'selected_block':prefs.get('selected_block'),'sale_policy':'block_and_soc','automatic_battery_policy':'scheduled_above_60','automatic_battery_requires_commission':False,'sale_floor_soc':policy()['sale_soc'],
   'bias_status':({'average_grid_w':c.record.get('bias_average_w'),'target_export_w':policy()['bias_w']} if c.active and c.record.get('mode')=='bias' else None),'bias_policy':{'enabled':prefs.get('bias_enabled',True),'target_export_w':policy()['bias_w'],'minimum_soc':home_floor(),'resume_soc':policy()['resume_soc'],'verified':prefs.get('bias_verified',False),'ha_required':True},'charging_active':charge_controller.active,'capacity':capacity(),'house_power_w':house(),'last_cycle':cycle_acceptance(prefs.get('battery_sale_proof')),'settings':dict(prefs),'policy':policy(),'policy_revision':policy_revision(policy()),'automatic_requested':bool(prefs.get('requested_automatic')),'autonomous_verification':autonomous_state(),'measurement_recovery':dict(prefs.get('measurement_recovery') or {}),'pv_surplus_soc':policy()['pv_soc'],'last_stop':prefs.get('last_sale_stop'),'diagnostic_stop':prefs.get('last_diagnostic_stop') or prefs.get('last_sale_stop'),'reason':('Ověřovací test baterie · '+window.record.get('phase','')+f" · 500 W / 5 minut / rezerva {window.record.get('minimum_soc',95)} %." if window.active else 'Automatika pozastavena po zásahu ochrany. '+(c.error or battery.error or 'Čeká na odeznění příčiny a potvrzení bezpečného režimu.') if prefs.get('inhibited') else last_reason),'error':window.error if window.active else battery.error if battery.active else c.error or runtime_error,'price':p,
   'mode':'battery_commission' if window.active else 'battery' if battery.active else c.record.get('mode'),'power_w':500 if window.active else battery.record.get('power_w') if battery.active else c.record.get('power_w'),'deadline':window.record.get('end') if window.active else battery.record.get('end') if battery.active else c.record.get('deadline'),
   'grid_target_w':GRID_TARGET_W,'native_grid_target_w':prefs.get('native_grid_target_w'),'grid_target_confirmed':prefs.get('zero_target_proof',{}).get('verified') is True and len(prefs.get('zero_target_proof',{}).get('read_shapes',[]))==2 and prefs.get('zero_target_proof',{}).get('actual_w')==GRID_TARGET_W and prefs.get('native_grid_target_w')==GRID_TARGET_W,'grid_import_policy':f"Malý přetok {policy()['bias_w']:g} W; domácí rezerva {home_floor():g} %; plánovaný prodej do {policy()['sale_soc']:g} %.",'automatic_limit_w':cap(),'healthy':healthy(),'health':health_report(),'battery_soc':number(entity.state) if entity else None,
   'history_error':archive_error,'planning':home_plan(),'notice':'Časové ukončení vyžaduje běžící řízení; při jeho výpadku může pokračovat PV export pod nativním limitem.'}
 def write_report(body):
  path=Path(hass.config.path('jarvis_workspace','sales-runtime.json'));path.parent.mkdir(exist_ok=True)
  temp=path.with_suffix('.tmp');temp.write_text(json.dumps(body,ensure_ascii=False,allow_nan=False));temp.replace(path)
 async def report(_now=None):
  nonlocal last_report
  if report_lock.locked():return
  async with report_lock:
   body=snapshot()
   telemetry={}
   for entity_id in ('sensor.inverter_pv_power','sensor.inverter_grid_power','sensor.inverter_battery','sensor.inverter_battery_power','sensor.inverter_battery_current','sensor.inverter_temperature','sensor.inverter_battery_temperature','sensor.inverter_total_energy_export','number.inverter_zero_export_power'):
    state=hass.states.get(entity_id)
    if state:telemetry[entity_id]={'state':state.state,'source_reported':(getattr(state,'last_reported',None) or state.last_updated).isoformat()}
   body['telemetry']=telemetry
   try:body['supervision']=supervisor.publish(body)
   except Exception as exc:
    body['supervision']={'status':'error','alerts':[],'error':type(exc).__name__}
    hass.states.async_set('sensor.jarvis_solar_dohled','error',{'friendly_name':'Dohled nad solárem','error':type(exc).__name__})
   hass.states.async_set('sensor.jarvis_energy_sales',body['phase'],{'friendly_name':'Prodej elektřiny',**body})
   states=read();source_ok=prefs['source']=='pv' or prefs['battery_verified']
   base_ok=states.get('select.inverter_work_mode')=='Zero Export To CT' and states.get('switch.inverter_export_surplus')=='off' and number(states.get('number.inverter_export_surplus_power')) is not None
   hass.states.async_set('binary_sensor.jarvis_sales_ready','on' if ready and not active() and healthy() and source_ok and base_ok and current_price() and current_price()['net']>0 else 'off',{'friendly_name':'Prodej připraven'})
   hass.bus.async_fire('jarvis_sales_settings')
   if time.time()-last_report>=10:
    recent=await hass.async_add_executor_job(journal.recent,80)
    try:await hass.async_add_executor_job(write_report,{'captured_at':datetime.now(timezone.utc).isoformat(),**body,'telemetry':telemetry,'events':recent})
    except OSError:pass
    last_report=time.time()
 def read_command():
  path=Path(hass.config.path('jarvis_workspace','sales-command.json'))
  if not path.exists():return None
  with path.open('rb') as stream:raw=stream.read(4097)
  if len(raw)>4096:return None
  try:
   body=json.loads(raw)
   if not isinstance(body,dict) or set(body)!={'id','issued_at','expires_at','action','data'}:return None
   if not isinstance(body['id'],str) or not 1<=len(body['id'])<=80:return None
   issued=number(body['issued_at']);expires=number(body['expires_at']);now=time.time()
   previous=prefs.get('command',{})
   if issued is None or expires is None or not issued<=now<=expires<=issued+120:return None
   if issued<=previous.get('issued_at',0):return None
   schemas={
    'start':vol.Schema({vol.Optional('mode'):vol.In(['pv','battery']),vol.Optional('power_w'):vol.All(vol.Coerce(float),vol.Range(min=100,max=9300)),vol.Optional('duration_minutes'):vol.All(vol.Coerce(float),vol.Range(min=1,max=60))}),
    'bias_probe':vol.Schema({}), 'stop':vol.Schema({}), 'zero_import_target':vol.Schema({}), 'automatic':vol.Schema({vol.Required('enabled'):bool}),'commission_battery':vol.Schema({vol.Optional('minimum_soc',default=90):vol.In([60,90]),vol.Optional('power_w',default=500):vol.In([500,2000])}),'commission_window':vol.Schema({vol.Optional('solar_sell',default=False):bool,vol.Optional('selling_first',default=False):bool})}
   if body['action'] not in schemas:return None
   body['data']=schemas[body['action']](body['data']);return body
  except (ValueError,TypeError,vol.Invalid):return None
 async def process_command():
  if command_lock.locked():return
  async with command_lock:
   body=await hass.async_add_executor_job(read_command)
   if not body:return
   protective=body['action']=='stop' or body['action']=='automatic' and not body['data']['enabled']
   try:
    if not await hass.async_add_executor_job(journal.claim_command,body):return
   except Exception:
    if protective:await stop_sale()
    raise
   receipt={'id':body['id'],'issued_at':body['issued_at'],'action':body['action'],'status':'claimed'}
   # A persisted claim is consumed even if journaling or the action later fails.
   previous=prefs.get('command');prefs['command']=receipt
   try:await persist_settings()
   except Exception:
    if previous is None:prefs.pop('command',None)
    else:prefs['command']=previous
    if protective:await stop_sale()
    raise
   try:
    await event('command_claimed',receipt)
    if time.time()>body['expires_at']:raise ValueError('Povel před provedením vypršel.')
    if body['action']=='start':await start_sale(body['data'],body['expires_at'])
    elif body['action']=='bias_probe':await bias_probe(body['expires_at'])
    elif body['action']=='commission_battery':await commission_battery(body['expires_at'],body['data']['minimum_soc'],body['data']['power_w'])
    elif body['action']=='zero_import_target':await zero_import_target(body['expires_at'])
    elif body['action']=='commission_window':await commission_window(body['expires_at'],body['data']['solar_sell'],body['data']['selling_first'])
    elif body['action']=='stop':await stop_sale()
    elif body['data']['enabled']:await configure({'automatic':True,'auto_verification_enabled':False,'inhibited':False,'commission_cancelled':False,'commission_attempted':False if not prefs['pv_verified'] else True},body['expires_at'])
    else:await stop_sale()
    receipt={**receipt,'status':'confirmed'}
   except Exception as exc:
    if protective:await stop_sale()
    receipt={**receipt,'status':'failed','error':str(exc)}
   prefs['command']=receipt;await persist_settings();await event('command_result',receipt)
 def verification_state():
  kind=('native_window' if window.active else 'battery' if battery.active else 'stopping' if c.active and c.record.get('phase')=='stopping' else c.record.get('mode') if c.active else None)
  pending=(bool(c.last_stop and c.last_stop.get('id')!=prefs.get('handled_stop_id')) or bool(battery.last_stop and battery.last_stop.get('id')!=prefs.get('handled_battery_stop_id')))
  pvstate=hass.states.get('sensor.inverter_pv_power');pvstamp=(getattr(pvstate,'last_reported',None) or pvstate.last_updated).timestamp() if pvstate else None
  span=max(0,pvstamp-low_pv_since) if pvstamp is not None and low_pv_since is not None else 0
  return {'pv_low_seconds':span,'ready':ready,'healthy':healthy(),'active_kind':kind,'pending_stop':pending,'charging':charge_controller.active,'soc':fresh_number('sensor.inverter_battery'),'pv_w':fresh_number('sensor.inverter_pv_power'),'capacity_kwh':capacity()['capacity_kwh'],'net_price':(current_price() or {}).get('net')}
 def autonomous_state():
  a=dict(prefs.get('auto_verification') or {})
  if prefs.get('verification_resume_auto'):return {**a,'state':'running' if active() else 'recovering','reason':a.get('reason','HA ověřuje bezpečné obnovení po restartu.')}
  if not prefs.get('auto_verification_enabled'):return {'state':'disabled','reason':'Automatické testy jsou vypnuté. HA řídí běžný provoz podle dostupných ověření.'}
  if prefs.get('inhibited'):return {**a,'state':'failed','reason':c.error or battery.error or 'Automatiku pozastavila ochrana.'}
  if not prefs.get('automatic'):return {**a,'state':'off','reason':'Automatika je vypnutá.'}
  if prefs.get('bias_verified') and prefs.get('battery_verified'):return {**a,'state':'verified','reason':'Ověření dokončena; provoz řídí HA.'}
  return {**a,**verification_candidate(prefs,verification_state(),quotes(),time.time())}
 async def autonomous_verify():
  nonlocal low_pv_since
  async with lock:
   if prefs.get('verification_resume_auto') and not active() and not verification_state()['pending_stop']:
    if not prefs.get('requested_automatic'):
     prefs.update(automatic=False,verification_resume_auto=False);await persist_settings();return False
    if not ready or not healthy():return False
    try:
     clock_idle_profile((await native_test_read())['registers'])
     grid=fresh_number('sensor.inverter_grid_power')
     if grid is None or grid < -100:raise ValueError('Obnova čeká na potvrzené ukončení přetoku.')
    except Exception as exc:
     prefs.update(automatic=False,inhibited=True,verification_resume_auto=False)
     prefs['auto_verification']={**(prefs.get('auto_verification') or {}),'state':'failed','reason':'Obnovu po restartu nelze potvrdit: '+str(exc)}
     await persist_settings();await event('autonomous_resume_failed',dict(prefs['auto_verification']));return False
    prefs.update(automatic=True,inhibited=False,verification_resume_auto=False)
    prefs['auto_verification']={**(prefs.get('auto_verification') or {}),'state':'waiting','not_before':time.time()+1800,'reason':'Domácí režim po restartu ověřen; nedokončený test se nepovažuje za úspěšný.'}
    await persist_settings();await event('autonomous_resume_recovered',dict(prefs['auto_verification']));return True
   if not prefs.get('auto_verification_enabled'):return False
   pv=fresh_number('sensor.inverter_pv_power');pvstate=hass.states.get('sensor.inverter_pv_power')
   if healthy() and pv is not None and pv<=1700:
    stamp=(getattr(pvstate,'last_reported',None) or pvstate.last_updated).timestamp()
    if low_pv_since is None:low_pv_since=stamp
   else:low_pv_since=None
   choice=verification_candidate(prefs,verification_state(),quotes(),time.time())
   if not choice['due']:return False
   if c.active:
    await c.stop('price');await handle_stop()
    if active():return True
    choice=verification_candidate(prefs,verification_state(),quotes(),time.time())
    if not choice['due']:return True
   prefs['auto_verification']={'kind':choice['kind'],'day':choice['day'],'attempts':choice['attempts']+1,'last_attempt':time.time(),'state':'preparing','reason':choice['reason']}
   prefs['verification_resume_auto']=True
   try:
    await persist_settings();await event('autonomous_verification_started',dict(prefs['auto_verification']))
    if choice['kind']=='bias':await _bias_probe_locked(autonomous=True)
    else:await _commission_battery_locked(minimum_soc=60,power_w=2000,autonomous=True)
   except Exception as exc:
    prefs.update(automatic=False,inhibited=True,verification_resume_auto=False)
    prefs['auto_verification'].update(state='failed',reason='Automatické ověření se zastavilo: '+type(exc).__name__+': '+str(exc))
    try:await persist_settings();await event('autonomous_verification_failed',dict(prefs['auto_verification']))
    except Exception:pass
   return True
 async def recover_measurement():
  nonlocal measurement_healthy_since,last_reason
  recovery=prefs.get('measurement_recovery') or {}
  if not recovery.get('pending'):measurement_healthy_since=None;return
  if recovery.get('source')=='battery':
   proof=prefs.get('battery_sale_proof') or {}
   if proof.get('id')!=recovery.get('stop_id') or prefs.get('handled_battery_stop_id')!=proof.get('id') or not recoverable_battery_stop(proof):
    measurement_healthy_since=None;return
  if not prefs.get('requested_automatic'):
   prefs['measurement_recovery']={};measurement_healthy_since=None;await persist_settings();return
  if not ready or active() or not healthy() or not current_price():measurement_healthy_since=None;return
  if measurement_healthy_since is None:measurement_healthy_since=time.time();return
  if time.time()-measurement_healthy_since<recovery.get('stable_seconds',10):return
  async with lock:
   if not prefs.get('requested_automatic') or active() or not healthy():return
   try:
    if not await ensure_house_profile(recovering=True):return
    clock_idle_profile((await native_test_read())['registers'])
    grid=fresh_number('sensor.inverter_grid_power')
    if grid is None or grid < -100:raise ValueError('Čekám na potvrzení ukončené dodávky.')
   except Exception as exc:
    last_reason='Obnovení automatiky čeká: '+str(exc);return
   prefs.update(automatic=True,inhibited=False,verification_resume_auto=False,measurement_recovery={'pending':False,'stop_id':recovery.get('stop_id'),'restored_at':time.time()})
   c.error='';measurement_healthy_since=None
   await persist_settings();await event('measurement_recovery_confirmed',dict(prefs['measurement_recovery']))
 async def tick(_now=None):
  nonlocal ready,last_reason,last_decision,runtime_error,last_native_read,last_power_adjust
  if lock.locked() or c.lock.locked():return
  if ready:
   try:await process_command()
   except Exception as exc:runtime_error='Povel nelze zpracovat: '+str(exc)
   try:
    await recover_measurement()
    if await autonomous_verify():return
   except Exception as exc:
    runtime_error='Automatické ověření: '+type(exc).__name__+': '+str(exc)
    prefs.update(automatic=False,inhibited=True,verification_resume_auto=False)
    prefs['auto_verification']={**(prefs.get('auto_verification') or {}),'state':'failed','reason':runtime_error}
    try:await stop_sale(requested_off=False)
    except Exception:pass
  async with lock:
   try:
    if not ready:
     if window.active:await window.stop('recovery')
     if battery.active:await battery.stop('recovery')
     if c.active:await c.stop('recovery');await handle_stop()
     await handle_native_stops()
     ready=not active()
     if ready:await read_native_program()
    if healthy() and not active() and time.time()-last_native_read>=60:
     last_native_read=time.time();await read_native_program()
    await handle_native_stops()
    if window.active:
     await window.tick();await handle_native_stops();last_reason=f"Ověřuji nativní časové ukončení baterie · 500 W / 5 minut / rezerva {window.record.get('minimum_soc',95)} %.";return
    if battery.active:
     if battery.record.get('purpose')=='automatic' and fresh_number('sensor.inverter_battery') is not None and fresh_number('sensor.inverter_battery')<=battery.record.get('minimum_soc',policy()['sale_soc']):await battery.stop('reserve')
     await battery.tick();await handle_native_stops()
     if battery.active:
      last_reason='Bateriový segment · '+battery.record.get('phase','')+f" · rezerva {battery.record.get('minimum_soc',60)} %."
      if battery.record.get('purpose') not in ('commission','automatic') and battery.record.get('phase')!='stopping' and time.time()<battery.record['end']:
       block=prefs.get('selected_block') if battery.record.get('purpose')=='automatic' else {'start':battery.record['start'],'end':battery.record['end']}
       if not isinstance(block,dict):await battery.stop('selected_block_missing')
       else:
        sizing=battery_size(block,number(battery.record.get('maximum_power_w')) or battery.record['power_w'])
        if sizing['power_w']<100:await battery.stop('budget')
        elif time.time()-last_power_adjust>=5 and abs(sizing['power_w']-battery.record['power_w'])>=100:
         await battery.adjust_power(sizing['power_w']);last_power_adjust=time.time()
      await handle_native_stops()
     return
    was_active=c.active
    if c.active:
     await refresh_sale_controls()
     if prefs.get('automatic') and not prefs.get('inhibited'):await c.renew_automatic_pv()
     await c.tick();await handle_stop()
     if c.active and c.record.get('purpose')=='automatic':
      block=await select_block(quotes())
      choice=sale_decision(block,current_price(),fresh_number('sensor.inverter_battery'),fresh_number('sensor.inverter_pv_power'))
      if choice['mode']=='battery' and c.record.get('mode')!='battery' or choice['mode']=='pv' and c.record.get('mode')=='bias':
       await c.stop('price');await handle_stop()
    if was_active:return
    if not active() and ready and healthy():
     if prefs.get('automatic') and not prefs.get('inhibited') and not await ensure_house_profile():
      last_reason='Čekám na aktualizaci potvrzené domácí rezervy v HA.';return
     p=current_price();soc=fresh_number('sensor.inverter_battery');pv=fresh_number('sensor.inverter_pv_power')
     future=quotes();block=await select_block(future)
     decision=sale_decision(block,p,soc,pv)
     signature=(decision['mode'],decision['reason'],p['start'] if p else None,prefs['automatic'],block['start'] if block else None)
     if signature!=last_decision:
      await event('decision',{'decision':decision,'price':p,'automatic':prefs['automatic'],'selected_block':block,'policy':'simple_daily_block','forecast_is_informational':True});last_decision=signature
     last_reason=decision['reason']
     if commission_requested and not prefs.get('commission_cancelled') and not prefs.get('inhibited') and not prefs.get('commission_attempted') and p and p['net']>0 and soc is not None and soc>=97 and daylight_pv(pv) and time.time()>=float(prefs.get('cooldown_until',0)):
      prefs['commission_attempted']=True;await persist_settings()
      await verify_baseline()
      await c.start('pv',500,3,minimum_soc=60,purpose='commission',promote_auto=True)
      last_reason='První ověřovací prodej přebytků · nejvýše 500 W / 3 minuty.'
     elif prefs['automatic'] and not prefs.get('inhibited'):
      if decision['mode']=='battery' and decision['power_w']>=100:
       await verify_baseline()
       operating_end=automatic_window_end(block)
       if operating_end is not None:
        await battery.start(cap(),min(60,(operating_end-time.time())/60),policy()['sale_soc'],quotes(),purpose='automatic',window_end=operating_end,maximum_power_w=cap())
        last_reason='Bateriový prodej připraven přes HA; čekám na potvrzení dodávky.'
       elif operating_end is None:last_reason='Před půlnocí již nelze bezpečně dokončit další bateriový segment; automatika čeká.'
      elif decision['mode']=='bias' and prefs.get('bias_verified'):
       await verify_baseline();await c.start('bias',policy()['bias_w'],60,minimum_soc=home_floor(),purpose='automatic')
      elif decision['mode']=='pv' and prefs['pv_verified']:
       await verify_baseline();await c.start('pv',cap(),15,minimum_soc=policy()['sale_soc'],purpose='automatic')
   except Exception as exc:
    runtime_error=str(exc) or type(exc).__name__
    prefs['last_controller_error']={'at':time.time(),'error':runtime_error,'sale_id':c.record.get('id') or battery.record.get('id')}
    try:await event('controller_error',{'error':runtime_error})
    except Exception:pass
    prefs['automatic']=False;prefs['inhibited']=True
    if window.active:await window.stop('error')
    if battery.active:await battery.stop('error');await handle_native_stops()
    if c.active:await c.stop('error');await handle_stop()
   finally:
    await flush_history()
    await report()
 async def service_resume(call):
  nonlocal runtime_error,last_reason
  async with lock:
   proof=prefs.get('last_sale_stop') or {}
   if not prefs.get('requested_automatic') or prefs.get('automatic') or not prefs.get('inhibited') or not ready or active() or not healthy():return
   if call.data['stop_id']!=proof.get('id') or prefs.get('handled_stop_id')!=proof.get('id') or not recoverable_stop(proof):return
   registers=(await native_test_read())['registers'];clock_idle_profile(registers)
   if any(registers.get(166+i)!=home_floor() for i in range(6)):return
   grid=fresh_number('sensor.inverter_grid_power')
   if not prefs.get('requested_automatic') or active() or not healthy() or grid is None or grid < -100:return
   await verify_baseline()
   # Same application lock protects this check and the operational enable.
   if not prefs.get('requested_automatic'):return
   c.error='';runtime_error=''
   await _configure_locked({'automatic':True,'requested_automatic':True,'inhibited':False,'auto_verification_enabled':False,'verification_resume_auto':False})
   last_reason='HA obnovilo automatický provoz po potvrzeném ukončení přechodné chyby.'
   await event('conditional_recovery_confirmed',{'stop_id':proof['id']})
  await report()
 async def service_start(call):await start_sale(dict(call.data));await report()
 async def service_stop(call):await stop_sale();await report()
 async def service_auto(call):
  if call.data['enabled']:await configure({'automatic':True,'auto_verification_enabled':False,'inhibited':False,'commission_cancelled':False,'commission_attempted':False if not prefs['pv_verified'] else True})
  else:await stop_sale()
  await report()
 async_register_admin_service(hass,DOMAIN,'configure_policy',service_policy,vol.Schema({vol.Required('changes'):dict,vol.Required('expected_revision'):str}))
 async_register_admin_service(hass,DOMAIN,'resume_confirmed_sale',service_resume,vol.Schema({vol.Required('stop_id'):str}))
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
 hass.data[KEY]={'controller':c,'window':window,'battery_controller':battery,'battery_sale':battery,'controllers':[c,battery,window],
  'busy':lambda:lock.locked(),'clock_sync_active':False,'settings':prefs,'configure':configure,'configure_policy':configure_policy,'report':report,'journal':journal,'start':start_sale,'stop':stop_sale,'bias_probe':bias_probe,'commission_battery':commission_battery,'zero_import_target':zero_import_target}
 for platform in ('number','select','switch'):hass.async_create_task(discovery.async_load_platform(hass,platform,DOMAIN,{},config))
 async_track_time_interval(hass,tick,timedelta(seconds=5))
 async_track_time_interval(hass,report,timedelta(seconds=5))
 try:planning=await async_setup_planning(hass)
 except Exception:planning=None
 hass.data[KEY]['planning']=planning
 if hass.is_running:hass.async_create_task(tick())
 else:hass.bus.async_listen_once('homeassistant_started',tick)
 await report()
 return c

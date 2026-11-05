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
from .sales import decide,price_at,market_rows,number,after_stop
from .sale_controller import SaleController
from .journal import Journal
from .native_window import NativeWindow,WRITABLE
from .planning_setup import async_setup_planning
from .simple_sales import choose_daily_block,size_sale
from .battery_native import BatterySaleController,WRITABLE as BATTERY_WRITABLE
from .native_clock import sync_native_clock
from .native_plan import native_clock_acceptable
from .native_zero_target import set_zero_target

DOMAIN='jarvis_spot_control'
KEY=DOMAIN+'_sales'
VERSION='0.6.3'
AUTO_EXPORT_LIMIT=9300

async def async_setup_sales(hass,config,charge_controller):
 store=Store(hass,1,KEY);saved=await store.async_load() or {}
 prefs={'automatic':False,'power_w':500,'minutes':3,'source':'pv','pv_verified':False,'battery_verified':False,**saved.get('settings',{})}
 journal=await hass.async_add_executor_job(Journal,Path(hass.config.path('.storage','jarvis_energy_sales.sqlite')))
 lock=asyncio.Lock();command_lock=asyncio.Lock();history_lock=asyncio.Lock();report_lock=asyncio.Lock();ready=False;last_reason='Připravuji měření.';last_decision=None;last_report=0;native_program={};window=None;battery=None;last_native_read=0;planning=None;last_power_adjust=0
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
 def fresh_number(entity_id):
  state=hass.states.get(entity_id)
  if state is None:return None
  stamp=(getattr(state,'last_reported',None) or state.last_updated).timestamp()
  return number(state.state) if 0<=time.time()-stamp<30 else None
 def quotes():
  entity=hass.states.get('sensor.jarvis_spot_ote')
  if entity is None or entity.state in ('unknown','unavailable'):return []
  try:
   issued=datetime.fromisoformat(entity.attributes['fetched_at'])
   if issued.tzinfo is None or not 0<=time.time()-issued.timestamp()<=2100:return []
   return market_rows(entity.attributes.get('rows',[]),entity.attributes.get('rate'))
  except (KeyError,TypeError,ValueError,OverflowError):return []
 async def select_block(rows):
  now=time.time();selected=prefs.get('selected_block')
  if isinstance(selected,dict):
   start=number(selected.get('start'));end=number(selected.get('end'))
   if start is not None and end is not None and end-start==7200 and now<end:
    valid=True
    for offset in range(8):
     matches=[row for row in rows if row['start']==start+offset*900]
     if len(matches)!=1 or matches[0]['net']<=0:valid=False;break
    if valid:return selected
  local=datetime.fromtimestamp(now,ZoneInfo('Europe/Prague'))
  selected=choose_daily_block(rows,local.date().isoformat(),now)
  if selected is None:selected=choose_daily_block(rows,(local.date()+timedelta(days=1)).isoformat(),now)
  if selected!=prefs.get('selected_block'):
   prefs['selected_block']=selected;await persist_settings()
   await event('daily_block_selected',{'selected_block':selected,'policy':'simple_120_minutes','minimum_soc':60})
  return selected
 def battery_size(block,maximum_power_w=AUTO_EXPORT_LIMIT):
  return size_sale(fresh_number('sensor.inverter_battery'),23.5,block['start'],block['end'],time.time(),fresh_number('sensor.inverter_load_power'),max_export_w=min(AUTO_EXPORT_LIMIT,maximum_power_w),minimum_soc=60)
 def automatic_window_end(block):
  now=time.time();local=datetime.fromtimestamp(now,ZoneInfo('Europe/Prague'))
  cutoff=local.replace(hour=23,minute=40,second=0,microsecond=0).timestamp()
  end=min(block['end'],cutoff)
  minute=((local.hour*60+local.minute+5)//5)*5
  native_start=(local.replace(hour=0,minute=0,second=0,microsecond=0)+timedelta(minutes=minute)).timestamp()
  return end if end-now>=360 and native_start+300<=end else None
 def daylight_pv(pv):
  sun=hass.states.get('sun.sun')
  return pv is not None and pv>30 or sun is not None and sun.state=='above_horizon'
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
 async def native_readback(entity,value,required=True):
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
  await event('native_register_readback',{'entity':entity,'address':address,'expected':expected,'actual':actual,'sale_id':c.record.get('id')})
  if entity=='number.inverter_zero_export_power':prefs['native_grid_target_w']=(actual-offset)*scale if actual is not None else None
  if required and actual!=expected:raise RuntimeError(f'Měnič nepotvrdil registr {address}: požadováno {expected}, naměřeno {actual}.')
 async def verify_baseline():
  await native_readback('select.inverter_work_mode','Zero Export To CT')
  await native_readback('switch.inverter_export_surplus','off')
  await native_readback('number.inverter_zero_export_power',0,required=False)
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
   if same and reported is not None and reported>issued:
    await native_readback(entity,value);return
  raise RuntimeError('Měnič nepotvrdil '+entity)
 c=SaleController(read,write,save_record,event,healthy=healthy,price=lambda:(current_price() or {}).get('net'),saved=saved.get('transaction'),reported=reported)
 def native_device():
  entries=hass.config_entries.async_entries('solarman')
  if len(entries)!=1:raise ValueError('Inverter interface is ambiguous')
  runtime=getattr(entries[0],'runtime_data',None)
  if runtime is None:raise ValueError('Inverter is not ready')
  return runtime.device
 async def native_test_read():
  device=native_device();registers={}
  async with asyncio.timeout(25):
   for address,count in ((0,1),(98,14),(130,1),(142,36),(212,8),(62,3)):
    raw=await device.execute(3,address,count=count)
    if not isinstance(raw,list) or len(raw)!=count or any(type(v) is not int for v in raw):raise ValueError('Incomplete native register snapshot')
    registers.update({address+i:v for i,v in enumerate(raw)})
  values=[registers[i] for i in (62,63,64)]
  date=datetime(2000+(values[0]>>8),values[0]&255,values[1]>>8,values[1]&255,values[2]>>8,values[2]&255,tzinfo=ZoneInfo('Europe/Prague'))
  return {'clock':date,'registers':registers}
 async def native_test_write(address,value):
  if address not in WRITABLE|BATTERY_WRITABLE:raise ValueError('Native register is outside commissioning scope')
  device=native_device()
  if address==109 or 166<=address<=171:
   entity='number.inverter_battery_max_discharging_current' if address==109 else f'number.inverter_program_{address-165}_soc'
   await write(entity,value)
   bulk_start,count=(98,14) if address==109 else (166,6)
   async with asyncio.timeout(20):
    await asyncio.sleep(2)
    raw=await device.execute(3,bulk_start,count=count)
   actual=raw[address-bulk_start] if isinstance(raw,list) and len(raw)==count and all(type(v) is int for v in raw) else None
   await event('native_bulk_readback',{'entity':entity,'address':address,'bulk_start':bulk_start,'count':count,'expected':value,'actual':actual})
   if actual!=value:raise ValueError(f'Native bulk register {address} did not confirm {value}; actual={actual}')
   return
  async with asyncio.timeout(20):
   await device.execute(16,address,data=[value])
   await asyncio.sleep(1) # Give the inverter configuration write time to settle.
   actual=await device.execute(3,address,count=1)
  if actual!=[value]:raise ValueError(f'Native commissioning register {address} did not confirm {value}')
 async def save_window(record):await store.async_save({'settings':dict(prefs),'transaction':c.record,'native_window':record,'battery_sale':battery.record if battery else saved.get('battery_sale',{})})
 async def save_battery(record):await store.async_save({'settings':dict(prefs),'transaction':c.record,'native_window':window.record if window else saved.get('native_window',{}),'battery_sale':record})
 def window_telemetry():
  states=read()
  voltage=hass.states.get('sensor.inverter_battery_voltage');current=hass.states.get('sensor.inverter_battery_current')
  stamp=lambda state:(getattr(state,'last_reported',None) or state.last_updated).timestamp() if state else None
  return {'soc':number(states.get('sensor.inverter_battery')),'grid_w':number(states.get('sensor.inverter_grid_power')),'battery_w':number(states.get('sensor.inverter_battery_power')),'pv_w':number(states.get('sensor.inverter_pv_power')),'healthy':healthy(),'reported_at':reported(),'net_price':(current_price() or {}).get('net'),
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
   if not admission():raise ValueError('Nulový cíl vyžaduje čerstvá měření a neaktivní řízení.')
   result=await set_zero_target(native_device(),admission,event)
   prefs['zero_target_proof']=result;prefs['native_grid_target_w']=result.get('actual_w')
   await persist_settings();await event('native_zero_target_result',result)
   if result.get('verified') is not True:raise ValueError('Měnič nativně nepotvrdil nulový cíl odběru: '+str(result.get('actual_w'))+' W.')
 async def commission_window(valid_until=None,solar_sell=False,selling_first=False):
  async with lock:
   if not ready or active() or charge_controller.active:raise ValueError('Nejprve ukonči současný test nebo prodej.')
   prefs.update(automatic=False,commission_cancelled=True,inhibited=False);await persist_settings()
   await ensure_native_clock()
   await window.start(valid_until,solar_sell=solar_sell,selling_first=selling_first)
 async def commission_battery(valid_until=None):
  async with lock:
   if valid_until is not None and time.time()>valid_until:raise ValueError('Povel před provedením vypršel.')
   if not ready or active() or charge_controller.active or not healthy():raise ValueError('Nejprve ukonči současný test nebo prodej a ověř měření.')
   prefs.update(automatic=False,commission_cancelled=True,inhibited=False);await persist_settings()
   await verify_baseline();await ensure_native_clock()
   await battery.start(500,5,90,quotes(),valid_until=valid_until,purpose='commission',maximum_power_w=500)
 async def handle_native_stops():
  proof=getattr(window,'last_stop',None)
  if proof and proof.get('stop_verified') is True and prefs.get('native_window_proof',{}).get('id')!=proof.get('id'):
   prefs['native_window_proof']=dict(proof);await persist_settings()
  proof=battery.last_stop
  if battery.active or not proof or prefs.get('handled_battery_stop_id')==proof.get('id'):return
  prefs['handled_battery_stop_id']=proof.get('id');prefs['battery_sale_proof']=dict(proof)
  accepted=(all(proof.get(key) is True for key in ('observed','native_expiry_observed','stop_verified'))
   and proof.get('reason')=='deadline' and proof.get('purpose')=='commission' and proof.get('power_w')==500
   and proof.get('minimum_soc')==90 and proof.get('phase')=='complete' and not proof.get('conflicts'))
  if proof.get('purpose')=='commission':
   prefs['automatic']=False
   if accepted:prefs['battery_verified']=True;await event('battery_native_acceptance',dict(proof))
  normal=proof.get('reason') in ('deadline','manual','price','reserve','budget','energy_budget') or proof.get('reason')=='recovery' and proof.get('purpose')=='automatic' and proof.get('stop_verified') is True
  if proof.get('conflicts'):normal=False
  if not normal:prefs.update(automatic=False,inhibited=True)
  await persist_settings()
 async def handle_stop():
  if c.active and c.record.get('inhibited') and (prefs.get('automatic') or not prefs.get('inhibited')):
   prefs.update(automatic=False,inhibited=True);await persist_settings()
  if c.active or not c.last_stop or prefs.get('handled_stop_id')==c.last_stop['id']:return
  result=after_stop(prefs,c.last_stop);prefs.clear();prefs.update(result);await persist_settings()
 async def configure(changes,valid_until=None):
  async with lock:
   if valid_until is not None and time.time()>valid_until:raise ValueError('Povel před provedením vypršel.')
   before=dict(prefs);prefs.update(changes)
   try:await persist_settings();await event('settings_changed',{'before':before,'after':dict(prefs)})
   except Exception:prefs.clear();prefs.update(before);raise
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
    sizing=size_sale(fresh_number('sensor.inverter_battery'),23.5,time.time(),end,time.time(),fresh_number('sensor.inverter_load_power'),max_export_w=min(AUTO_EXPORT_LIMIT,float(power)),minimum_soc=60)
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
 async def stop_sale():
  changes={'automatic':False,'commission_cancelled':True,'commission_attempted':True}
  try:await configure(changes)
  except Exception:prefs.update(changes)
  async with lock:
   if window.active:await window.stop('manual')
   if battery.active:await battery.stop('manual')
   await c.stop('manual');await handle_stop()
   await handle_native_stops()
  if active():raise ValueError(c.error or window.error or battery.error or 'Čekám na potvrzení ukončení.')
 def snapshot():
  p=current_price();entity=hass.states.get('sensor.inverter_battery')
  return {'version':VERSION,'ready':ready,'active':active(),'observed':bool(window.record.get('observed')) if window.active else battery.observed if battery.active else c.observed,'phase':'native_test' if window.active else battery.record.get('phase','idle') if battery.active else c.record.get('phase','idle'),'native_program':native_program,'native_test':{k:v for k,v in window.record.items() if k!='before'},'native_test_error':window.error,
   'battery_sale':{k:v for k,v in battery.record.items() if k not in ('before','expected','pending')},'battery_sale_error':battery.error,'native_start':battery.record.get('start'),'selected_block':prefs.get('selected_block'),'sale_policy':'simple_daily_block','sale_floor_soc':60,
   'settings':dict(prefs),'reason':('Ověřovací test baterie · '+window.record.get('phase','')+f" · 500 W / 5 minut / rezerva {window.record.get('minimum_soc',95)} %." if window.active else 'Automatika pozastavena po zásahu ochrany. '+(c.error or battery.error or 'Čeká na nový ověřovací test.') if prefs.get('inhibited') else last_reason),'error':window.error if window.active else battery.error if battery.active else c.error or runtime_error,'price':p,
   'mode':'battery_commission' if window.active else 'battery' if battery.active else c.record.get('mode'),'power_w':500 if window.active else battery.record.get('power_w') if battery.active else c.record.get('power_w'),'deadline':window.record.get('end') if window.active else battery.record.get('end') if battery.active else c.record.get('deadline'),
   'grid_target_w':0,'native_grid_target_w':prefs.get('native_grid_target_w'),'grid_target_confirmed':prefs.get('native_grid_target_w')==0,'grid_import_policy':'Cíl běžného odběru 0 W; síť pro nedostatek vlastní energie nebo výslovné nabití.','automatic_limit_w':AUTO_EXPORT_LIMIT,'healthy':healthy(),'battery_soc':number(entity.state) if entity else None,
   'history_error':archive_error,'planning':home_plan(),'notice':'Časové ukončení vyžaduje běžící řízení; při jeho výpadku může pokračovat PV export pod nativním limitem.'}
 def write_report(body):
  path=Path(hass.config.path('jarvis_workspace','sales-runtime.json'));path.parent.mkdir(exist_ok=True)
  temp=path.with_suffix('.tmp');temp.write_text(json.dumps(body,ensure_ascii=False,allow_nan=False));temp.replace(path)
 async def report(_now=None):
  nonlocal last_report
  if report_lock.locked():return
  async with report_lock:
   body=snapshot();hass.states.async_set('sensor.jarvis_energy_sales',body['phase'],{'friendly_name':'Prodej elektřiny',**body})
   states=read();source_ok=prefs['source']=='pv' or prefs['battery_verified']
   base_ok=states.get('select.inverter_work_mode')=='Zero Export To CT' and states.get('switch.inverter_export_surplus')=='off' and number(states.get('number.inverter_export_surplus_power')) is not None
   hass.states.async_set('binary_sensor.jarvis_sales_ready','on' if ready and not active() and healthy() and source_ok and base_ok and current_price() and current_price()['net']>0 else 'off',{'friendly_name':'Prodej připraven'})
   hass.bus.async_fire('jarvis_sales_settings')
   if time.time()-last_report>=10:
    telemetry={}
    for entity_id in ('sensor.inverter_pv_power','sensor.inverter_grid_power','sensor.inverter_battery','sensor.inverter_battery_power','sensor.inverter_battery_current','sensor.inverter_temperature','sensor.inverter_battery_temperature','sensor.inverter_total_energy_export','number.inverter_zero_export_power'):
     state=hass.states.get(entity_id)
     if state:telemetry[entity_id]={'state':state.state,'source_reported':(getattr(state,'last_reported',None) or state.last_updated).isoformat()}
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
    'stop':vol.Schema({}), 'zero_import_target':vol.Schema({}), 'automatic':vol.Schema({vol.Required('enabled'):bool}),'commission_battery':vol.Schema({}),'commission_window':vol.Schema({vol.Optional('solar_sell',default=False):bool,vol.Optional('selling_first',default=False):bool})}
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
    elif body['action']=='commission_battery':await commission_battery(body['expires_at'])
    elif body['action']=='zero_import_target':await zero_import_target(body['expires_at'])
    elif body['action']=='commission_window':await commission_window(body['expires_at'],body['data']['solar_sell'],body['data']['selling_first'])
    elif body['action']=='stop':await stop_sale()
    elif body['data']['enabled']:await configure({'automatic':True,'inhibited':False,'commission_cancelled':False,'commission_attempted':False if not prefs['pv_verified'] else True},body['expires_at'])
    else:await stop_sale()
    receipt={**receipt,'status':'confirmed'}
   except Exception as exc:
    if protective:await stop_sale()
    receipt={**receipt,'status':'failed','error':str(exc)}
   prefs['command']=receipt;await persist_settings();await event('command_result',receipt)
 async def tick(_now=None):
  nonlocal ready,last_reason,last_decision,runtime_error,last_native_read,last_power_adjust
  if lock.locked() or c.lock.locked():return
  if ready:
   try:await process_command()
   except Exception as exc:runtime_error='Povel nelze zpracovat: '+str(exc)
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
     await battery.tick();await handle_native_stops()
     if battery.active:
      last_reason='Bateriový segment · '+battery.record.get('phase','')+f" · rezerva {battery.record.get('minimum_soc',60)} %."
      if battery.record.get('purpose')!='commission' and battery.record.get('phase')!='stopping' and time.time()<battery.record['end']:
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
     await c.tick();await handle_stop()
     if c.active and c.record.get('purpose')=='automatic':
      block=await select_block(quotes()) if prefs.get('battery_verified') else None
      if block and block['start']-180<=time.time()<block['end'] and automatic_window_end(block) is not None:await c.stop('price');await handle_stop()
    if was_active:return
    if not active() and ready and healthy():
     p=current_price();soc=fresh_number('sensor.inverter_battery');pv=fresh_number('sensor.inverter_pv_power')
     future=quotes();block=await select_block(future)
     decision={'mode':'hold','power_w':0,'minimum_soc':60,'reason':'Čekám na vybraný cenový blok nebo skutečné přebytky panelů.'}
     if block:decision['reason']='Vybraný nejlepší dvouhodinový blok; bateriová rezerva60 %.'
     if block and block['start']-180<=time.time() and automatic_window_end(block) is None:
      decision['reason']='Dostupné okno již nestačí na bezpečný bateriový segment; automatika čeká.'
     if p and p['net']>0 and soc is not None:
      if prefs['battery_verified'] and block and block['start']-180<=time.time()<=block['end']-360 and automatic_window_end(block) is not None:
       decision={**battery_size(block),'mode':'battery','reason':'Vybraný cenový blok · výkon z aktuální energie nad60 %.'}
      elif soc>=98 and daylight_pv(pv) and time.time()>=float(prefs.get('cooldown_until',0)):
       decision={'mode':'pv','power_w':AUTO_EXPORT_LIMIT,'minimum_soc':60,'reason':'Baterie je téměř plná a panely vyrábějí · dostupné přebytky.'}
     signature=(decision['mode'],decision['reason'],p['start'] if p else None,prefs['automatic'],block['start'] if block else None)
     if signature!=last_decision:
      await event('decision',{'decision':decision,'price':p,'automatic':prefs['automatic'],'selected_block':block,'policy':'simple_daily_block','forecast_is_informational':True});last_decision=signature
     last_reason=decision['reason']
     if commission_requested and not prefs.get('commission_cancelled') and not prefs.get('inhibited') and not prefs.get('commission_attempted') and p and p['net']>0 and soc is not None and soc>=98 and daylight_pv(pv) and time.time()>=float(prefs.get('cooldown_until',0)):
      prefs['commission_attempted']=True;await persist_settings()
      await verify_baseline()
      await c.start('pv',500,3,minimum_soc=60,purpose='commission',promote_auto=True)
      last_reason='První ověřovací prodej přebytků · nejvýše 500 W / 3 minuty.'
     elif prefs['automatic'] and not prefs.get('inhibited'):
      if decision['mode']=='battery' and prefs['battery_verified'] and decision['power_w']>=100:
       await verify_baseline();await ensure_native_clock()
       sizing=battery_size(block)
       operating_end=automatic_window_end(block)
       if sizing['power_w']>=100 and operating_end is not None:
        await battery.start(sizing['power_w'],min(60,(operating_end-time.time())/60),60,quotes(),purpose='automatic',window_end=operating_end,maximum_power_w=AUTO_EXPORT_LIMIT)
        last_reason='Bateriový segment připraven; skutečný nativní začátek může následovat po začátku cenového bloku.'
       elif operating_end is None:last_reason='Před půlnocí již nelze bezpečně dokončit další bateriový segment; automatika čeká.'
      elif decision['mode']=='pv' and prefs['pv_verified']:
       await verify_baseline();await c.start('pv',AUTO_EXPORT_LIMIT,15,minimum_soc=60,purpose='automatic')
   except Exception as exc:
    runtime_error=str(exc)
    try:await event('controller_error',{'error':runtime_error})
    except Exception:pass
    prefs['automatic']=False;prefs['inhibited']=True
    if window.active:await window.stop('error')
    if battery.active:await battery.stop('error');await handle_native_stops()
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
 hass.data[KEY]={'controller':c,'window':window,'battery_controller':battery,'battery_sale':battery,'controllers':[c,battery,window],
  'busy':lambda:lock.locked(),'clock_sync_active':False,'settings':prefs,'configure':configure,'report':report,'journal':journal,'start':start_sale,'stop':stop_sale,'commission_battery':commission_battery,'zero_import_target':zero_import_target}
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

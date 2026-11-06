"""Execute real HA adapter with only HA infrastructure/device I/O substituted."""
import asyncio
import copy
from datetime import datetime,timezone
import importlib.util
import pathlib
import sys
import tempfile
import time
import types
import unittest
from unittest.mock import patch

class State:
 def __init__(self,entity,state,attributes=None):
  self.entity_id=entity;self.state=str(state);self.attributes=attributes or {}
  self.last_changed=self.last_updated=self.last_reported=datetime.now(timezone.utc)

class States:
 def __init__(self):self.items={}
 def get(self,key):return self.items.get(key)
 def async_all(self):return list(self.items.values())
 def async_set(self,key,value,attributes=None):
  old=self.items.get(key);new=State(key,value,attributes)
  if old and old.state==new.state:new.last_changed=old.last_changed
  self.items[key]=new

class Store:
 def __init__(self,*args):self.data=None
 async def async_load(self):return copy.deepcopy(self.data)
 async def async_save(self,data):self.data=copy.deepcopy(data)

class AdapterTests(unittest.IsolatedAsyncioTestCase):
 async def test_supervision_failure_remains_visible_without_breaking_control_report(self):
  data=await self.setup()
  with patch.object(self.module.Supervisor,'publish',side_effect=RuntimeError('monitor failed')):
   await data['report']()
  self.assertEqual(self.hass.states.get('sensor.jarvis_solar_dohled').state,'error')
  self.assertEqual(self.hass.states.get('sensor.jarvis_energy_sales').attributes['supervision']['error'],'RuntimeError')

 async def asyncSetUp(self):
  self.temp=tempfile.TemporaryDirectory();path=pathlib.Path(self.temp.name)
  (path/'.storage').mkdir()
  self.services={};self.writes=[];self.raw_writes=[];self.tasks=[];self.ticks=[]
  self.hass=types.SimpleNamespace(data={},is_running=False,states=States(),config=types.SimpleNamespace(path=lambda *parts:str(path.joinpath(*parts))))
  self.device_registers={143:9990,142:2,145:0,104:0,0:5,98:1,111:1,130:0,219:175,109:175,146:255};self.device_reads=[];self.device_reject=False
  for i in range(6):
   self.device_registers.update({148+i:i*400,154+i:12000,166+i:30,172+i:0})
  async def execute(code,address,count=1,**kwargs):
   self.device_reads.append((code,address,count))
   if code==16:
    self.raw_writes.append((address,list(kwargs['data'])))
    if not self.device_reject:
     for offset,value in enumerate(kwargs['data']):self.device_registers[address+offset]=value
    return list(kwargs['data'])
   if address==62:
    from zoneinfo import ZoneInfo
    d=datetime.now(ZoneInfo('Europe/Prague'))
    return [((d.year-2000)<<8)|d.month,(d.day<<8)|d.hour,(d.minute<<8)|d.second][:count]
   return [self.device_registers.get(a,0) for a in range(address,address+count)]
  device=types.SimpleNamespace(execute=execute)
  async def response(*args,**kwargs):return await device.execute(*args,**kwargs)
  device.modbus=types.SimpleNamespace(_semaphore=asyncio.Semaphore(1),get_response=response)
  entry=types.SimpleNamespace(runtime_data=types.SimpleNamespace(device=device))
  self.hass.config_entries=types.SimpleNamespace(async_entries=lambda domain:[entry] if domain=='solarman' else [])
  self.hass.http=types.SimpleNamespace(register_view=lambda view:None)
  self.hass.bus=types.SimpleNamespace(async_fire=lambda *a:None,async_listen_once=lambda *a:None)
  self.hass.async_create_task=lambda coro:self.tasks.append(asyncio.create_task(coro))
  async def executor(fn,*args):
   await asyncio.sleep(0);return fn(*args)
  self.hass.async_add_executor_job=executor
  async def call(domain,service,data,blocking=False):
   entity=data['entity_id'];value=data.get('value',data.get('option','on' if service=='turn_on' else 'off'))
   self.writes.append((entity,value));self.hass.states.async_set(entity,value)
   mapping={'number.inverter_export_surplus_power':143,'select.inverter_work_mode':142,'switch.inverter_export_surplus':145,'number.inverter_zero_export_power':104}
   mapping['number.inverter_battery_max_discharging_current']=109
   mapping.update({f'number.inverter_program_{i}_soc':165+i for i in range(1,7)})
   if entity in mapping and not self.device_reject:self.device_registers[mapping[entity]]=int({'Zero Export To CT':2,'Export First':0,'on':1,'off':0}.get(value,value))
   if entity=='number.inverter_export_surplus_power' and value==0:self.hass.states.async_set('sensor.inverter_grid_power',20)
   self.poll()
  self.hass.services=types.SimpleNamespace(async_call=call)
  async def load(*args):return None
  def register(hass,domain,name,handler,schema):self.services[name]=(handler,schema)
  class View:
   def json(self,data):return data
  modules={}
  for name in ['homeassistant','homeassistant.helpers','homeassistant.helpers.discovery','homeassistant.helpers.event','homeassistant.helpers.service','homeassistant.helpers.storage','homeassistant.components','homeassistant.components.http']:
   modules[name]=types.ModuleType(name)
  modules['homeassistant.helpers'].discovery=types.SimpleNamespace(async_load_platform=load)
  modules['homeassistant.helpers.event'].async_track_time_interval=lambda hass,callback,interval:self.ticks.append(callback)
  modules['homeassistant.helpers.service'].async_register_admin_service=register
  modules['homeassistant.helpers.storage'].Store=Store
  modules['homeassistant.components.http'].HomeAssistantView=View
  pkg=types.ModuleType('sales_adapter_test');pkg.__path__=[str(pathlib.Path('managed_sources/spot_control').resolve())];modules[pkg.__name__]=pkg
  self.patch=patch.dict(sys.modules,modules);self.patch.start()
  spec=importlib.util.spec_from_file_location('sales_adapter_test.sale_setup',pathlib.Path('managed_sources/spot_control/sale_setup.py'))
  self.module=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.module)
  self.real_sleep=asyncio.sleep
  async def quick_sleep(_delay):await self.real_sleep(0)
  self.sleep_patch=patch.object(self.module.asyncio,'sleep',quick_sleep);self.sleep_patch.start()
  values={'select.inverter_work_mode':'Zero Export To CT','switch.inverter_export_surplus':'off',
   'number.inverter_export_surplus_power':9990,'number.inverter_zero_export_power':0,'sensor.inverter_battery':99,'sensor.inverter_battery_power':-50,
   'sensor.inverter_grid_power':20,'sensor.inverter_pv_power':400,'sensor.inverter_battery_temperature':20,
   'sensor.inverter_device_state':'Normal','sensor.inverter_device_alarm':'OK','sensor.inverter_device_fault':'OK',
   'binary_sensor.inverter_battery_alarm':'off','binary_sensor.inverter_battery_fault':'off',
   'select.inverter_time_of_use':'Week','number.inverter_battery_max_charging_current':175,
   'number.inverter_battery_max_discharging_current':175,'sensor.inverter_battery_voltage':53.7,
   'sensor.inverter_battery_current':0,'sensor.inverter_load_power':450,'number.inverter_battery_capacity':460}
  for i in range(1,7):
   values.update({f'number.inverter_program_{i}_soc':30,f'number.inverter_program_{i}_power':12000,
    f'select.inverter_program_{i}_charging':'Disabled',f'time.inverter_program_{i}_time':f'{(i-1)*4:02}:00:00'})
  for key,value in values.items():self.hass.states.async_set(key,value)
  now=time.time();start=datetime.fromtimestamp(now-now%900,timezone.utc).isoformat()
  self.hass.states.async_set('sensor.jarvis_spot_ote',5,{'fetched_at':datetime.now(timezone.utc).isoformat(),'rate':25,'rows':[{'time':start,'eur_mwh':240}]})
 async def asyncTearDown(self):
  await asyncio.gather(*self.tasks)
  self.sleep_patch.stop();self.patch.stop();self.temp.cleanup()
 def poll(self):
  for key in ('sensor.inverter_grid_power','sensor.inverter_battery_power','sensor.inverter_pv_power'):
   s=self.hass.states.get(key)
   if s:self.hass.states.async_set(key,s.state,s.attributes)
 async def setup(self,commission=False):
  await self.module.async_setup_sales(self.hass,{'jarvis_spot_control':{'commission_pv_test':commission}},types.SimpleNamespace(active=False))
  return self.hass.data[self.module.KEY]
 async def service(self,name,data):
  handler,schema=self.services[name];await handler(types.SimpleNamespace(data=schema(data)))
 async def test_charge_refuses_every_active_sale_controller_and_reports_new_version(self):
  modules={}
  for name in ('homeassistant.const','homeassistant.util','homeassistant.util.dt','homeassistant.exceptions'):
   modules[name]=types.ModuleType(name)
  modules['homeassistant.const'].EVENT_HOMEASSISTANT_STARTED='started'
  modules['homeassistant.util.dt'].utcnow=lambda:datetime.now(timezone.utc)
  modules['homeassistant.util.dt'].now=lambda:datetime.now(timezone.utc)
  modules['homeassistant.util'].dt=modules['homeassistant.util.dt']
  modules['homeassistant.exceptions'].HomeAssistantError=RuntimeError
  sales=types.ModuleType('sales_adapter_test.sale_setup')
  async def setup_sales(hass,config,controller):
   hass.data['jarvis_spot_control_sales']={key:types.SimpleNamespace(active=False) for key in ('controller','window','battery_controller')}
  sales.async_setup_sales=setup_sales;modules[sales.__name__]=sales
  finance=types.ModuleType('sales_adapter_test.finance_setup')
  async def setup_finance(hass):pass
  finance.async_setup_finance=setup_finance;modules[finance.__name__]=finance
  with patch.dict(sys.modules,modules):
   spec=importlib.util.spec_from_file_location('sales_adapter_test.integration',pathlib.Path('managed_sources/spot_control/__init__.py'))
   spec.submodule_search_locations=None
   integration=importlib.util.module_from_spec(spec);spec.loader.exec_module(integration)
   await integration.async_setup(self.hass,{})
   charge=self.hass.data['jarvis_spot_control'];controllers=self.hass.data['jarvis_spot_control_sales']
   self.assertTrue(charge.healthy())
   for key in ('controller','window','battery_controller'):
    controllers[key].active=True
    self.assertFalse(charge.healthy(),key)
    controllers[key].active=False
   controllers['busy']=lambda:True
   self.assertFalse(charge.healthy(),'sale preparation owns control before active record exists')
   controllers['busy']=lambda:False
   controllers['clock_sync_active']=True
   self.assertFalse(charge.healthy(),'RTC synchronization owns control')
  self.assertEqual(self.hass.states.get('sensor.jarvis_spot_control').attributes['version'],'0.6.6')
 async def test_active_owner_conflict_latches_automatic_off_before_cleanup_finishes(self):
  from unittest.mock import AsyncMock
  data=await self.setup();await self.ticks[0]()
  data['settings']['automatic']=True
  c=data['controller'];c.record={'before':{'number.inverter_export_surplus_power':9300},'phase':'stopping','inhibited':True}
  c.tick=AsyncMock()
  await self.ticks[0]()
  self.assertTrue(c.active)
  self.assertFalse(data['settings']['automatic']);self.assertTrue(data['settings']['inhibited'])
 async def test_native_clock_is_read_after_slow_configuration_requests(self):
  from zoneinfo import ZoneInfo
  data=await self.setup();now=[time.time()]
  async def execute(code,address,count=1):
   if address==142:now[0]+=10
   if address==62:
    d=datetime.fromtimestamp(now[0],ZoneInfo('Europe/Prague'))
    return [((d.year-2000)<<8)|d.month,(d.day<<8)|d.hour,(d.minute<<8)|d.second]
   return [0]*count
  self.hass.config_entries.async_entries('solarman')[0].runtime_data.device.execute=execute
  result=await data['window'].native_read()
  self.assertLess(abs(result['clock'].timestamp()-now[0]),1)
 async def test_native_report_shows_actual_commissioning_soc_floor(self):
  data=await self.setup()
  data['window'].record={'before':{'109':175},'phase':'armed','minimum_soc':90,'end':time.time()+300}
  await data['report']()
  self.assertIn('90 %',self.hass.states.get('sensor.jarvis_energy_sales').attributes['reason'])
 async def test_missing_house_history_exposes_protected_planning_reserve(self):
  await self.setup();await self.ticks[0]()
  plan=self.hass.states.get('sensor.jarvis_energy_sales').attributes['planning']
  self.assertEqual(plan['required_soc'],100)
  self.assertEqual(plan['quality'],'insufficient')
 async def test_planning_storage_failure_cannot_break_native_control_or_report(self):
  with patch.object(self.module,'async_setup_planning',side_effect=RuntimeError('storage offline')):
   await self.setup()
  await self.ticks[0]()
  state=self.hass.states.get('sensor.jarvis_energy_sales')
  self.assertTrue(state.attributes['ready'])
  self.assertEqual(state.attributes['planning']['required_soc'],100)
 async def test_planning_snapshot_failure_remains_isolated_from_control(self):
  data=await self.setup()
  def broken():raise RuntimeError('invalid optional forecast')
  data['planning']['snapshot']=broken
  await self.ticks[0]()
  self.assertTrue(self.hass.states.get('sensor.jarvis_energy_sales').attributes['ready'])
  self.assertEqual(self.hass.states.get('sensor.jarvis_energy_sales').attributes['planning']['required_soc'],100)
 async def test_explicit_stop_cancels_pending_commissioning_before_first_tick(self):
  data=await self.setup(True);await self.service('stop_sale',{})
  await self.ticks[0]()
  self.assertFalse(data['settings']['automatic']);self.assertTrue(data['settings']['commission_cancelled'])
  self.assertEqual(self.writes,[])
 async def test_unverified_normal_start_cannot_exceed_commissioning_envelope(self):
  await self.setup();await self.ticks[0]()
  with self.assertRaises(ValueError):await self.service('start_sale',{'power_w':9300,'duration_minutes':60})
  self.assertEqual(self.writes,[])
 async def test_measured_manual_sale_then_stop_stays_off_and_is_recorded(self):
  data=await self.setup();await self.ticks[0]()
  await self.service('start_sale',{'power_w':500,'duration_minutes':3})
  self.hass.states.async_set('sensor.inverter_grid_power',-400);self.poll()
  await self.ticks[0]()
  self.assertTrue(data['controller'].observed)
  await self.service('stop_sale',{});await self.ticks[0]()
  self.assertFalse(data['controller'].active);self.assertFalse(data['settings']['automatic'])
  self.assertEqual(self.hass.states.get('switch.inverter_export_surplus').state,'off')
  kinds=[row['kind'] for row in data['journal'].recent(100)]
  self.assertIn('export_observed',kinds);self.assertIn('sale_stop',kinds)
 async def test_stale_alarm_prevents_start(self):
  await self.setup();await self.ticks[0]()
  self.hass.states.get('sensor.inverter_device_alarm').last_reported=datetime.fromtimestamp(time.time()-120,timezone.utc)
  with self.assertRaises(ValueError):await self.service('start_sale',{'power_w':500,'duration_minutes':3})
  self.assertEqual(self.writes,[])

 async def test_optimistic_ha_value_does_not_prove_device_accepted_cap(self):
  data=await self.setup();await self.ticks[0]();self.device_reject=True
  with self.assertRaisesRegex(RuntimeError,'registr'):
   await self.service('start_sale',{'power_w':500,'duration_minutes':3})
  self.assertNotIn(('switch.inverter_export_surplus','on'),self.writes)

 async def test_native_current_and_all_soc_writes_use_ha_then_single_and_bulk_readback(self):
  data=await self.setup()
  await data['window'].native_write(109,60)
  self.assertIn(('number.inverter_battery_max_discharging_current',60),self.writes)
  self.assertIn((3,109,1),self.device_reads);self.assertIn((3,98,14),self.device_reads)
  for i in range(1,7):
   await data['window'].native_write(165+i,90)
   self.assertIn((f'number.inverter_program_{i}_soc',90),self.writes)
   self.assertIn((3,165+i,1),self.device_reads)
  self.assertIn((3,166,6),self.device_reads)
  self.assertFalse(any(address==109 or 166<=address<=171 for address,_ in self.raw_writes))

 async def test_optimistic_ha_and_single_register_ack_cannot_replace_bulk_confirmation(self):
  data=await self.setup();device=self.hass.config_entries.async_entries('solarman')[0].runtime_data.device
  original=device.execute;self.device_reject=True
  async def optimistic(code,address,count=1,**kwargs):
   if code==3 and count==1 and address in (109,166):return [60 if address==109 else 90]
   return await original(code,address,count=count,**kwargs)
  device.execute=optimistic
  for address,value in ((109,60),(166,90)):
   with self.subTest(address=address),self.assertRaisesRegex(ValueError,'bulk|hromad'):
    await data['window'].native_write(address,value)

 async def test_single_register_confirmation_is_required_even_when_bulk_matches(self):
  data=await self.setup();self.device_reject=True
  device=self.hass.config_entries.async_entries('solarman')[0].runtime_data.device;original=device.execute
  async def optimistic_bulk(code,address,count=1,**kwargs):
   raw=await original(code,address,count=count,**kwargs)
   if code==3 and address==98 and count==14:raw[11]=60
   return raw
  device.execute=optimistic_bulk
  with self.assertRaisesRegex(ValueError,'109'):
   await data['window'].native_write(109,60)
  self.assertIn((3,98,14),self.device_reads)
  self.assertEqual(self.writes.count(('number.inverter_battery_max_discharging_current',60)),1)

 async def test_malformed_bulk_read_cannot_confirm_ha_current_write(self):
  data=await self.setup();device=self.hass.config_entries.async_entries('solarman')[0].runtime_data.device
  original=device.execute
  async def malformed(code,address,count=1,**kwargs):
   if code==3 and address==98 and count==14:return [0]*13
   return await original(code,address,count=count,**kwargs)
  device.execute=malformed
  with self.assertRaisesRegex(ValueError,'bulk'):
   await data['window'].native_write(109,60)
  self.assertEqual(self.device_registers[109],60)

 async def test_delayed_bulk_confirmation_is_reread_without_reissuing_ha_write(self):
  data=await self.setup();device=self.hass.config_entries.async_entries('solarman')[0].runtime_data.device
  original=device.execute;bulk_reads=[]
  async def delayed(code,address,count=1,**kwargs):
   raw=await original(code,address,count=count,**kwargs)
   if code==3 and address==98 and count==14:
    bulk_reads.append(True)
    if len(bulk_reads)==1:raw[11]=175
   return raw
  device.execute=delayed
  await data['window'].native_write(109,60)
  self.assertEqual(len(bulk_reads),2)
  self.assertEqual(self.writes.count(('number.inverter_battery_max_discharging_current',60)),1)
  self.assertEqual(self.raw_writes,[])

 async def test_initial_stale_single_read_can_be_confirmed_by_later_bulk_and_single(self):
  data=await self.setup();device=self.hass.config_entries.async_entries('solarman')[0].runtime_data.device
  original=device.execute;single_reads=[]
  async def delayed(code,address,count=1,**kwargs):
   if code==3 and address==166 and count==1:
    single_reads.append(True)
    if len(single_reads)==1:return [30]
   return await original(code,address,count=count,**kwargs)
  device.execute=delayed
  await data['window'].native_write(166,100)
  self.assertGreaterEqual(len(single_reads),2)
  self.assertEqual(self.writes.count(('number.inverter_program_1_soc',100)),1)

 async def test_pending_confirmation_cannot_outlive_native_arming_deadline(self):
  data=await self.setup();owner=data['battery_controller'];record={'id':'pending','before':{'109':175},'phase':'preparing',
   'arm_until':time.time()-1,'pending':{'109':{'value':60,'previous':[175]}},'conflicts':{}}
  owner.record=record
  with self.assertRaisesRegex(ValueError,'deadline|arming|vypršel'):
   await owner.native_write(109,60)
  self.assertLessEqual(self.writes.count(('number.inverter_battery_max_discharging_current',60)),1)

 async def test_cleanup_confirmation_uses_fresh_stop_not_expired_start_deadline(self):
  data=await self.setup();owner=data['battery_controller']
  owner.record={'id':'cleanup','before':{'109':175},'phase':'stopping','stop_issued':time.time()-1,
   'arm_until':time.time()-3600,'pending':{'109':{'value':175,'previous':[60]}},'conflicts':{}}
  self.device_registers[109]=60
  await owner.native_write(109,175)
  self.assertEqual(self.device_registers[109],175)
  self.assertEqual(self.writes.count(('number.inverter_battery_max_discharging_current',175)),1)

 async def test_confirmation_rechecks_owner_after_awaited_readback_audit(self):
  data=await self.setup();owner=data['battery_controller']
  owner.record={'id':'pending-owner','before':{'109':175},'phase':'preparing','arm_until':time.time()+120,
   'plan':{'minimum_soc':60},'pending':{'109':{'value':60,'previous':[175]}},'conflicts':{}}
  append=data['journal'].append
  def changed(kind,*args):
   if kind=='native_bulk_readback':owner.record['phase']='stopping'
   return append(kind,*args)
  data['journal'].append=changed
  with self.assertRaisesRegex(ValueError,'owner changed'):await owner.native_write(109,60)
  self.assertEqual(self.writes.count(('number.inverter_battery_max_discharging_current',60)),1)

 async def test_failed_zero_target_proof_cannot_show_confirmed_after_zero_bulk(self):
  data=await self.setup();await self.ticks[0]()
  async def unverified(*args,**kwargs):return {'verified':False,'actual_w':0,'error':'single20 disagrees'}
  self.module.set_zero_target=unverified
  with self.assertRaises(ValueError):await data['zero_import_target']()
  self.assertIsNone(data['settings']['native_grid_target_w'])
  self.assertEqual(data['settings']['zero_target_proof']['actual_w'],0)
  data['settings']['native_grid_target_w']=0
  await data['report']()
  self.assertFalse(self.hass.states.get('sensor.jarvis_energy_sales').attributes['grid_target_confirmed'])

 async def test_other_native_register_routes_still_use_raw_write(self):
  data=await self.setup();await data['window'].native_write(143,500)
  self.assertEqual(self.raw_writes,[(143,[500])])
  self.assertNotIn(('number.inverter_export_surplus_power',500),self.writes)

 async def test_legacy_single_only_zero_proof_is_not_shape_confirmation(self):
  data=await self.setup();data['settings']['native_grid_target_w']=0
  data['settings']['zero_target_proof']={'verified':True,'actual_w':0,'reads':[0,0,0]}
  await data['report']()
  self.assertFalse(self.hass.states.get('sensor.jarvis_energy_sales').attributes['grid_target_confirmed'])
  data['settings']['zero_target_proof']['read_shapes']=[{'single_before':0,'bulk':0,'single_after':0}]*2
  await data['report']()
  self.assertFalse(self.hass.states.get('sensor.jarvis_energy_sales').attributes['grid_target_confirmed'])
  data['settings']['native_grid_target_w']=1
  data['settings']['zero_target_proof']={'verified':True,'actual_w':1,'reads':[1]*7,'read_shapes':[{'single_before':1,'bulk':1,'single_after':1}]*2}
  await data['report']()
  self.assertEqual(self.hass.states.get('sensor.jarvis_energy_sales').attributes['grid_target_w'],1)
  self.assertTrue(self.hass.states.get('sensor.jarvis_energy_sales').attributes['grid_target_confirmed'])

 async def test_shared_native_clock_range_admits_eleven_second_lag_without_sync(self):
  from test_simple_sale_adapter import FakeBattery
  from unittest.mock import AsyncMock
  from zoneinfo import ZoneInfo
  with patch.object(self.module,'BatterySaleController',FakeBattery):data=await self.setup()
  device=self.hass.config_entries.async_entries('solarman')[0].runtime_data.device;original=device.execute
  async def lagged(code,address,count=1,**kwargs):
   if address==62:
    dt=datetime.fromtimestamp(time.time()-11,ZoneInfo('Europe/Prague'))
    return [((dt.year-2000)<<8)|dt.month,(dt.day<<8)|dt.hour,(dt.minute<<8)|dt.second]
   return await original(code,address,count=count,**kwargs)
  device.execute=lagged;self.module.sync_native_clock=AsyncMock(side_effect=AssertionError('Unnecessary RTC write'))
  await self.ticks[0]();await data['commission_battery']()
  self.module.sync_native_clock.assert_not_awaited()
 async def test_start_reads_native_cap_register_before_enabling(self):
  data=await self.setup();await self.ticks[0]()
  await self.service('start_sale',{'power_w':500,'duration_minutes':3})
  self.assertIn((3,143,1),self.device_reads)

 async def test_read_only_native_program_snapshot_does_not_change_inverter(self):
  entry=self.hass.config_entries.async_entries('solarman')[0]
  async def execute(code,address,count=1):
   self.assertEqual(code,3)
   if address==62:return [0x1a0b,0x050f,0x1e00]
   if address==146:return [255,0]+[0]*30
   if address==340:return [12000]
   if address==212:return [200,50,94,460,5,0,300,300]
   if address==98:return [0]*6+[20]+[0]*4+[175]+[0]*2
   raise ValueError(address)
  entry.runtime_data.device.execute=execute
  data=await self.setup();await self.ticks[0]()
  snapshot=self.hass.states.get('sensor.jarvis_energy_sales').attributes['native_program']
  self.assertEqual(snapshot['clock_local'],'2026-11-05T15:30:00+01:00')
  self.assertEqual(len(snapshot['registers_146_177']),32)
  self.assertEqual(snapshot['bms_discharge_limit_a'],50)
  self.assertEqual(snapshot['bms_max_discharge_limit_a'],300)
  self.assertEqual(snapshot['register_104'],20)
  self.assertEqual(snapshot['register_109'],175)
  self.assertEqual(data['settings']['native_grid_target_w'],20)
  self.assertEqual(self.writes,[])

 async def test_native_window_blocks_ordinary_sale_and_charge_conflict(self):
  data=await self.setup();await self.ticks[0]()
  self.assertIn('window',data)
  data['window'].record={'before':{'109':175},'phase':'armed','end':time.time()+300}
  with self.assertRaises(ValueError):await self.service('start_sale',{'mode':'pv','power_w':500,'duration_minutes':3})
  self.assertEqual(self.writes,[])
 async def test_native_stop_status_stays_visible_while_device_ack_is_pending(self):
  data=await self.setup();await self.ticks[0]()
  window=data['window'];window.record={'id':'pending-stop','before':{'109':175},'phase':'armed','end':time.time()+300}
  entered=asyncio.Event();release=asyncio.Event()
  async def blocked(address,value):
   if address==143 and not entered.is_set():entered.set();await release.wait()
  window.native_write=blocked
  task=asyncio.create_task(data['stop']());await entered.wait()
  try:
   self.assertGreaterEqual(len(self.ticks),2,'Status updates need an independent timer')
   await self.ticks[1]()
   state=self.hass.states.get('sensor.jarvis_energy_sales')
   self.assertEqual(state.attributes['native_test']['phase'],'stopping')
  finally:
   release.set()
   with self.assertRaises(ValueError):await task

 async def test_expiring_file_start_is_durable_and_not_repeated(self):
  import json
  data=await self.setup();await self.ticks[0]()
  now=time.time();path=pathlib.Path(self.hass.config.path('jarvis_workspace','sales-command.json'))
  path.parent.mkdir(exist_ok=True)
  path.write_text(json.dumps({'id':'test-1','issued_at':now,'expires_at':now+60,'action':'start','data':{'mode':'pv','power_w':500,'duration_minutes':3}}))
  await self.ticks[0]()
  self.assertTrue(data['controller'].active)
  count=len(self.writes);await self.ticks[0]()
  self.assertEqual(len(self.writes),count)
  self.assertEqual(data['settings']['command']['status'],'confirmed')
 async def test_expired_file_command_cannot_start_sale(self):
  import json
  data=await self.setup();await self.ticks[0]()
  now=time.time();path=pathlib.Path(self.hass.config.path('jarvis_workspace','sales-command.json'))
  path.parent.mkdir(exist_ok=True)
  path.write_text(json.dumps({'id':'old','issued_at':now-100,'expires_at':now-1,'action':'start','data':{'power_w':500}}))
  await self.ticks[0]()
  self.assertFalse(data['controller'].active);self.assertEqual(self.writes,[])
 async def test_file_command_does_not_expose_arbitrary_services(self):
  import json
  data=await self.setup();await self.ticks[0]()
  now=time.time();path=pathlib.Path(self.hass.config.path('jarvis_workspace','sales-command.json'))
  path.parent.mkdir(exist_ok=True)
  path.write_text(json.dumps({'id':'bad','issued_at':now,'expires_at':now+60,'action':'service','data':{'service':'switch.turn_off'}}))
  await self.ticks[0]()
  self.assertEqual(self.writes,[])

 async def test_unreadable_inbox_does_not_disable_export_guard(self):
  data=await self.setup();await self.ticks[0]()
  await self.service('start_sale',{'power_w':500,'duration_minutes':3})
  path=pathlib.Path(self.hass.config.path('jarvis_workspace','sales-command.json'));path.mkdir()
  self.hass.states.async_set('sensor.inverter_grid_power',-931);self.poll()
  await self.ticks[0]()
  self.assertFalse(data['controller'].active)
 async def test_overlapping_ticks_claim_command_only_once(self):
  import json
  data=await self.setup();await self.ticks[0]()
  now=time.time();path=pathlib.Path(self.hass.config.path('jarvis_workspace','sales-command.json'));path.parent.mkdir(exist_ok=True)
  path.write_text(json.dumps({'id':'concurrent','issued_at':now,'expires_at':now+60,'action':'start','data':{'power_w':500,'duration_minutes':3}}))
  await asyncio.gather(self.ticks[0](),self.ticks[0]())
  self.assertTrue(data['controller'].active)
  self.assertEqual(sum(e=='switch.inverter_export_surplus' and v=='on' for e,v in self.writes),1)
  self.assertEqual(data['settings']['command']['status'],'confirmed')

 async def test_reused_id_with_new_timestamp_cannot_start_again(self):
  import json
  data=await self.setup();await self.ticks[0]()
  path=pathlib.Path(self.hass.config.path('jarvis_workspace','sales-command.json'));path.parent.mkdir(exist_ok=True)
  async def send():
   now=time.time();path.write_text(json.dumps({'id':'same-id','issued_at':now,'expires_at':now+60,'action':'start','data':{'power_w':500,'duration_minutes':3}}));await self.ticks[0]()
  await send();await self.service('stop_sale',{});await send()
  self.assertFalse(data['controller'].active)
  self.assertEqual(sum(e=='switch.inverter_export_surplus' and v=='on' for e,v in self.writes),1)

 async def test_start_rechecks_expiry_inside_control_lock(self):
  data=await self.setup();await self.ticks[0]()
  with self.assertRaisesRegex(ValueError,'vypršel'):
   await data['start']({'power_w':500,'duration_minutes':3},valid_until=time.time()-1)
  self.assertEqual(self.writes,[])

 async def test_protective_stop_still_runs_when_command_database_claim_fails(self):
  import json
  for action,body in [('stop',{}),('automatic',{'enabled':False})]:
   data=await self.setup();tick=next(fn for fn in reversed(self.ticks) if fn.__name__=='tick');await tick()
   await self.service('start_sale',{'power_w':500,'duration_minutes':3})
   def fail(_body):raise OSError('database full')
   data['journal'].claim_command=fail
   now=time.time();path=pathlib.Path(self.hass.config.path('jarvis_workspace','sales-command.json'));path.parent.mkdir(exist_ok=True)
   path.write_text(json.dumps({'id':'stop-'+action,'issued_at':now,'expires_at':now+60,'action':action,'data':body}))
   await tick()
   self.assertFalse(data['controller'].active)
   self.assertEqual(self.hass.states.get('switch.inverter_export_surplus').state,'off')

 async def test_automatic_pv_operation_stays_within_nine_point_three_kw_operating_limit(self):
  data=await self.setup();data['settings'].update(automatic=True,pv_verified=True)
  await self.ticks[0]()
  self.assertTrue(data['controller'].active)
  self.assertLessEqual(data['controller'].record['power_w'],9300)

 async def test_command_expiring_during_native_reads_cannot_enable_export(self):
  data=await self.setup();await self.ticks[0]()
  device=self.hass.config_entries.async_entries('solarman')[0].runtime_data.device
  original=device.execute
  async def delayed(*args,**kwargs):
   await self.real_sleep(.02);return await original(*args,**kwargs)
  device.execute=delayed
  with self.assertRaisesRegex(ValueError,'vypršel'):
   await data['start']({'power_w':500,'duration_minutes':3},valid_until=time.time()+.01)
  self.assertEqual(self.writes,[])

 async def test_nonzero_native_import_bias_does_not_block_safe_pv_selling(self):
  data=await self.setup();await self.ticks[0]();self.device_registers[104]=20
  self.hass.states.async_set('number.inverter_zero_export_power',20)
  await self.service('start_sale',{'power_w':500,'duration_minutes':3})
  self.assertTrue(data['controller'].active)
  self.assertEqual(data['settings'].get('native_grid_target_w'),20)

if __name__=='__main__':unittest.main()

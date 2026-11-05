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
  self.last_updated=self.last_reported=datetime.now(timezone.utc)

class States:
 def __init__(self):self.items={}
 def get(self,key):return self.items.get(key)
 def async_all(self):return list(self.items.values())
 def async_set(self,key,value,attributes=None):self.items[key]=State(key,value,attributes)

class Store:
 def __init__(self,*args):self.data=None
 async def async_load(self):return copy.deepcopy(self.data)
 async def async_save(self,data):self.data=copy.deepcopy(data)

class AdapterTests(unittest.IsolatedAsyncioTestCase):
 async def asyncSetUp(self):
  self.temp=tempfile.TemporaryDirectory();path=pathlib.Path(self.temp.name)
  (path/'.storage').mkdir()
  self.services={};self.writes=[];self.tasks=[];self.ticks=[]
  self.hass=types.SimpleNamespace(data={},is_running=False,states=States(),config=types.SimpleNamespace(path=lambda *parts:str(path.joinpath(*parts))))
  self.hass.http=types.SimpleNamespace(register_view=lambda view:None)
  self.hass.bus=types.SimpleNamespace(async_fire=lambda *a:None,async_listen_once=lambda *a:None)
  self.hass.async_create_task=lambda coro:self.tasks.append(asyncio.create_task(coro))
  async def executor(fn,*args):return fn(*args)
  self.hass.async_add_executor_job=executor
  async def call(domain,service,data,blocking=False):
   entity=data['entity_id'];value=data.get('value',data.get('option','on' if service=='turn_on' else 'off'))
   self.writes.append((entity,value));self.hass.states.async_set(entity,value)
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
   'number.inverter_export_surplus_power':9990,'sensor.inverter_battery':99,'sensor.inverter_battery_power':-50,
   'sensor.inverter_grid_power':20,'sensor.inverter_pv_power':400,'sensor.inverter_battery_temperature':20,
   'sensor.inverter_device_state':'Normal','sensor.inverter_device_alarm':'OK','sensor.inverter_device_fault':'OK',
   'binary_sensor.inverter_battery_alarm':'off','binary_sensor.inverter_battery_fault':'off'}
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

if __name__=='__main__':unittest.main()

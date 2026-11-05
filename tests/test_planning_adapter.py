import copy
from datetime import datetime,timezone
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

class Store:
 def __init__(self,*args):self.data=None
 async def async_load(self):return copy.deepcopy(self.data)
 async def async_save(self,data):self.data=copy.deepcopy(data)

class PlanningAdapterTests(unittest.IsolatedAsyncioTestCase):
 async def asyncSetUp(self):
  modules={n:types.ModuleType(n) for n in ('homeassistant','homeassistant.helpers','homeassistant.helpers.event','homeassistant.helpers.storage')}
  modules['homeassistant.helpers.storage'].Store=Store
  modules['homeassistant.helpers.event'].async_track_time_interval=lambda *args:None
  package=types.ModuleType('planning_adapter_test');package.__path__=[str(Path('managed_sources/spot_control').resolve())];modules[package.__name__]=package
  self.patch=patch.dict(sys.modules,modules);self.patch.start()
  file=Path('managed_sources/spot_control/planning_setup.py')
  spec=importlib.util.spec_from_file_location('planning_adapter_test.planning_setup',file)
  self.module=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.module)
  async def executor(fn,*args):return fn(*args)
  self.hass=types.SimpleNamespace(data={},is_running=False,states=types.SimpleNamespace(get=lambda _:None),bus=types.SimpleNamespace(async_listen_once=lambda *args:None),async_add_executor_job=executor)
 async def asyncTearDown(self):self.patch.stop()
 async def test_no_archive_keeps_battery_reserve_fully_protected(self):
  plan=await self.module.async_setup_planning(self.hass);await plan['refresh']()
  out=plan['snapshot']();self.assertEqual(out['required_soc'],100)
  self.assertTrue(out['history_error'])
 async def test_native_test_prevents_background_history_fetch(self):
  calls=[]
  async def read(*args):calls.append(args);return {'complete':True}
  self.hass.data['jarvis_energy_archive']={'read_window':read}
  self.hass.data['jarvis_spot_control_sales']={'window':types.SimpleNamespace(active=True)}
  plan=await self.module.async_setup_planning(self.hass);await plan['refresh']()
  self.assertEqual(calls,[])
 async def test_incomplete_archive_cannot_become_a_valid_house_model(self):
  async def read(*args):return {'complete':False,'samples':[]}
  self.hass.data['jarvis_energy_archive']={'read_window':read}
  plan=await self.module.async_setup_planning(self.hass);await plan['refresh']()
  self.assertEqual(plan['snapshot']()['required_soc'],100)
  self.assertTrue(plan['snapshot']()['history_error'])
 async def test_calibration_receives_forecast_issued_on_previous_day(self):
  seen=[]
  async def read(start,end):
   return {'complete':True,'samples':[],'publications':{'weather':{'attributes':{'fetched_at':datetime.fromtimestamp(start+3600,timezone.utc).isoformat(),'rows':[]}}}}
  def build(days):seen.extend(days);return {}
  self.hass.data['jarvis_energy_archive']={'read_window':read}
  self.module.build_history=build
  plan=await self.module.async_setup_planning(self.hass);await plan['refresh']()
  self.assertEqual(len(seen),3)
  for day in seen:
   issued=datetime.fromisoformat(day['weather']['fetched_at']).timestamp()
   self.assertLess(issued,day['start'])

if __name__=='__main__':unittest.main()

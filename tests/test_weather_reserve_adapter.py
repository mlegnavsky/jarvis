import importlib.util,sys,types,unittest
from pathlib import Path
from datetime import datetime,timezone
from unittest.mock import patch
from test_planning_adapter import Store
from test_weather_reserve import fixture
from test_sale_adapter import States
class ReserveAdapter(unittest.IsolatedAsyncioTestCase):
 async def asyncSetUp(self):
  modules={n:types.ModuleType(n) for n in ('homeassistant','homeassistant.helpers','homeassistant.helpers.event','homeassistant.helpers.storage')}
  modules['homeassistant.helpers.storage'].Store=Store;modules['homeassistant.helpers.event'].async_track_time_interval=lambda *args:None
  pkg=types.ModuleType('reserve_test');pkg.__path__=[str(Path('managed_sources/spot_control').resolve())];modules[pkg.__name__]=pkg
  self.patch=patch.dict(sys.modules,modules);self.patch.start();self.addCleanup(self.patch.stop)
  spec=importlib.util.spec_from_file_location('reserve_test.weather_reserve_setup',Path('managed_sources/spot_control/weather_reserve_setup.py'));self.mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.mod)
  w,self.block,self.now=fixture();self.clock=patch.object(self.mod.time,'time',lambda:self.now);self.clock.start();self.addCleanup(self.clock.stop)
  self.states=States();self.states.async_set('sensor.jarvis_pocasi_zitenice','ready',w);self.states.async_set('sensor.inverter_today_load_consumption',4);self.states.async_set('sensor.jarvis_spotreba_domu',300)
  self.store=Store();self.mod.Store=lambda *a:self.store
  self.h=types.SimpleNamespace(data={},states=self.states)
 async def test_bootstrap_counter_durable_history_and_higher_consumption(self):
  p=await self.mod.async_setup_weather_reserve(self.h);r=p['snapshot'](self.block,23.552)
  self.assertEqual(r['required_soc'],75);self.assertGreaterEqual(r['house_daily_kwh'],8);self.assertEqual(r['load_quality'],'bootstrap_or_partial')
  self.states.async_set('sensor.inverter_today_load_consumption',18);r=p['snapshot'](self.block,23.552)
  self.assertGreaterEqual(r['required_soc'],90)
  await p['sample']();self.assertTrue(self.store.data['days']);self.assertTrue(self.store.data['history'])
 async def test_unavailable_weather_does_not_reuse_old_forecast(self):
  p=await self.mod.async_setup_weather_reserve(self.h)
  self.assertEqual(p['snapshot'](self.block,23.552)['required_soc'],75)
  self.states.async_set('sensor.jarvis_pocasi_zitenice','unavailable')
  self.assertEqual(p['snapshot'](self.block,23.552)['required_soc'],100)
 async def test_storage_failure_is_visible_and_keeps_safe_calculation(self):
  p=await self.mod.async_setup_weather_reserve(self.h)
  async def fail(*a):raise OSError('disk')
  self.store.async_save=fail;await p['sample']()
  self.assertEqual(p['snapshot'](self.block,23.552)['storage_error'],'OSError')

 async def test_rejected_power_cannot_poison_next_valid_interval(self):
  p=await self.mod.async_setup_weather_reserve(self.h)
  self.now+=60;self.states.async_set('sensor.jarvis_spotreba_domu',100000);p['snapshot'](self.block,23.552)
  self.now+=60;self.states.async_set('sensor.jarvis_spotreba_domu',300);r=p['snapshot'](self.block,23.552)
  self.assertEqual(r['load_covered_hours'],0)
  self.assertEqual(r['required_soc'],75)

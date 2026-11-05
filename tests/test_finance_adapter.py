import datetime as dt
import importlib.util
import pathlib
import time
import unittest
import test_sale_adapter as fixtures

class FinanceAdapterTests(unittest.IsolatedAsyncioTestCase):
 asyncSetUp=fixtures.AdapterTests.asyncSetUp
 asyncTearDown=fixtures.AdapterTests.asyncTearDown
 async def setup_finance(self):
  spec=importlib.util.spec_from_file_location('sales_adapter_test.finance_setup',pathlib.Path('managed_sources/spot_control/finance_setup.py'))
  module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);self.finance_module=module
  self.hass.states.async_set('sensor.inverter_today_energy_import',4.9)
  self.hass.states.async_set('sensor.inverter_today_energy_export',0)
  self.data=await module.async_setup_finance(self.hass)
  return self.data
 async def test_publishes_today_purchase_cost_and_refreshes_with_grid_measurements(self):
  data=await self.setup_finance();now=time.time()
  data['ledger'].add([{'t':now-5,'grid_w':-1000,'import_kwh':4.9,'export_kwh':0}])
  self.hass.states.async_set('sensor.inverter_grid_power',-1000)
  await data['capture']()
  self.assertGreaterEqual(float(self.hass.states.get('sensor.jarvis_dnes_nakoupeno_za').state),24.50)
  self.assertGreater(data['snapshot']()['known_sale_czk'],0)
  self.assertEqual(self.hass.states.get('sensor.jarvis_dnes_prodano_za').state,'unknown')
  report=pathlib.Path(self.hass.config.path('jarvis_workspace','finance-runtime.json'))
  self.assertTrue(report.exists())
 async def test_private_archive_backfill_is_replay_safe(self):
  now=time.time();samples=[]
  for t in (now-20,now-10):
   samples.append({'t':t+.1,'values':{'sensor.inverter_grid_power':{'value':'-1000','source_updated':dt.datetime.fromtimestamp(t,dt.timezone.utc).isoformat()},'sensor.inverter_today_energy_import':{'value':'4.9','source_updated':dt.datetime.fromtimestamp(t,dt.timezone.utc).isoformat()},'sensor.inverter_today_energy_export':{'value':'0','source_updated':dt.datetime.fromtimestamp(t,dt.timezone.utc).isoformat()}}})
  async def read(start,end):return {'samples':samples,'publications':{},'complete':True}
  self.hass.data['jarvis_energy_archive']={'read_window':read}
  data=await self.setup_finance()
  await data['backfill']();first=float(self.hass.states.get('sensor.jarvis_dnes_prodano_za').state)
  await data['backfill']();second=float(self.hass.states.get('sensor.jarvis_dnes_prodano_za').state)
  self.assertGreater(first,0);self.assertEqual(first,second)

 async def test_archive_is_reconciled_again_after_delayed_upload(self):
  from unittest.mock import patch
  calls=[]
  async def read(start,end):calls.append((start,end));return {'samples':[],'publications':{},'complete':True}
  self.hass.data['jarvis_energy_archive']={'read_window':read}
  data=await self.setup_finance();await data['backfill']()
  self.assertEqual(len(calls),1)
  later=time.time()+61
  with patch.object(self.finance_module.time,'time',return_value=later):
   await data['capture']()
   await __import__('asyncio').gather(*self.tasks)
  self.assertGreaterEqual(len(calls),2)

 async def test_unverified_history_does_not_publish_zero_as_whole_day_sale(self):
  data=await self.setup_finance();await data['capture']()
  body=data['snapshot']()
  self.assertFalse(body['archive_loaded']);self.assertEqual(body['quality'],'partial')
  self.assertIsNone(body['sale_czk']);self.assertEqual(body['purchase_czk'],24.5)

if __name__=='__main__':unittest.main()

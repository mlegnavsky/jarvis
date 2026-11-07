from unittest.mock import patch
import unittest
import test_sale_adapter as fixture

class HousePriorityTests(unittest.IsolatedAsyncioTestCase):
 asyncSetUp=fixture.AdapterTests.asyncSetUp
 asyncTearDown=fixture.AdapterTests.asyncTearDown
 poll=fixture.AdapterTests.poll
 setup=fixture.AdapterTests.setup
 service=fixture.AdapterTests.service
 async def test_saved_tiny_export_is_disabled_without_disabling_owner_automatic_plan(self):
  saved={'automatic':True,'requested_automatic':True,'bias_enabled':True,
         'selected_block':{'day':'2099-01-01','start':9999999999,'end':10000000899},
         'policy':{'sale_soc':75,'max_w':9300},'completed_battery_plan':{'day':'2026-11-06'}}
  with patch.object(fixture.Store,'async_load',return_value={'settings':saved}):
   data=await self.setup()
  self.assertFalse(data['settings']['bias_enabled'])
  self.assertTrue(data['settings']['automatic'])
  self.assertTrue(data['settings']['requested_automatic'])
  self.assertEqual(data['settings']['selected_block'],saved['selected_block'])
  self.assertEqual(data['settings']['policy'],saved['policy'])
  self.assertEqual(data['settings']['completed_battery_plan'],saved['completed_battery_plan'])
  await self.service('set_sales_automatic',{'enabled':True})
  self.assertFalse(data['settings']['bias_enabled'])
  await self.ticks[0]()
  self.assertFalse(data['controller'].active)
  self.assertNotIn(('select.inverter_work_mode','Export First'),self.writes)
  await data['report']()
  attrs=self.hass.states.get('sensor.jarvis_energy_sales').attributes
  self.assertIn('dom',attrs['reason'].lower())
  self.assertFalse(attrs['bias_policy']['enabled'])
  self.assertIn('dom',attrs['bias_policy']['disabled_reason'].lower())

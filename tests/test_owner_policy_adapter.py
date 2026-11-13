import unittest
import test_simple_sale_adapter as fixtures
class OwnerPolicyAdapterTests(unittest.IsolatedAsyncioTestCase):
 asyncSetUp=fixtures.SimpleAdapterTests.asyncSetUp
 asyncTearDown=fixtures.SimpleAdapterTests.asyncTearDown
 setup=fixtures.SimpleAdapterTests.setup
 refresh=fixtures.SimpleAdapterTests.refresh
 poll=fixtures.SimpleAdapterTests.poll
 prices=fixtures.SimpleAdapterTests.prices
 service=fixtures.SimpleAdapterTests.service
 async def test_policy_save_is_cas_atomic_no_flags_no_device_calls(self):
  data=await self.setup();await data['report']();a=self.hass.states.get('sensor.jarvis_energy_sales').attributes
  before=dict(data['settings']);writes=len(self.writes)
  await data['configure_policy']({'sale_soc':65,'pv_soc':98,'block_minutes':90},a['policy_revision'])
  self.assertEqual(len(self.writes),writes);self.assertEqual(data['settings']['automatic'],before['automatic'])
  self.assertEqual(data['settings']['policy']['sale_soc'],65)
  with self.assertRaises(ValueError):await data['configure_policy']({'sale_soc':70},a['policy_revision'])
  self.assertEqual(data['settings']['policy']['sale_soc'],65)
 async def test_policy_save_rejects_busy_and_unknown_flags(self):
  data=await self.setup();await data['report']();a=self.hass.states.get('sensor.jarvis_energy_sales').attributes
  with self.assertRaises(ValueError):await data['configure_policy']({'automatic':True},a['policy_revision'])
  data['controller'].record={'id':'running','phase':'running','before':{'cap':0}}
  with self.assertRaises(ValueError):await data['configure_policy']({'sale_soc':65},a['policy_revision'])

 async def test_fixed_home_floor_and_pv_threshold_drive_next_transaction(self):
  data=await self.setup();await data['report']();a=self.hass.states.get('sensor.jarvis_energy_sales').attributes
  with self.assertRaises(ValueError):await data['configure_policy']({'home_soc':35},a['policy_revision'])
  await data['configure_policy']({'home_soc':30,'resume_soc':36,'sale_soc':65,'pv_soc':98},a['policy_revision'])
  data['settings'].update(automatic=True,requested_automatic=True,pv_verified=True)
  self.hass.states.async_set('sensor.inverter_battery',99);self.hass.states.async_set('sensor.inverter_pv_power',3000)
  import math
  self.prices(math.floor(self.clock[0]/900)*900);self.refresh();await self.ticks[0]()
  self.assertTrue(data['controller'].active,self.hass.states.get('sensor.jarvis_energy_sales').attributes['error'])
  self.assertEqual(self.native_registers[166],30)
  self.assertTrue(all(self.native_registers[i]==30 for i in range(166,172)))
 async def test_store_failure_rolls_back_policy_and_intent(self):
  data=await self.setup();await data['report']();a=self.hass.states.get('sensor.jarvis_energy_sales').attributes
  before=dict(data['settings'])
  async def fail(_):raise OSError('disk full')
  self.storage.async_save=fail
  with self.assertRaises(OSError):await data['configure_policy']({'sale_soc':65},a['policy_revision'])
  self.assertEqual(data['settings'],before)

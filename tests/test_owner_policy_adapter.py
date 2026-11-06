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

 async def test_native_house_floor_cannot_be_reconfigured_through_policy(self):
  data=await self.setup();await data['report']();a=self.hass.states.get('sensor.jarvis_energy_sales').attributes
  with self.assertRaises(ValueError):await data['configure_policy']({'home_soc':35},a['policy_revision'])
  self.assertFalse(self.native_group_writes)
 async def test_store_failure_rolls_back_policy_and_intent(self):
  data=await self.setup();await data['report']();a=self.hass.states.get('sensor.jarvis_energy_sales').attributes
  before=dict(data['settings'])
  async def fail(_):raise OSError('disk full')
  self.storage.async_save=fail
  with self.assertRaises(OSError):await data['configure_policy']({'sale_soc':65},a['policy_revision'])
  self.assertEqual(data['settings'],before)

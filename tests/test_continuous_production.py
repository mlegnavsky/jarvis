import unittest
import test_simple_sale_adapter as fixtures
class ContinuousProductionTests(unittest.IsolatedAsyncioTestCase):
 asyncSetUp=fixtures.SimpleAdapterTests.asyncSetUp
 asyncTearDown=fixtures.SimpleAdapterTests.asyncTearDown
 setup=fixtures.SimpleAdapterTests.setup
 refresh=fixtures.SimpleAdapterTests.refresh
 poll=fixtures.SimpleAdapterTests.poll
 prices=fixtures.SimpleAdapterTests.prices
 service=fixtures.SimpleAdapterTests.service
 async def test_bias_renews_without_service_or_inverter_writes(self):
  data=await self.setup();c=data['controller'];data['settings'].update(automatic=True,requested_automatic=True,bias_verified=True)
  self.hass.states.async_set('sensor.inverter_battery',80);self.refresh()
  await c.start('bias',20,60,minimum_soc=30,purpose='automatic')
  c.record['deadline']=self.clock[0]+30;c.observed=True;c.record['phase']='running'
  before=list(self.writes);self.refresh()
  self.assertTrue(await c.renew_automatic_window())
  self.assertGreater(c.record['deadline'],self.clock[0]+800);self.assertEqual(self.writes,before)
 async def test_house_mismatch_never_repairs_settings(self):
  data=await self.setup();data['settings'].update(automatic=True,requested_automatic=True,pv_verified=True)
  self.hass.states.async_set('sensor.inverter_battery',99);self.hass.states.async_set('sensor.inverter_pv_power',3000)
  for i in range(6):self.native_registers[166+i]=100;self.hass.states.async_set(f'number.inverter_program_{i+1}_soc',100)
  self.refresh();before=list(self.native_group_writes);await self.ticks[0]()
  self.assertEqual(self.native_group_writes,before);self.assertFalse(data['controller'].active)
  self.assertTrue(data['settings']['inhibited'])
 async def test_automatic_pv_does_not_write_soc_slots(self):
  data=await self.setup();data['settings'].update(automatic=True,requested_automatic=True,pv_verified=True)
  self.hass.states.async_set('sensor.inverter_battery',99);self.hass.states.async_set('sensor.inverter_pv_power',3000);self.refresh();await self.ticks[0]()
  self.assertTrue(data['controller'].active)
  self.assertFalse([e for e,v in self.writes if '_soc' in e]);self.assertFalse(self.native_group_writes)
 async def test_completion_saved_atomically_for_original_block_before_handler(self):
  from production_policy import block_key
  data=await self.setup();b=data['battery_controller'];original={'start':self.clock[0]-10,'end':self.clock[0]+600,'day':'2026-11-06'}
  replacement={**original,'end':original['end']+300}
  b.record={'before':{'143':9300},'id':'transaction','phase':'measuring','power_w':500,'minimum_soc':60,'purpose':'automatic','business_block':original}
  data['settings']['selected_block']=replacement
  # No adapter tick/handle_native_stops can run between this clear and assertion.
  await b.stop('reserve')
  self.assertIn(block_key(original),self.storage.data['settings'].get('completed_blocks',{}))
  self.assertNotIn(block_key(replacement),self.storage.data['settings']['completed_blocks'])
  self.assertFalse(self.storage.data['battery_sale'])
 async def test_normal_bias_without_probe_is_started_not_forged_verified(self):
  data=await self.setup();data['settings'].update(automatic=True,requested_automatic=True,bias_verified=False)
  self.hass.states.async_set('sensor.inverter_battery',60);self.hass.states.async_set('sensor.inverter_pv_power',0)
  self.refresh();await self.ticks[0]()
  self.assertTrue(data['controller'].active)
  self.assertEqual(data['controller'].record['mode'],'bias')
  self.assertFalse(data['settings']['bias_verified'])

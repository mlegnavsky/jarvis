import unittest,time,sys
sys.path.insert(0,'managed_sources/spot_control')
from engine import Controller,CURRENT,SWITCH

class HeatingChargeTests(unittest.IsolatedAsyncioTestCase):
 async def asyncSetUp(self):
  self.values={CURRENT:'175',SWITCH:'off','sensor.inverter_battery_temperature':'15','number.inverter_battery_max_charging_current':'175','sensor.inverter_battery_voltage':'52.8','sensor.inverter_battery':'30','select.inverter_work_mode':'Zero Export To CT','switch.inverter_export_surplus':'off','select.inverter_time_of_use':'Week'}
  for i in range(1,7):self.values.update({f'time.inverter_program_{i}_time':f'{(i-1)*4:02}:00:00',f'select.inverter_program_{i}_charging':'Disabled',f'number.inverter_program_{i}_soc':'30'})
  self.before=dict(self.values);self.calls=[];self.saved={}
  async def write(e,v):self.calls.append((e,v));self.values[e]=str(v)
  async def save(record):
   import copy
   self.saved=copy.deepcopy(record)
  self.c=Controller(lambda:dict(self.values),write,save,clock=lambda:1000)
 async def test_scoped_1000w_charge_and_exact_restore(self):
  await self.c.start_heating(60)
  self.assertEqual(self.c.record['purpose'],'heating');self.assertTrue(self.c.active)
  self.assertEqual(self.values[CURRENT],'19');self.assertEqual(self.values[SWITCH],'on')
  self.assertAlmostEqual(float(self.values[CURRENT])*52.8,1000,delta=30)
  self.assertTrue(self.c.heating_ready())
  self.assertEqual(self.values['number.inverter_program_1_soc'],'90')
  self.assertEqual(self.values['number.inverter_program_2_soc'],'30')
  await self.c.stop();self.assertEqual(self.values,self.before);self.assertFalse(self.c.active)
 async def test_rising_soc_does_not_end_charge_and_slot_rollover_is_restored(self):
  await self.c.start_heating(60);self.values['sensor.inverter_battery']='35'
  await self.c.tick_heating(True,minute=300)
  self.assertEqual(self.values['select.inverter_program_2_charging'],'Grid')
  self.assertTrue(self.c.active)
  await self.c.stop();self.before['sensor.inverter_battery']='35';self.assertEqual(self.values,self.before)
 async def test_conflicting_setting_is_not_overwritten_on_restore(self):
  await self.c.start_heating(60);self.values[CURRENT]='25';await self.c.stop()
  self.assertEqual(self.values[CURRENT],'25');self.assertTrue(self.c.active);self.assertIn('conflict',self.c.error)
  self.assertEqual(self.values['select.inverter_program_1_charging'],'Disabled')
 async def test_native_30_floor_and_unrelated_existing_charge_protected(self):
  self.values['number.inverter_program_3_soc']='29'
  with self.assertRaises(ValueError):await self.c.start_heating(60)
  self.assertFalse(self.calls)
  self.values.update(self.before);self.c.record={'before':{'some':'state'},'purpose':'test'}
  with self.assertRaises(ValueError):await self.c.start_heating(60)
 async def test_failed_durable_save_causes_no_writes(self):
  async def fail(_):raise OSError('disk full')
  self.c.save=fail
  with self.assertRaises(OSError):await self.c.start_heating(60)
  self.assertFalse(self.calls)
 async def test_health_loss_restores_and_owner_can_share_session(self):
  await self.c.start_heating(60);n=len(self.calls);await self.c.start_heating(60);self.assertEqual(len(self.calls),n)
  await self.c.tick_heating(False,minute=60);self.assertFalse(self.c.active);self.assertEqual(self.values,self.before)
 async def test_reaching_target90_keeps_grid_support_until_heater_stops(self):
  await self.c.start_heating(60);self.values['sensor.inverter_battery']='90'
  await self.c.tick_heating(True,minute=60);self.assertTrue(self.c.active);self.assertTrue(self.c.heating_ready())
 async def test_owned_slot_rollover_pending_is_continuation_ready(self):
  await self.c.start_heating(60);original=self.c.write
  async def check(e,v):
   if e=='number.inverter_program_2_soc':self.assertTrue(self.c.heating_ready(include_pending=True));self.assertFalse(self.c.heating_ready())
   await original(e,v)
  self.c.write=check;await self.c.tick_heating(True,minute=300);self.assertTrue(self.c.heating_ready())
 async def test_count_1_2_1_preserves_one_before_image_and_then_restores_zero(self):
  await self.c.start_heating(60,heaters=1);before=dict(self.c.record['before'])
  self.assertEqual(self.c.record['target_w'],1000)
  await self.c.start_heating(60,heaters=2)
  self.assertEqual(self.c.record['target_w'],2000);self.assertEqual(self.c.record['heaters'],2)
  self.assertEqual(self.values[CURRENT],'38');self.assertEqual(self.c.record['before'],before)
  await self.c.resize_heating(1);self.assertEqual(self.values[CURRENT],'19');self.assertEqual(self.c.record['target_w'],1000)
  await self.c.stop();self.assertEqual(self.values,self.before)
 async def test_count_validation_and_cap_are_respected(self):
  for count in (0,3,True,1.5):
   with self.assertRaises(ValueError):await self.c.start_heating(60,heaters=count)
  self.values['number.inverter_battery_max_charging_current']='30'
  await self.c.start_heating(60,heaters=2);self.assertEqual(self.values[CURRENT],'30')

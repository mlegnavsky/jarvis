"""Real state-machine tests with device I/O as the only fake boundary."""
import copy
import sys
import unittest
sys.path.insert(0,'managed_sources/spot_control')
try:from sale_controller import SaleController
except ImportError:SaleController=None

class SaleTests(unittest.IsolatedAsyncioTestCase):
 def setUp(self):
  self.assertIsNotNone(SaleController,'sales controller is not implemented')
  self.states={'select.inverter_work_mode':'Zero Export To CT','switch.inverter_export_surplus':'off',
   'number.inverter_export_surplus_power':'9990','sensor.inverter_battery':'99',
   'sensor.inverter_battery_power':'-700','sensor.inverter_grid_power':'20',
   'select.inverter_energy_pattern':'Load First','select.inverter_time_of_use':'Week'}
  for i in range(1,7):
   self.states[f'number.inverter_program_{i}_soc']='30'
   self.states[f'number.inverter_program_{i}_power']='12000'
   self.states[f'select.inverter_program_{i}_charging']='Disabled'
  self.persisted={};self.events=[];self.calls=[];self.now=100;self.fresh=True;self.net=4
  self.sample_stamp=100
 async def save(self,r):self.persisted=copy.deepcopy(r)
 async def event(self,kind,data):self.events.append((kind,copy.deepcopy(data)))
 async def write(self,e,v):
  self.assertTrue(self.persisted.get('before'))
  self.assertEqual(self.events[-1][0],'write_intent')
  self.calls.append((e,v));self.states[e]=str(v)
  self.now+=1;self.sample_stamp=self.now
  if e=='switch.inverter_export_surplus' and v=='off':self.states['sensor.inverter_grid_power']='20'
 def c(self,saved=None):return SaleController(lambda:self.states,self.write,self.save,self.event,clock=lambda:self.now,healthy=lambda:self.fresh,price=lambda:self.net,saved=saved,reported=lambda:self.sample_stamp)
 async def test_pv_only_caps_before_enabling_and_does_not_change_battery_program(self):
  c=self.c();await c.start('pv',500,3)
  self.assertEqual(self.calls,[('number.inverter_export_surplus_power',500),('switch.inverter_export_surplus','on')])
  self.assertEqual(self.states['select.inverter_work_mode'],'Zero Export To CT')
  self.assertEqual(self.states['number.inverter_program_1_soc'],'30')
  self.assertFalse(c.observed)
 async def test_confirm_running_only_after_measured_export(self):
  c=self.c();await c.start('pv',500,3);self.states['sensor.inverter_grid_power']='-300'
  self.now+=5;self.sample_stamp=self.now
  await c.tick();self.assertTrue(c.observed)
 async def test_stop_preserves_safe_export_cap(self):
  c=self.c();await c.start('pv',500,3);await c.stop()
  self.assertFalse(c.active);self.assertEqual(self.states['switch.inverter_export_surplus'],'off')
  self.assertEqual(float(self.states['number.inverter_export_surplus_power']),9300)
 async def test_negative_price_or_stale_data_stops(self):
  for change in ('price','fresh'):
   c=self.c();self.fresh=True;self.net=4;await c.start('pv',500,3)
   if change=='price':self.net=-1
   else:self.fresh=False
   await c.tick();self.assertFalse(c.active)
 async def test_deadline_stops_and_restart_reconciles(self):
  c=self.c();await c.start('pv',500,3);self.now=281;await c.tick();self.assertFalse(c.active)
  self.now=100;await c.start('pv',500,3)
  recovered=self.c(self.persisted);await recovered.stop();self.assertFalse(recovered.active)
 async def test_snapshot_failure_never_changes_device(self):
  c=self.c()
  async def fail(r):raise RuntimeError('disk full')
  c.save=fail
  with self.assertRaises(RuntimeError):await c.start('pv',500,3)
  self.assertEqual(self.calls,[])
 async def test_partial_failure_attempts_safe_stop(self):
  c=self.c();real=c.write
  async def fail(e,v):
   if e=='switch.inverter_export_surplus' and v=='on':raise RuntimeError('offline')
   await real(e,v)
  c.write=fail
  with self.assertRaises(RuntimeError):await c.start('pv',500,3)
  self.assertEqual(self.states['switch.inverter_export_surplus'],'off')
 async def test_refuses_overlimit_and_invalid_duration(self):
  for power,minutes in [(9500,3),(500,0),(500,61),(float('nan'),3)]:
   with self.assertRaises(ValueError):await self.c().start('pv',power,minutes)
  self.assertEqual(self.calls,[])
 async def test_battery_floor_programmed_before_export_and_respected(self):
  c=self.c();await c.start('battery',1000,3)
  turn=next(i for i,(e,v) in enumerate(self.calls) if v=='Export First')
  for i in range(1,7):self.assertIn((f'number.inverter_program_{i}_soc',62),self.calls[:turn])
  self.states['sensor.inverter_battery']='62';await c.tick();self.assertFalse(c.active)
 async def test_pv_mode_stops_if_battery_is_exporting(self):
  c=self.c();await c.start('pv',500,3)
  self.states['sensor.inverter_grid_power']='-400';self.states['sensor.inverter_battery_power']='500'
  await c.tick();self.assertFalse(c.active)
 async def test_failed_journal_does_not_prevent_emergency_stop(self):
  c=self.c();await c.start('pv',500,3)
  async def fail(kind,data):raise RuntimeError('disk full')
  c.event=fail
  # Device boundary still executes even though intent could not be persisted.
  async def physical(e,v):
   self.calls.append((e,v));self.states[e]=str(v);self.now+=1;self.sample_stamp=self.now
   if e=='switch.inverter_export_surplus' and v=='off':self.states['sensor.inverter_grid_power']='20'
  c.write=physical
  await c.stop()
  self.assertEqual(self.states['switch.inverter_export_surplus'],'off')
 async def test_tick_during_start_does_not_cancel_current_transaction(self):
  c=self.c();real=c.write
  async def yielding(e,v):
   await real(e,v);await c.tick()
  c.write=yielding
  await c.start('battery',500,3)
  self.assertTrue(c.active)
 async def test_failed_cap_stop_still_attempts_mode_and_export_off(self):
  c=self.c();await c.start('pv',500,3);real=c.write
  async def fail_cap(e,v):
   if e=='number.inverter_export_surplus_power' and v==0:raise RuntimeError('cap offline')
   await real(e,v)
  c.write=fail_cap;await c.stop()
  self.assertIn(('switch.inverter_export_surplus','off'),self.calls)
  self.assertEqual(self.states['switch.inverter_export_surplus'],'off')
 async def test_stale_prestart_export_is_not_sale_confirmation(self):
  self.states['sensor.inverter_grid_power']='-70'
  c=self.c();await c.start('pv',500,3);await c.tick()
  self.assertFalse(c.observed)

if __name__=='__main__':unittest.main()

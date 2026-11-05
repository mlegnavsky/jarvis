import unittest,sys,copy
sys.path.insert(0,'managed_sources/spot_control')
from engine import Controller,plan,CURRENT,SWITCH
class Tests(unittest.IsolatedAsyncioTestCase):
 def setUp(self):
  self.s={'select.inverter_work_mode':'Zero Export To CT','switch.inverter_export_surplus':'off','select.inverter_time_of_use':'Week','sensor.inverter_battery':'44',CURRENT:'40',SWITCH:'on','sensor.inverter_battery_temperature':'13.5','number.inverter_battery_max_charging_current':'100'}
  for i,h in enumerate([1,5,9,13,17,21],1):self.s.update({f'time.inverter_program_{i}_time':f'{h:02}:00:00',f'select.inverter_program_{i}_charging':'Disabled',f'number.inverter_program_{i}_soc':'30'})
  self.before=copy.deepcopy(self.s);self.saved={};self.calls=[]
 async def save(self,r):self.saved=copy.deepcopy(r)
 async def write(self,e,v):
  assert self.saved.get('before');self.calls.append((e,v));self.s[e]=v
 def controller(self,saved=None):return Controller(lambda:self.s,self.write,self.save,saved,clock=lambda:100)
 async def test_start_stop_exact(self):
  c=self.controller();await c.start(16*60);self.assertEqual(float(self.s[CURRENT]),100);self.assertEqual(c.record['slot'],4)
  await c.stop();self.assertEqual(self.s,self.before);self.assertFalse(c.active)
 async def test_restart_restore(self):
  await self.controller().start(960);c=self.controller(self.saved);await c.stop();self.assertEqual(self.s,self.before)
 async def test_partial_failure_rollback(self):
  c=self.controller();original=c.write
  async def failing(e,v):
   if v=='Grid':raise RuntimeError('offline')
   await original(e,v)
  c.write=failing
  with self.assertRaises(RuntimeError):await c.start(960)
  self.assertEqual(self.s,self.before)
 async def test_no_write_if_snapshot_fails(self):
  c=self.controller()
  async def fail(r):raise RuntimeError('disk')
  c.save=fail
  with self.assertRaises(RuntimeError):await c.start(960)
  self.assertEqual(self.calls,[])
 async def test_guards_and_repeated_start(self):
  c=self.controller();self.s['switch.inverter_export_surplus']='on'
  with self.assertRaises(ValueError):await c.start(960)
  self.assertFalse(self.calls);self.s['switch.inverter_export_surplus']='off';await c.start(960)
  with self.assertRaises(ValueError):await c.start(960)
  await c.tick(False);self.assertEqual(self.s,self.before)
 async def test_retry_failed_restore(self):
  c=self.controller();await c.start(960);original=c.write
  async def fail(e,v):raise RuntimeError('offline')
  c.write=fail;await c.stop();self.assertTrue(c.active)
  c.write=original;await c.stop();self.assertFalse(c.active)
 async def test_restore_disable_failure_keeps_safe_current(self):
  c=self.controller();await c.start(960);original=c.write
  async def fail(e,v):
   if e.startswith('select.') and v=='Disabled':raise RuntimeError('offline')
   await original(e,v)
  c.write=fail;await c.stop();self.assertEqual(float(self.s[CURRENT]),100);self.assertTrue(c.active)
 async def test_stop_attempts_hardware_despite_save_failure(self):
  c=self.controller();await c.start(960)
  async def fail(r):raise RuntimeError('disk')
  c.save=fail;await c.stop();self.assertEqual(self.s,self.before);self.assertTrue(c.active)
 async def test_guard_rechecked_between_writes(self):
  c=self.controller();original=c.write
  async def mutate(e,v):
   await original(e,v);c.healthy=lambda:False
  c.write=mutate
  with self.assertRaises(ValueError):await c.start(960)
  self.assertNotIn('Grid',[v for e,v in self.calls])
 async def test_deadline_and_target(self):
  c=self.controller();await c.start(960);c.clock=lambda:701;await c.tick();self.assertFalse(c.active)
 async def test_temperature_stops_and_restores(self):
  c=self.controller();await c.start(960);self.s['sensor.inverter_battery_temperature']='45'
  await c.tick();self.assertFalse(c.active);self.assertEqual(self.s[CURRENT],self.before[CURRENT])
 def test_button_requests_100_from_previous_settings(self):
  for previous in ('20','40','80','100'):
   with self.subTest(previous=previous):
    self.s[CURRENT]=previous
    self.assertEqual(float(plan(self.s,960)[0][0][1]),100)
 def test_charge_bounds(self):
  self.s['number.inverter_battery_max_charging_current']='25'
  self.assertEqual(float(plan(self.s,960)[0][0][1]),25)
  self.s['sensor.inverter_battery_temperature']='unavailable'
  with self.assertRaises(ValueError):plan(self.s,960)
 def test_midnight_and_bad_time(self):
  self.assertEqual(plan(self.s,0)[2],6)
  self.s['time.inverter_program_2_time']='bad'
  with self.assertRaises(ValueError):plan(self.s,0)
if __name__=='__main__':unittest.main()

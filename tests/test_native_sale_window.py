"""A hardware clock boundary must stop export without any HA boundary write."""
import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo
import unittest
from native_window import NativeWindow

class NativeWindowTests(unittest.IsolatedAsyncioTestCase):
 async def asyncSetUp(self):
  self.now=datetime(2026,11,5,15,40,tzinfo=ZoneInfo('Europe/Prague')).timestamp()
  self.reg={0:0x0500,98:1,109:175,111:1,130:0,142:2,143:9300,145:0,146:255,219:200}
  self.reg.update({148+i:t for i,t in enumerate((0,400,800,1200,1600,2000))})
  for i in range(6):self.reg.update({154+i:12000,166+i:30,172+i:0})
  self.original=dict(self.reg);self.writes=[];self.events=[];self.saved={}
  self.states={'soc':98,'grid_w':10,'pv_w':100,'battery_w':-50,'reported_at':self.now,'healthy':True,'net_price':8}
  async def read():
   d=datetime.fromtimestamp(self.now,ZoneInfo('Europe/Prague'))
   return {'clock':d,'registers':dict(self.reg)}
  async def write(address,value):self.writes.append((address,value));self.reg[address]=value
  async def save(record):self.saved=record
  async def event(kind,payload):self.events.append((kind,payload))
  self.window=NativeWindow(read,write,lambda:dict(self.states),save,event,clock=lambda:self.now)
 async def advance(self,seconds,**values):
  self.now+=seconds;self.states.update(reported_at=self.now,**values);await self.window.tick()
 async def test_arm_changes_only_one_future_sell_slot_and_keeps_house_slots(self):
  await self.window.start()
  self.assertTrue(self.window.active);self.assertEqual(self.reg[142],2);self.assertEqual(self.reg[145],0)
  self.assertEqual(self.reg[143],500);self.assertEqual(self.reg[109],20)
  self.assertEqual([self.reg[172+i] for i in range(6)],[0,32,0,0,0,0])
  self.assertEqual([self.reg[166+i] for i in range(6)],[30,95,30,30,30,30])
  self.assertEqual(self.writes[-1],(173,32));self.assertEqual(self.reg[146],255)
 async def test_legacy_lv_device_code_in_active_profile_can_be_commissioned(self):
  self.reg[0]=5
  await self.window.start()
  self.assertEqual(self.reg[173],32)
 async def test_solar_sell_variant_protects_all_slots_and_enables_only_inside_window(self):
  await self.window.start(solar_sell=True)
  self.assertEqual([self.reg[166+i] for i in range(6)],[95]*6)
  self.assertEqual(self.reg[145],0)
  self.now=self.window.record['start'];await self.advance(1)
  self.assertEqual(self.reg[145],1)
  self.assertFalse(self.window.record['observed'])
  self.assertTrue(self.window.record['solar_sell'])
 async def test_no_export_cannot_be_misreported_as_verified_native_expiry(self):
  await self.window.start();self.now=self.window.record['end']
  await self.advance(5,grid_w=10,battery_w=110)
  self.assertFalse(self.window.record['native_expiry_observed'])
 async def test_failed_guard_reason_survives_later_cleanup_retry(self):
  await self.window.start();self.states['healthy']=False
  await self.advance(1)
  self.assertTrue(self.window.active)
  self.states['healthy']=True;await self.advance(5,grid_w=10)
  proof=[p for k,p in self.events if k=='native_window_stop'][-1]
  self.assertEqual(proof['reason'],'guard')
 async def test_delayed_enable_intent_cannot_start_solar_sell_after_window(self):
  await self.window.start(solar_sell=True);event=self.window.event
  async def delayed(kind,payload):
   if kind=='native_window_write_intent' and payload.get('address')==145 and payload.get('value')==1:
    self.now=self.window.record['end']+1;self.states['reported_at']=self.now
   await event(kind,payload)
  self.window.event=delayed
  self.now=self.window.record['start']
  await self.advance(1)
  self.assertNotIn((145,1),self.writes)
 async def test_native_expiry_is_observed_before_any_stop_write(self):
  await self.window.start();record=dict(self.window.record);arm_count=len(self.writes)
  self.now=record['start']
  for _ in range(5):await self.advance(5,grid_w=-450,battery_w=500,pv_w=100)
  self.assertEqual(len(self.writes),arm_count)
  self.now=record['end']-30
  for _ in range(5):await self.advance(5,grid_w=-450,battery_w=500,pv_w=100)
  self.now=record['end'];await self.advance(5,grid_w=10,battery_w=-50)
  self.assertTrue(self.window.record['native_expiry_observed']);self.assertEqual(len(self.writes),arm_count)
  await self.advance(20,grid_w=10)
  self.assertTrue(self.window.active)
  await self.advance(5,grid_w=10)
  self.assertFalse(self.window.active)
  self.assertEqual(self.reg,self.original)
  proof=[p for k,p in self.events if k=='native_window_stop'][-1]
  self.assertTrue(proof['observed']);self.assertTrue(proof['native_expiry_observed'])
  self.assertFalse(proof['production_verified'])
 async def test_export_ending_minutes_early_cannot_prove_clock_expiry(self):
  await self.window.start(solar_sell=True);self.now=self.window.record['start'];await self.advance(1)
  for _ in range(5):await self.advance(5,grid_w=-450,battery_w=500,pv_w=100)
  self.assertTrue(self.window.record['observed'])
  for _ in range(50):await self.advance(5,grid_w=10,battery_w=-50)
  self.now=self.window.record['end'];await self.advance(1,grid_w=10)
  self.assertFalse(self.window.record['native_expiry_observed'])
 async def test_old_or_skewed_native_clock_cannot_arm_export(self):
  self.window.native_read=lambda:asyncio.sleep(0,result={'clock':datetime.fromtimestamp(self.now-60,ZoneInfo('Europe/Prague')),'registers':self.reg})
  with self.assertRaises(ValueError):await self.window.start()
  self.assertEqual(self.writes,[])
 async def test_alarm_at_preflight_cannot_change_any_register(self):
  self.states['healthy']=False
  with self.assertRaises(ValueError):await self.window.start()
  self.assertEqual(self.writes,[])
 async def test_charging_starting_during_native_read_cannot_overlap_first_write(self):
  read=self.window.native_read
  async def charging_race():
   result=await read();self.states['healthy']=False;return result
  self.window.native_read=charging_race
  with self.assertRaises(ValueError):await self.window.start()
  self.assertEqual(self.writes,[])
 async def test_slow_audit_cannot_arm_a_window_or_command_that_expired(self):
  event=self.window.event
  async def slow_event(kind,payload):
   if kind=='native_window_write_intent' and payload.get('address')==173 and payload.get('value')==32:
    self.now=self.window.record['end']+1;self.states['reported_at']=self.now
   await event(kind,payload)
  self.window.event=slow_event
  with self.assertRaises(ValueError):await self.window.start(valid_until=self.now+120)
  self.assertNotIn((173,32),self.writes)
 async def test_restart_cleanup_removes_sell_even_if_cap_write_fails(self):
  await self.window.start();record=dict(self.window.record)
  original=self.window.native_write
  async def fail_cap(address,value):
   if address==143:raise OSError('offline register')
   await original(address,value)
  self.window.native_write=fail_cap
  await self.window.stop('recovery')
  self.assertTrue(self.window.active)
  self.assertTrue(all(self.reg[172+i]==0 for i in range(6)))
  self.assertEqual(self.reg[145],0)
  self.assertEqual(record['before']['109'],175)

if __name__=='__main__':unittest.main()

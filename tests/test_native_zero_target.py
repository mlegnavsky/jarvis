"""The requested1W grid bias needs delayed native proof, never HA optimism."""
import asyncio
import unittest
try:from native_zero_target import set_zero_target
except ImportError:set_zero_target=None

class Device:
 def __init__(self,ignore=False):
  self.modbus=self;self._semaphore=asyncio.Lock();self.ignore=ignore;self.calls=[]
  self.r={0:5,98:1,111:1,130:0,142:2,145:0,146:255,104:20}
  for i in range(6):self.r.update({166+i:30,172+i:0})
 async def get_response(self,code,address,count=1,data=None):
  assert self._semaphore.locked();self.calls.append((code,address,data))
  if code==16:
   if not self.ignore:self.r[address]=data[0]
   return data
  return [self.r.get(address+i,0) for i in range(count)]
 async def execute(self,code,address,count=1):
  assert not self._semaphore.locked();self.calls.append((code,address,None))
  return [self.r.get(address+i,0) for i in range(count)]

class ZeroTargetTests(unittest.IsolatedAsyncioTestCase):
 async def run_probe(self,device=None,ready=None,event=None):
  self.assertIsNotNone(set_zero_target)
  device=device or Device();self.events=[]
  async def audit(kind,payload):self.events.append((kind,payload))
  async def sleep(seconds):await asyncio.sleep(0)
  result=await set_zero_target(device,ready or (lambda:True),event or audit,sleep=sleep)
  return device,result
 async def test_one_watt_is_the_only_write_and_delayed_reads_prove_it(self):
  d,r=await self.run_probe()
  self.assertTrue(r['verified']);self.assertEqual(r['before_w'],20);self.assertEqual(r['actual_w'],1)
  self.assertEqual([c for c in d.calls if c[0]==16],[(16,104,[1])])
  self.assertGreaterEqual(sum(c[0]==3 and c[1]==104 for c in d.calls),3)
 async def test_ignored_write_reports_actual_twenty_without_fake_success(self):
  _,r=await self.run_probe(Device(ignore=True))
  self.assertFalse(r['verified']);self.assertEqual(r['actual_w'],20)
 async def test_single_read_echo_cannot_hide_disagreeing_bulk_read(self):
  class ShapeDependent(Device):
   async def get_response(self,code,address,count=1,data=None):
    result=await super().get_response(code,address,count,data)
    if code==3 and address==98 and count==14:result[6]=20
    return result
  _,r=await self.run_probe(ShapeDependent())
  self.assertFalse(r['verified']);self.assertEqual(r['actual_w'],20)
  self.assertTrue(any(p['single_before']==1 and p['bulk']==20 and p['single_after']==1 for p in r['read_shapes']))
 async def test_active_unhealthy_or_changed_native_program_never_writes(self):
  for change in ({142:0},{145:1},{130:1},{166:60},{172:1},{0:6}):
   d=Device();d.r.update(change);_,r=await self.run_probe(d)
   self.assertFalse(r['verified']);self.assertFalse(any(c[0]==16 for c in d.calls))
  d,r=await self.run_probe(ready=lambda:False)
  self.assertFalse(r['verified']);self.assertFalse(any(c[0]==16 for c in d.calls))
 async def test_owner_change_during_awaited_audit_prevents_write(self):
  d=Device()
  async def event(kind,payload):d.r[142]=0
  _,r=await self.run_probe(d,event=event)
  self.assertFalse(r['verified']);self.assertFalse(any(c[0]==16 for c in d.calls))
 async def test_audit_failure_prevents_write(self):
  async def event(kind,payload):raise OSError('history unavailable')
  d,r=await self.run_probe(event=event)
  self.assertFalse(r['verified']);self.assertFalse(any(c[0]==16 for c in d.calls))
 async def test_unsupported_transport_never_falls_back_to_unverified_write(self):
  _,r=await self.run_probe(object())
  self.assertFalse(r['verified']);self.assertFalse(r['supported'])

import asyncio
import types
import unittest
try:from native_snapshot import read_snapshot
except ImportError:read_snapshot=None

class NativeSnapshotTests(unittest.IsolatedAsyncioTestCase):
 async def test_six_read_chunks_hold_one_transport_lock_without_poll_interleaving(self):
  self.assertIsNotNone(read_snapshot)
  lock=asyncio.Semaphore(1);calls=[];polls=[]
  async def poll():
   async with lock:calls.append('poll')
  async def response(code,address,count):
   self.assertTrue(lock.locked());self.assertEqual(code,3);calls.append(address)
   if address==98:polls.append(asyncio.create_task(poll()))
   await asyncio.sleep(0)
   clock={62:(26<<8)|11,63:(6<<8)|8,64:(45<<8)|10}
   return [clock.get(i,0) for i in range(address,address+count)]
  device=types.SimpleNamespace(modbus=types.SimpleNamespace(_semaphore=lock,get_response=response))
  result=await read_snapshot(device);await asyncio.gather(*polls)
  self.assertEqual(calls,[0,98,130,142,212,62,'poll'])
  self.assertEqual(result['clock'].isoformat(),'2026-11-06T08:45:10+01:00')
  self.assertEqual(len(result['registers']),63)
  self.assertFalse(lock.locked())

 async def test_timeout_names_read_stage_and_releases_transport(self):
  self.assertIsNotNone(read_snapshot)
  lock=asyncio.Semaphore(1)
  async def response(code,address,count):
   if address==98:await asyncio.Event().wait()
   return [0]*count
  device=types.SimpleNamespace(modbus=types.SimpleNamespace(_semaphore=lock,get_response=response))
  with self.assertRaisesRegex(TimeoutError,'98/14'):await read_snapshot(device,timeout_seconds=.01)
  self.assertFalse(lock.locked())

 async def test_bad_or_incomplete_register_values_never_form_a_snapshot(self):
  self.assertIsNotNone(read_snapshot)
  lock=asyncio.Semaphore(1)
  async def response(code,address,count):return [True]*count
  device=types.SimpleNamespace(modbus=types.SimpleNamespace(_semaphore=lock,get_response=response))
  with self.assertRaises(ValueError):await read_snapshot(device)
  self.assertFalse(lock.locked())

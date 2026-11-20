import asyncio
import unittest
from background_learning import BackgroundLearning

class LearningTests(unittest.IsolatedAsyncioTestCase):
 async def test_bound_and_shutdown_release_pending_audio_without_blocking(self):
  begun=asyncio.Event();release=asyncio.Event()
  async def infer(pcm):begun.set();await release.wait();return {'status':'ok'}
  async def executor(fn,*args):return fn(*args)
  worker=BackgroundLearning(infer,executor,lambda *a:True,limit=2)
  for n in range(3):
   item={'learning_pcm':bytes(100),'voiced':4,'text':'private sentence','utterance':str(n),'playback':False}
   worker.submit(item,'c');self.assertNotIn('learning_pcm',item)
  self.assertEqual(worker.snapshot()['pending'],2)
  self.assertEqual(worker.snapshot()['dropped'],1)
  await begun.wait();await worker.shutdown()
  self.assertEqual(worker.snapshot()['pending'],0)
  self.assertEqual(worker.snapshot()['cancelled'],2)
  self.assertNotIn('private',str(worker.snapshot()))
 async def test_timeout_and_failure_are_observed_and_do_not_escape(self):
  async def infer(pcm):await asyncio.Event().wait()
  async def executor(fn,*args):return fn(*args)
  worker=BackgroundLearning(infer,executor,lambda *a:True,timeout=.01)
  worker.submit({'learning_pcm':b'pcm'},'c')
  await asyncio.gather(*worker.tasks)
  self.assertEqual(worker.snapshot()['failed'],1)
  self.assertEqual(worker.snapshot()['last_error'],'TimeoutError')
 async def test_running_collector_keeps_slot_until_shutdown_really_drains(self):
  import threading
  begun=threading.Event();release=threading.Event();writes=[]
  async def infer(pcm):return {'status':'ok'}
  async def executor(fn,*args):return await asyncio.to_thread(fn,*args)
  def collect(*args):begun.set();release.wait();writes.append('finished')
  worker=BackgroundLearning(infer,executor,collect,timeout=.01)
  worker.submit({'learning_pcm':b'pcm'},'c')
  try:
   await asyncio.wait_for(asyncio.to_thread(begun.wait),1)
   await asyncio.sleep(.03)
   self.assertEqual(worker.snapshot()['pending'],1)
   stopping=asyncio.create_task(worker.shutdown());await asyncio.sleep(.02)
   self.assertFalse(stopping.done())
  finally:
   release.set();await worker.shutdown()
  self.assertEqual(worker.snapshot()['pending'],0)
  self.assertEqual(writes,['finished'])
  count=len(writes);await asyncio.sleep(.02);self.assertEqual(len(writes),count)
 async def test_native_future_executor_is_owned_and_drained(self):
  import threading
  begun=threading.Event();release=threading.Event();writes=[]
  async def infer(pcm):return {'status':'ok'}
  def executor(fn,*args):return asyncio.get_running_loop().run_in_executor(None,fn,*args)
  def collect(*args):begun.set();release.wait();writes.append('finished')
  worker=BackgroundLearning(infer,executor,collect)
  worker.submit({'learning_pcm':b'pcm'},'c')
  try:
   await asyncio.wait_for(asyncio.to_thread(begun.wait),1)
   await asyncio.sleep(.02)
   self.assertEqual(worker.snapshot()['pending'],1)
   self.assertEqual(worker.snapshot()['failed'],0)
   stopping=asyncio.create_task(worker.shutdown());await asyncio.sleep(.02)
   self.assertFalse(stopping.done())
  finally:
   release.set();await worker.shutdown()
  self.assertEqual(writes,['finished'])
  self.assertTrue(worker.snapshot()['drained'])

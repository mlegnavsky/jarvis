import unittest
from tv_session import TVSession

class TVSessionTests(unittest.IsolatedAsyncioTestCase):
 def session(self,state='playing',confirm=True,fail=False):
  self.state={'state':state,'attributes':{'media_title':'Film','app_id':'tv'}}
  self.calls=[]
  async def call(service):
   self.calls.append(service)
   if fail:raise RuntimeError('offline')
   if confirm:self.state['state']='paused' if service=='media_pause' else 'playing'
  return TVSession(lambda:self.state,call)
 async def test_prepaused_never_resumed(self):
  session=self.session('paused');await session.acquire();await session.release()
  self.assertEqual(self.calls,[])
 async def test_success_resumes_only_owned_pause(self):
  session=self.session();await session.acquire();self.assertTrue(session.snapshot()['owned'])
  await session.release();self.assertEqual(self.calls,['media_pause','media_play'])
 async def test_content_change_discards_ownership(self):
  session=self.session();await session.acquire();self.state['attributes']['media_title']='Other'
  await session.release();self.assertEqual(self.calls,['media_pause'])
 async def test_failed_pause_never_owned(self):
  session=self.session(fail=True);await session.acquire();await session.release()
  self.assertFalse(session.snapshot()['owned']);self.assertEqual(self.calls,['media_pause'])
 async def test_unconfirmed_pause_never_owned(self):
  session=self.session(confirm=False);await session.acquire();await session.release()
  self.assertFalse(session.snapshot()['owned']);self.assertEqual(self.calls,['media_pause'])
 async def test_double_release_is_consumed(self):
  session=self.session();await session.acquire();await session.release();await session.release()
  self.assertEqual(self.calls,['media_pause','media_play'])
 async def test_sequential_acquire_keeps_same_lease(self):
  session=self.session();await session.acquire();await session.acquire();await session.release()
  self.assertEqual(self.calls,['media_pause','media_play'])
 async def test_external_play_discards_ownership(self):
  session=self.session();await session.acquire();self.state['state']='playing';session.observe(self.state)
  self.state['state']='paused';await session.release();self.assertEqual(self.calls,['media_pause'])
 async def test_off_idle_unavailable_do_not_pause(self):
  for state in ('off','idle','unavailable','unknown'):
   session=self.session(state);await session.acquire();await session.release();self.assertEqual(self.calls,[])
 async def test_release_predicate_is_checked_after_waiting_for_lock(self):
  import asyncio
  session=self.session();await session.acquire();current=True
  await session._lock.acquire()
  task=asyncio.create_task(session.release(if_current=lambda:current))
  await asyncio.sleep(0);current=False;session._lock.release();await task
  self.assertTrue(session.snapshot()['owned']);self.assertEqual(self.calls,['media_pause'])
 async def test_unconfirmed_resume_is_not_counted_as_resumed(self):
  session=self.session();await session.acquire()
  async def accepted_only(service):self.calls.append(service)
  session.call_service=accepted_only
  await session.release()
  self.assertEqual(session.snapshot()['resumed'],0)
  self.assertEqual(session.snapshot()['resume_requested'],1)
  self.assertEqual(session.snapshot()['last_error'],'resume_TimeoutError')

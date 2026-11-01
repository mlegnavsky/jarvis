import asyncio
from types import SimpleNamespace as NS
import unittest
from routing import Router
from interrupt import install_abort_resume


class InterruptTests(unittest.IsolatedAsyncioTestCase):
 async def exercise(self, *, continuation=True, stop_fails=False, replace=False,
                    allowed=True, abort=True, change_conversation=False, prebound=False, layered=False, foreign_callback=False):
  began=asyncio.Event();resumed=[];stopped=[]
  async def play(media):began.set();await asyncio.Event().wait()
  async def stop():
   if stop_fails:raise OSError('stop unavailable')
   stopped.append(True)
  router=Router(play,stop)
  hass=NS(async_create_task=asyncio.create_task)
  run=NS(id='run',_jarvis_tv_continue=continuation)
  router.latest='run'
  terminal=NS()
  class Terminal:
   async def handle_pipeline_stop(self,abort):
    if abort:self._abort_pipeline()
   def _abort_pipeline(self):self._pipeline_task.cancel()
   def event_callback(self,event):pass
   def tts_response_finished(self):self.finished=True
  terminal=Terminal();terminal.hass=hass;terminal.entity_id='satellite'
  terminal._conversation_id='conversation';terminal._is_announcing=False
  terminal.finished=False
  run.event_callback=(Terminal() if foreign_callback else terminal).event_callback
  subscribed_stop=terminal.handle_pipeline_stop if prebound else None
  async def resume(entity,pending):resumed.append((entity._conversation_id,pending['conversation_id']))
  pending={'run_id':'run','conversation_id':'conversation','seconds':3}
  controller=NS(pending=pending)
  gate=install_abort_resume(hass,Terminal,router,'2026.6.4','satellite',
                           lambda entity:allowed,resume,lambda:controller.pending)
  async def output():
   router.begin(run)
   try:await router.answer(run,{'media_id':'speech'})
   finally:router.end(run)
  task=asyncio.create_task(output())
  async def outer():await task
  wrapper=asyncio.create_task(outer()) if layered else task
  terminal._pipeline_task=wrapper
  await began.wait()
  await (subscribed_stop or terminal.handle_pipeline_stop)(abort)
  if replace:router.activate('replacement')
  if change_conversation:terminal._conversation_id='new-conversation'
  if not abort:task.cancel()
  try:await wrapper
  except asyncio.CancelledError:pass
  terminal._pipeline_task=None
  for _ in range(5):await asyncio.sleep(0)
  if gate.jobs:await asyncio.gather(*list(gate.jobs.values()),return_exceptions=True)
  gate.test_finished=terminal.finished
  return resumed,stopped,gate

 async def test_distinct_native_and_output_tasks_recover_and_finish_response(self):
  resumed,stopped,gate=await self.exercise(layered=True)
  self.assertEqual(resumed,[('conversation','conversation')])
  self.assertTrue(gate.test_finished)
 async def test_cancelled_final_reply_is_cleaned_without_reopening(self):
  resumed,stopped,gate=await self.exercise(continuation=False,layered=True)
  self.assertEqual(resumed,[])
  self.assertTrue(gate.test_finished)
 async def test_muting_blocks_listening_but_still_cleans_cancelled_response(self):
  resumed,stopped,gate=await self.exercise(allowed=False,layered=True)
  self.assertEqual(resumed,[])
  self.assertTrue(gate.test_finished)
 async def test_unrelated_callback_never_cleans_another_entity(self):
  resumed,stopped,gate=await self.exercise(foreign_callback=True)
  self.assertFalse(resumed);self.assertFalse(gate.test_finished)
 async def test_stop_callback_bound_before_install_still_resumes(self):
  resumed,stopped,gate=await self.exercise(prebound=True)
  self.assertEqual(stopped,[True])
  self.assertEqual(resumed,[('conversation','conversation')])
 async def test_device_abort_stops_audio_then_resumes_same_conversation_once(self):
  resumed,stopped,gate=await self.exercise()
  self.assertEqual(stopped,[True]);self.assertEqual(resumed,[('conversation','conversation')])
  self.assertEqual(gate.resumed,1)
 async def test_explicit_end_never_resumes(self):
  resumed,_,_=await self.exercise(continuation=False);self.assertEqual(resumed,[])
 async def test_failed_stop_never_opens_microphone(self):
  resumed,_,_=await self.exercise(stop_fails=True);self.assertEqual(resumed,[])
 async def test_new_activation_suppresses_late_resume(self):
  resumed,_,_=await self.exercise(replace=True);self.assertEqual(resumed,[])
 async def test_muted_or_stopping_device_never_resumes(self):
  resumed,_,_=await self.exercise(allowed=False);self.assertEqual(resumed,[])
 async def test_nonabort_and_changed_session_never_resume(self):
  for options in ({'abort':False},{'change_conversation':True}):
   resumed,_,_=await self.exercise(**options);self.assertEqual(resumed,[])


if __name__=='__main__':unittest.main()

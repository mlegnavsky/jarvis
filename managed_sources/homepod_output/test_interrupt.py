import asyncio
from types import SimpleNamespace as NS
import unittest
from routing import Router
from interrupt import install_abort_resume


class InterruptTests(unittest.IsolatedAsyncioTestCase):
 async def exercise(self, *, continuation=True, stop_fails=False, replace=False,
                    allowed=True, abort=True, change_conversation=False):
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
    if abort:self._pipeline_task.cancel()
  terminal=Terminal();terminal.hass=hass;terminal.entity_id='satellite'
  terminal._conversation_id='conversation';terminal._is_announcing=False
  async def resume(entity,pending):resumed.append((entity._conversation_id,pending['conversation_id']))
  pending={'run_id':'run','conversation_id':'conversation','seconds':3}
  controller=NS(pending=pending)
  gate=install_abort_resume(hass,Terminal,router,'2026.6.4','satellite',
                           lambda entity:allowed,resume,lambda:controller.pending)
  async def output():
   router.begin(run)
   try:await router.answer(run,{'media_id':'speech'})
   finally:router.end(run)
  task=asyncio.create_task(output());terminal._pipeline_task=task
  await began.wait()
  await terminal.handle_pipeline_stop(abort)
  if replace:router.activate('replacement')
  if change_conversation:terminal._conversation_id='new-conversation'
  if not abort:task.cancel()
  try:await task
  except asyncio.CancelledError:pass
  terminal._pipeline_task=None
  for _ in range(5):await asyncio.sleep(0)
  if gate.jobs:await asyncio.gather(*list(gate.jobs.values()),return_exceptions=True)
  return resumed,stopped,gate

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

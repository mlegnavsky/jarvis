import asyncio, sys, types, unittest
from types import SimpleNamespace as NS
from direct_wake import install
class Event:
 def __init__(self, type, data=None): self.type=type; self.data=data
class EventType:
 ERROR='error'
native=types.ModuleType('homeassistant.components.assist_pipeline.pipeline')
native.PipelineEvent=Event; native.PipelineEventType=EventType
sys.modules['homeassistant.components.assist_pipeline.pipeline']=native
class GuardTests(unittest.IsolatedAsyncioTestCase):
 def setup_input(self,phrase='rozsviť',sat='sat',pipe='pipe'):
  calls=[]; events=[]
  class Input:
   async def execute(self,validate=False): calls.append('delegated')
  hass=object()
  report=install(hass,Input,NS(STT='stt',INTENT='intent'),'2026.6.4','pipe','sat')
  run=NS(hass=hass,pipeline=NS(id=pipe),start_stage='stt',end_stage='intent',tts_stream=None)
  run.start=lambda **kwargs:events.append('run-start')
  run.process_event=lambda e:events.append(getattr(e.type,'value',e.type))
  async def end():events.append('run-end')
  run.end=end
  v=Input();v.run=run;v.wake_word_phrase=phrase;v.satellite_id=sat
  v.device_id='device';v.session=NS(conversation_id='conversation');v.intent_input=None;v.stt_stream=object()
  return v,calls,events,report
 async def test_unverified_light_wakes_never_reach_intent(self):
  for phrase in ('rozsviť','zhasni'):
   v,calls,events,r=self.setup_input(phrase);await v.execute()
   self.assertEqual(calls,[])
   self.assertEqual(events,['run-start','stt-vad-end','error','run-end'])
   self.assertEqual(r['blocked'],1);self.assertEqual(r['commands'],0)
 async def test_button_activation_and_other_devices_still_delegate(self):
  for phrase,sat,pipe in ((None,'sat','pipe'),('Hey Jarvis','sat','pipe'),('zhasni','other','pipe'),('zhasni','sat','other')):
   v,calls,events,r=self.setup_input(phrase,sat,pipe);await v.execute()
   self.assertEqual(calls,['delegated'])
 async def test_prepared_tts_is_cleaned_up(self):
  v,_,events,_=self.setup_input()
  v.run.tts_stream=NS(delete=lambda:events.append('tts-delete'))
  await v.execute()
  self.assertIsNone(v.run.tts_stream);self.assertIn('tts-delete',events)
if __name__=='__main__':unittest.main()

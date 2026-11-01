import asyncio, sys, types, unittest
from types import SimpleNamespace as NS
from unittest.mock import patch
from direct_wake import install

class Event:
 def __init__(self, type, data=None): self.type=type; self.data=data
class EventType:
 ERROR='error'
native=types.ModuleType('homeassistant.components.assist_pipeline.pipeline')
native.PipelineEvent=Event; native.PipelineEventType=EventType

class Speaker:
 enforce=True;public_controls=True;status='ready'
 def __init__(self):self.captures=[];self.training=False;self.results={}
 def training_active(self):return self.training
 async def complete(self,*args,**kwargs):
  self.captures.append((args,kwargs));self.results[args[0]]={'context_id':kwargs.get('context_id')}

class DirectTests(unittest.IsolatedAsyncioTestCase):
 def setup_input(self,phrase='rozsviť',sat='sat',pipe='pipe',speaker=True,clock=None,last=None):
  calls=[];events=[];coordinator=Speaker() if speaker else None
  class Input:
   async def execute(self,validate=False):
    calls.append((self.run.start_stage,self.intent_input,self.stt_stream,validate))
    if getattr(self,'before_start',None):await self.before_start()
    self.run.start(conversation_id=self.session.conversation_id,device_id=self.device_id,satellite_id=self.satellite_id)
    await self.run.end()
  async def executor(fn,*args):return fn(*args)
  hass=NS(data={'jarvis_speaker_identity':coordinator},async_add_executor_job=executor)
  report=install(hass,Input,NS(STT='stt',INTENT='intent'),'2026.6.4','pipe','sat',
     clock=clock or (lambda:10.),last_wakeups={} if last is None else last)
  class Run(NS):pass
  Run._jarvis_voice_intent_guard=True;Run._jarvis_speaker_adapter=coordinator
  run=Run(hass=hass,pipeline=NS(id=pipe),start_stage='stt',end_stage='tts',tts_stream=None,context=NS(id='context'))
  run.start=lambda **kwargs:events.append('run-start')
  run.process_event=lambda e:events.append(getattr(e.type,'value',e.type))
  async def end():events.append('run-end')
  run.end=end
  value=Input();value.run=run;value.wake_word_phrase=phrase;value.satellite_id=sat
  value.device_id='device';value.session=NS(conversation_id='conversation');value.intent_input=None;value.stt_stream=object()
  return value,calls,events,report,coordinator
 async def execute(self,value):
  with patch.dict(sys.modules,{'homeassistant.components.assist_pipeline.pipeline':native}):await value.execute(validate=True)
 async def test_public_light_wakes_use_native_intent_without_stt(self):
  for phrase in ('rozsviť','zhasni'):
   value,calls,events,report,speaker=self.setup_input(phrase)
   stream=value.stt_stream
   await self.execute(value)
   self.assertEqual(calls,[('intent',phrase,None,True)])
   self.assertEqual(events,['run-start','stt-vad-end','run-end'])
   self.assertEqual(speaker.captures,[(('sat',b'',0,phrase),{'context_id':'context'})])
   self.assertEqual(report['commands'],1)
   self.assertEqual(value.run.start_stage,'stt');self.assertIs(value.stt_stream,stream)
   self.assertIsNone(value.intent_input)
 async def test_not_ready_or_non_public_policy_never_reaches_intent(self):
  for mode in ('missing','guard_missing','private','training'):
   value,calls,events,report,speaker=self.setup_input(speaker=mode!='missing')
   if mode=='guard_missing':type(value.run)._jarvis_voice_intent_guard=False
   if mode=='private':speaker.public_controls=False
   if mode=='training':speaker.training=True
   await self.execute(value)
   self.assertEqual(calls,[]);self.assertEqual(events,['run-start','stt-vad-end','error','run-end'])
   self.assertEqual(report['blocked'],1)
 async def test_ordinary_activation_and_other_devices_delegate_unchanged(self):
  for phrase,sat,pipe in ((None,'sat','pipe'),('Hey Jarvis','sat','pipe'),('zhasni','other','pipe'),('zhasni','sat','other'),('odemkni','sat','pipe')):
   value,calls,events,report,speaker=self.setup_input(phrase,sat,pipe)
   stream=value.stt_stream;await self.execute(value)
   self.assertEqual(calls,[('stt',None,stream,True)])
   self.assertEqual(speaker.captures,[]);self.assertEqual(report['commands'],0)
 async def test_duplicate_wake_cooldown_does_not_repeat_action(self):
  now=[10.];last={}
  first,calls,_,report,_=self.setup_input(clock=lambda:now[0],last=last)
  await self.execute(first);await self.execute(first)
  self.assertEqual(len(calls),1);self.assertEqual(report['commands'],1)
  self.assertEqual(report['blocked'],1)
  now[0]=12.1;await self.execute(first)
  self.assertEqual(len(calls),2)
 async def test_blocked_run_cleans_prepared_tts(self):
  value,_,events,_,_=self.setup_input(speaker=False)
  value.run.tts_stream=NS(delete=lambda:events.append('tts-delete'))
  await self.execute(value)
  self.assertIsNone(value.run.tts_stream);self.assertIn('tts-delete',events)
 async def test_failed_handoff_closes_run_without_native_intent(self):
  value,calls,events,report,speaker=self.setup_input()
  async def fail(*a,**kw):raise RuntimeError('offline')
  speaker.complete=fail
  await self.execute(value)
  self.assertEqual(calls,[]);self.assertEqual(events[-1],'run-end')
  self.assertEqual(report['commands'],0);self.assertEqual(report['blocked'],1)
 async def test_identity_backend_outage_does_not_block_public_lights(self):
  value,calls,_,report,speaker=self.setup_input();speaker.status='backend_unavailable'
  await self.execute(value)
  self.assertEqual(calls,[('intent','rozsviť',None,True)])
 async def test_cancelled_preparation_closes_native_run(self):
  value,calls,events,_,speaker=self.setup_input();entered=asyncio.Event()
  async def blocked(*args):entered.set();await asyncio.Future()
  value.run.hass.async_add_executor_job=blocked
  task=asyncio.create_task(self.execute(value));await entered.wait();task.cancel()
  with self.assertRaises(asyncio.CancelledError):await task
  self.assertEqual(calls,[])
  self.assertEqual(events,['run-start','stt-vad-end','error','run-end'])
 async def test_cancelled_validation_discards_only_own_pending_context(self):
  for other in (False,True):
   value,calls,events,_,speaker=self.setup_input();entered=asyncio.Event()
   async def blocked():entered.set();await asyncio.Future()
   value.before_start=blocked
   task=asyncio.create_task(self.execute(value));await entered.wait()
   if other:speaker.results['sat']={'context_id':'other'}
   task.cancel()
   with self.assertRaises(asyncio.CancelledError):await task
   self.assertEqual(events,['run-start','stt-vad-end','error','run-end'])
   self.assertEqual('sat' in speaker.results,other)

if __name__=='__main__':unittest.main()

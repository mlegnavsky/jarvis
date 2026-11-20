import asyncio,sys,types,unittest,shutil,subprocess,tempfile
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch
from direct_wake import install

class Event:
 def __init__(self,type,data=None):self.type=type;self.data=data
class EventType:ERROR='error'
native=types.ModuleType('homeassistant.components.assist_pipeline.pipeline')
native.PipelineEvent=Event;native.PipelineEventType=EventType

class Tests(unittest.IsolatedAsyncioTestCase):
 async def test_direct_activation_has_bounded_reason_and_native_hint(self):
  state=self.setup(phrase='rozsviť',tv='playing');state.release.set()
  for _ in range(30):await self.execute(state)
  recent=state.report['recent_activations']
  self.assertEqual(len(recent),16)
  self.assertEqual(recent[-1]['wake_word'],'rozsviť')
  self.assertEqual(recent[-1]['reason'],'media-active-explicit-wake-required')
  self.assertEqual(recent[-1]['outcome'],'blocked')
  self.assertEqual(state.intents,[])
 @classmethod
 def setUpClass(cls):
  compiler=shutil.which('g++')
  if compiler:
   cls._native_dir=tempfile.TemporaryDirectory()
   cls.addClassCleanup(cls._native_dir.cleanup)
   cls._native_binary=Path(cls._native_dir.name)/'terminal'
   subprocess.run([compiler,'-std=c++17',str(Path(__file__).parent/'test_data/esphome_terminal_2026_10_1.cpp'),'-o',str(cls._native_binary)],check=True,capture_output=True)
  else:cls._native_binary=None
 async def test_suppressed_batch_releases_real_terminal_state(self):
  if self._native_binary is None:self.skipTest('g++ needed for pinned device protocol probe')
  for initial in ('START_PIPELINE','STARTING_PIPELINE','STREAMING_MICROPHONE'):
   state=self.setup(tv='on');await self.execute(state)
   result=subprocess.run([str(self._native_binary),initial],input='\n'.join(state.events)+'\n',text=True,capture_output=True,check=True)
   self.assertEqual(result.stdout.strip(),'IDLE',initial)
 async def test_suppression_does_not_advertise_an_unused_tts_stream(self):
  state=self.setup(tv='on');deleted=[];advertised=[]
  state.value.run.tts_stream=NS(delete=lambda:deleted.append(True))
  original=state.value.run.start
  def start(**kwargs):
   advertised.append(state.value.run.tts_stream is not None)
   original(**kwargs)
  state.value.run.start=start
  await self.execute(state)
  self.assertEqual(deleted,[True]);self.assertEqual(advertised,[False])
 def setup(self,phrase='zhasni',tv='off',sat='sat',pipe='pipe'):
  events=[];intents=[];entered=asyncio.Event();release=asyncio.Event()
  class Speaker:
   enforce=True;public_controls=True;results={}
   def training_active(self):return False
   async def complete(self,*args,**kwargs):raise AssertionError('never dispatch an acoustic hint before STT')
  speaker=Speaker()
  async def executor(fn,*args):return fn(*args)
  hass=NS(data={'jarvis_speaker_identity':speaker},async_add_executor_job=executor,states=NS(get=lambda entity:NS(state='on' if entity.startswith('input_boolean.jarvis_povel_') else tv if 'televize_obyvak' in entity else 'off')))
  class Run(NS):pass
  Run._jarvis_voice_intent_guard=True;Run._jarvis_speaker_adapter=speaker
  class Input:
   async def execute(value,validate=False):
    if getattr(value,'before_start',None):await value.before_start()
    value.run.start()
    try:
     entered.set();await release.wait()
     intents.append((value.run.start_stage,value.intent_input,value.stt_stream,getattr(value.run,'_jarvis_direct_command_prefix',None)))
    finally:await value.run.end()
  report=install(hass,Input,NS(STT='stt',INTENT='intent'),'2026.6.4','pipe','sat',clock=lambda:10.)
  run=Run(hass=hass,pipeline=NS(id=pipe),start_stage='stt',end_stage='tts',tts_stream=None,context=NS(id='context'))
  run.start=lambda **kwargs:events.append('run-start')
  run.process_event=lambda event:events.append(getattr(event.type,'value',event.type))
  async def end():events.append('run-end')
  run.end=end
  value=Input();value.run=run;value.wake_word_phrase=phrase;value.satellite_id=sat;value.device_id='device'
  value.session=NS(conversation_id='c');value.intent_input=None;value.stt_stream=object()
  return NS(value=value,hass=hass,speaker=speaker,events=events,intents=intents,entered=entered,release=release,report=report)
 async def execute(self,state):
  with patch.dict(sys.modules,{'homeassistant.components.assist_pipeline.pipeline':native}):await state.value.execute(validate=True)
 async def test_word_detection_listens_to_complete_native_stt_before_intent(self):
  state=self.setup();stream=state.value.stt_stream
  task=asyncio.create_task(self.execute(state));await asyncio.wait_for(state.entered.wait(),.5)
  self.assertEqual(state.intents,[]);self.assertNotIn('stt-vad-end',state.events)
  state.release.set();await task
  self.assertEqual(state.intents,[('stt',None,stream,'zhasni')])
  self.assertFalse(hasattr(state.value.run,'_jarvis_direct_command_prefix'))
 async def test_tv_on_suppresses_verbs_without_audio_or_error_reply(self):
  for tv in ('on','playing','buffering','unknown','unavailable'):
   state=self.setup(tv=tv);state.release.set();await self.execute(state)
   self.assertEqual(state.intents,[]);self.assertNotIn('error',state.events)
   self.assertEqual(state.events[-1],'run-end')
 async def test_explicit_jarvis_and_other_devices_delegate_even_when_tv_on(self):
  for phrase,sat,pipe in [('Jarvis','sat','pipe'),(None,'sat','pipe'),('zhasni','other','pipe'),('zhasni','sat','other')]:
   state=self.setup(phrase=phrase,tv='on',sat=sat,pipe=pipe);state.release.set();await self.execute(state)
   self.assertEqual(state.intents[0][3],None)
 async def test_duplicate_hint_does_not_reexecute(self):
  state=self.setup();state.release.set();await self.execute(state);await self.execute(state)
  self.assertEqual(len(state.intents),1)
 async def test_missing_native_guard_cannot_reach_intent(self):
  state=self.setup();type(state.value.run)._jarvis_voice_intent_guard=False;state.release.set()
  await self.execute(state);self.assertEqual(state.intents,[])
 async def test_cancelled_validation_closes_run_without_intent(self):
  state=self.setup();entered=asyncio.Event()
  async def blocked():entered.set();await asyncio.Future()
  state.value.before_start=blocked
  task=asyncio.create_task(self.execute(state));await entered.wait();task.cancel()
  with self.assertRaises(asyncio.CancelledError):await task
  self.assertEqual(state.intents,[]);self.assertEqual(state.events[-1],'run-end')

 async def test_disabled_or_missing_command_does_not_start_stt(self):
  for phrase in ('rozsviť','zhasni'):
   for value in ('off','unknown','unavailable',None):
    state=self.setup(phrase=phrase);old=state.hass.states.get
    state.hass.states.get=lambda entity: (None if value is None else NS(state=value)) if entity.startswith('input_boolean.jarvis_povel_') else old(entity)
    state.release.set();await self.execute(state)
    self.assertEqual(state.intents,[])
    self.assertEqual(state.report['last_blocked_reason'],'direct-command-disabled')
 async def test_switches_are_independent(self):
  state=self.setup(phrase='rozsviť');old=state.hass.states.get
  state.hass.states.get=lambda entity:NS(state='off') if entity.endswith('_zhasni') else old(entity)
  state.release.set();await self.execute(state)
  self.assertEqual(len(state.intents),1)

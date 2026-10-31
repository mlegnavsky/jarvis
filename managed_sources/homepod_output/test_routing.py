import asyncio
from dataclasses import dataclass
from types import SimpleNamespace as NS
import unittest
from routing import Router,install,SILENT_URL,OutputError,url_terminal_supported

@dataclass
class Event:
 type:str
 data:dict

class RoutingTests(unittest.IsolatedAsyncioTestCase):
 async def test_url_terminal_mode_rejects_api_speaker_only_firmware(self):
  self.assertTrue(url_terminal_supported(1))
  self.assertTrue(url_terminal_supported(5))
  self.assertFalse(url_terminal_supported(3))
  self.assertFalse(url_terminal_supported(0))
 def setup_route(self,play,stop=None):
  calls=[];hass=object()
  class Pipeline:
   def process_event(self,event):calls.append(event)
   async def text_to_speech(self,text,override_media_path=None):
    self.process_event(Event('tts-start',{'tts_input':text}))
    self.process_event(Event('tts-end',{'tts_output':{'media_id':'media-source://tts/private','token':'private-token','url':'/private-audio','mime_type':'audio/mpeg'}}))
  async def noop():pass
  router=Router(play,stop or noop)
  self.assertEqual(install(hass,Pipeline,router,'2026.6.4','pipeline','satellite'),'active')
  run=Pipeline();run.hass=hass;run.pipeline=NS(id='pipeline');run._satellite_id='satellite';run.id='actual-run'
  return router,run,calls
 async def test_homepod_completes_before_silent_satellite_end(self):
  began=asyncio.Event();finish=asyncio.Event()
  async def play(media):self.assertEqual(media,'media-source://tts/private');began.set();await finish.wait()
  router,run,calls=self.setup_route(play)
  task=asyncio.create_task(run.text_to_speech('Odpověď'))
  await began.wait()
  self.assertEqual([e.type for e in calls],['tts-start'])
  finish.set();await task
  self.assertEqual(calls[-1].data['tts_output']['url'],SILENT_URL)
  self.assertNotIn('private',str(calls[-1].data))
  self.assertEqual(router.completed,1)
 async def test_cancellation_stops_owned_homepod_audio(self):
  began=asyncio.Event();stopped=[]
  async def play(media):began.set();await asyncio.Event().wait()
  async def stop():stopped.append(True)
  router,run,calls=self.setup_route(play,stop)
  task=asyncio.create_task(run.text_to_speech('Odpověď'));await began.wait();task.cancel()
  with self.assertRaises(asyncio.CancelledError):await task
  self.assertEqual(stopped,[True]);self.assertEqual([e.type for e in calls],['tts-start'])
 async def test_unrelated_pipeline_and_synthetic_probe_never_route(self):
  played=[]
  async def play(media):played.append(media)
  router,run,calls=self.setup_route(play)
  run.pipeline.id='other';await run.text_to_speech('Jiný asistent')
  self.assertFalse(played);self.assertEqual(calls[-1].data['tts_output']['url'],'/private-audio')
  run.pipeline.id='pipeline';run.id='synthetic-probe-6-None'
  await run.text_to_speech('Zkouška');self.assertFalse(played)
 async def test_failure_does_not_fall_back_to_terminal_speech(self):
  async def play(media):raise ValueError('unavailable')
  router,run,calls=self.setup_route(play)
  with self.assertRaises(OutputError) as caught:await run.text_to_speech('Odpověď')
  self.assertEqual(caught.exception.code,'tts-failed')
  self.assertFalse(any(e.type=='tts-end' for e in calls))
 async def test_synthetic_streaming_hints_are_suppressed_only_for_routed_run(self):
  async def play(media):pass
  _,run,calls=self.setup_route(play)
  run.process_event(Event('intent-progress',{'tts_start_streaming':True}))
  self.assertFalse(calls)
  run.pipeline.id='other';run.process_event(Event('intent-progress',{'tts_start_streaming':True}))
  self.assertEqual(len(calls),1)
 async def test_new_activation_cancels_owned_answer_only(self):
  began=asyncio.Event();stopped=[]
  async def play(media):began.set();await asyncio.Event().wait()
  async def stop():stopped.append(True)
  router,run,calls=self.setup_route(play,stop)
  task=asyncio.create_task(run.text_to_speech('První odpověď'));await began.wait()
  other=type(run)();other.__dict__.update(run.__dict__);other.id='new-activation'
  other.process_event(Event('run-start',{'conversation_id':'new'}))
  await asyncio.sleep(0)
  self.assertTrue(task.cancelling(),'a new targeted activation must cancel the old answer')
  with self.assertRaises(asyncio.CancelledError):await task
  self.assertEqual(stopped,[True])
 async def test_unrelated_activation_preserves_answer(self):
  began=asyncio.Event();finish=asyncio.Event();stopped=[]
  async def play(media):began.set();await finish.wait()
  async def stop():stopped.append(True)
  router,run,calls=self.setup_route(play,stop)
  task=asyncio.create_task(run.text_to_speech('Odpověď'));await began.wait()
  other=type(run)();other.__dict__.update(run.__dict__);other.id='other';other.pipeline=NS(id='other')
  other.process_event(Event('run-start',{}));await asyncio.sleep(0)
  self.assertFalse(task.cancelling());finish.set();await task;self.assertFalse(stopped)
 async def test_new_activation_cancels_generation_before_any_playback(self):
  generated=asyncio.Event();finish_generation=asyncio.Event();played=[]
  async def play(media):played.append(media)
  router,run,calls=self.setup_route(play)
  # Pause the original Core TTS stage through its event boundary.
  # A controlled native TTS implementation is needed before adapter installation.
  hass=object()
  class Pipeline:
   def process_event(self,event):pass
   async def text_to_speech(self,text,override_media_path=None):
    generated.set();await finish_generation.wait()
    self.process_event(Event('tts-end',{'tts_output':{'media_id':'old'}}))
  self.assertEqual(install(hass,Pipeline,router,'2026.6.4','pipeline','satellite'),'active')
  a=Pipeline();a.hass=hass;a.pipeline=NS(id='pipeline');a._satellite_id='satellite';a.id='a'
  a.process_event(Event('run-start',{}))
  task=asyncio.create_task(a.text_to_speech('old'));await generated.wait()
  b=Pipeline();b.__dict__.update(a.__dict__);b.id='b';b.process_event(Event('run-start',{}))
  finish_generation.set()
  try:await task
  except asyncio.CancelledError:pass
  self.assertEqual(played,[],'obsolete TTS must never start playback')

class VolumeTests(unittest.IsolatedAsyncioTestCase):
 async def test_speech_sets_volume_before_streaming(self):
  import routing
  calls=[]
  class Player:
   async def async_set_volume_level(self,level):calls.append(('volume',level))
   async def async_play_media(self,kind,media):calls.append(('play',kind,media))
  play=getattr(routing,'play_at_volume',None)
  self.assertIsNotNone(play,'speech route must explicitly set its own volume')
  await play(Player(),'speech',.45,takeover_audio=lambda e:lambda:None)
  self.assertEqual(calls,[('volume',.45),('play','music','speech')])
 async def test_volume_failure_does_not_play_at_unknown_level(self):
  import routing
  calls=[]
  class Player:
   async def async_set_volume_level(self,level):raise RuntimeError('unavailable')
   async def async_play_media(self,*args):calls.append(args)
  play=getattr(routing,'play_at_volume',None)
  self.assertIsNotNone(play,'speech route must explicitly set its own volume')
  with self.assertRaises(RuntimeError):await play(Player(),'speech',.45,takeover_audio=lambda e:lambda:None)
  self.assertEqual(calls,[])

class RaopVolumeTests(unittest.IsolatedAsyncioTestCase):
 async def test_idle_companion_volume_timeout_is_avoided_by_raop_takeover(self):
  import routing
  from types import SimpleNamespace
  from unittest.mock import patch
  calls=[];active=False;protocol=object();interface=object()
  def takeover(p,i):
   nonlocal active
   self.assertIs(p,protocol);self.assertIs(i,interface);active=True;calls.append('takeover')
   def release():
    nonlocal active
    active=False;calls.append('release')
   return release
  class Player:
   atv=SimpleNamespace(takeover=takeover)
   async def async_set_volume_level(self,level):
    if not active:raise TimeoutError('idle Companion volume path')
    calls.append(('volume',level))
   async def async_play_media(self,kind,media):
    self_test.assertFalse(active,'RAOP stream owns its own takeover lifecycle')
    calls.append(('play',media))
  self_test=self
  with patch.dict('sys.modules',{'pyatv.const':SimpleNamespace(Protocol=SimpleNamespace(RAOP=protocol)), 'pyatv.interface':SimpleNamespace(Audio=interface)}):
   await routing.play_at_volume(Player(),'speech',.35)
  self.assertEqual(calls,['takeover',('volume',.35),'release',('play','speech')])

 async def test_failed_volume_releases_takeover_and_never_starts_audio(self):
  import routing
  released=[];played=[]
  class Player:
   async def async_set_volume_level(self,level):raise TimeoutError()
   async def async_play_media(self,*args):played.append(args)
  with self.assertRaises(TimeoutError):
   await routing.play_at_volume(Player(),'speech',.35,takeover_audio=lambda e:lambda:released.append(True))
  self.assertEqual(released,[True]);self.assertFalse(played)

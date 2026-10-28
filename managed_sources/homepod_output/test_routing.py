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

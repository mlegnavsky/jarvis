"""Composition audit: installed adapters together, with no audio/provider calls."""
import asyncio
from dataclasses import dataclass
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace as NS
import unittest

ROOT=Path(__file__).resolve().parents[1]/'managed_sources'
def module(name,path):
 spec=importlib.util.spec_from_file_location(name,ROOT/path)
 value=importlib.util.module_from_spec(spec);sys.modules[name]=value;spec.loader.exec_module(value);return value
turn=module('stack_turn','voice_diagnostics/turn_taking.py')
speaker=module('stack_speaker','speaker_identity/hooks.py')
output=module('stack_output','homepod_output/routing.py')

@dataclass
class Event:
 type:str
 data:dict
@dataclass
class Vad:
 silence_seconds:float=.7
 timeout_seconds:float=60
 in_command:bool=False
 before_command_speech_threshold:float=.6

class StackTests(unittest.IsolatedAsyncioTestCase):
 def stack(self,reverse=False):
  events=[];messages=[];captures=[];played=[];stopped=[];began=asyncio.Event();finish=asyncio.Event();hass=object()
  class Pipeline:
   def process_event(self,event):events.append(event)
   async def _speech_to_text_stream(self,audio_stream,stt_vad,sample_rate=16000,sample_width=2):
    async for chunk in audio_stream:
     stt_vad.in_command=True;yield chunk.audio
   async def speech_to_text(self,metadata,stream):
    async for _ in self._speech_to_text_stream(stream,Vad()):pass
    return 'Dnes zkouším hlasový rozhovor.'
   async def text_to_speech(self,tts_input,override_media_path=None):
    self.process_event(Event('tts-start',{'tts_input':tts_input}))
    self.tts_stream.async_set_message(tts_input)
    self.process_event(Event('tts-end',{'tts_output':{'media_id':self.tts_stream.media_source_id,
      'token':self.tts_stream.token,'url':self.tts_stream.url,'mime_type':self.tts_stream.content_type}}))
  class Coordinator:
   async def complete(self,*args):captures.append(args)
  async def play(media):played.append(media);began.set();await finish.wait()
  async def stop():stopped.append(True)
  router=output.Router(play,stop)
  control=turn.install(hass,Pipeline,Exception,'2026.6.4','p','s',lambda text:6)
  installers=[lambda:speaker.install(hass,Pipeline,Coordinator(),'2026.6.4','p','s'),
              lambda:output.install(hass,Pipeline,router,'2026.6.4','p','s')]
  for install in reversed(installers) if reverse else installers:self.assertEqual(install(),'active')
  run=Pipeline();run.hass=hass;run.pipeline=NS(id='p');run._satellite_id='s';run.id='real-shaped-run'
  run.tts_stream=NS(async_set_message=messages.append,media_source_id='media-source://tts/private',token='secret',url='/private',content_type='audio/wav')
  run._streamed_response_text=False
  run.process_event(Event('run-start',{'conversation_id':'c'}))
  return NS(run=run,events=events,messages=messages,captures=captures,played=played,stopped=stopped,begin=began,finish=finish,router=router,control=control)
 async def test_both_valid_setup_orders_preserve_mic_pronunciation_and_output(self):
  for reverse in (False,True):
   s=self.stack(reverse)
   async def audio():
    for _ in range(4):yield NS(audio=bytes(32000),speech_probability=.9)
   await s.run.speech_to_text(NS(sample_rate=16000),audio())
   self.assertEqual(len(s.captures),1);self.assertEqual(len(s.captures[0][1]),128000)
   task=asyncio.create_task(s.run.text_to_speech('Jmenuji se Jarvis.'));await s.begin.wait()
   self.assertEqual(s.messages,['Jmenuji se Džárvis.'])
   self.assertFalse(any(e.type=='tts-end' for e in s.events))
   s.finish.set();await task
   self.assertEqual(s.events[-1].data['tts_output']['url'],output.SILENT_URL)
   self.assertEqual(s.played,['media-source://tts/private'])
 async def test_cancel_clears_native_followup_and_stops_only_owned_output(self):
  s=self.stack()
  s.run.process_event(Event('intent-end',{'intent_output':{'continue_conversation':True,'conversation_id':'c','response':{'speech':{'plain':{'speech':'Co dál?'}}}}}))
  self.assertIsNotNone(s.control.pending)
  task=asyncio.create_task(s.run.text_to_speech('Odpověď'));await s.begin.wait();task.cancel()
  with self.assertRaises(asyncio.CancelledError):await task
  self.assertEqual(s.stopped,[True]);self.assertIsNone(s.control.pending)
  self.assertFalse(any(e.type=='tts-end' for e in s.events))
 async def test_synthetic_native_probe_has_no_homepod_side_effect(self):
  s=self.stack();s.run.id='synthetic-probe-audit'
  await s.run.text_to_speech('Jmenuji se Jarvis.')
  self.assertEqual(s.messages,['Jmenuji se Džárvis.']);self.assertFalse(s.played)

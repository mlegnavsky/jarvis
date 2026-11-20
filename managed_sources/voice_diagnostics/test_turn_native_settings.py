import unittest
from dataclasses import dataclass
from types import SimpleNamespace as NS
from turn_taking import install

@dataclass
class VAD:
 silence_seconds:float=.5
 timeout_seconds:float=15
 in_command:bool=False
 before_command_speech_threshold:float=.5

class NativeSettingsTests(unittest.IsolatedAsyncioTestCase):
 async def test_finished_speaking_setting_is_not_overridden(self):
  seen=[]
  class Pipeline:
   def process_event(self,event):pass
   async def speech_to_text(self,metadata,stream):pass
   async def text_to_speech(self,text,override_media_path=None):pass
   async def _speech_to_text_stream(self,audio_stream,stt_vad,sample_rate=16000,sample_width=2):
    seen.append(stt_vad)
    if False:yield None
  hass=object();controller=install(hass,Pipeline,Exception,'2026.6.4','pipeline','satellite',lambda text:3)
  run=Pipeline();run.hass=hass;run.pipeline=NS(id='pipeline');run._satellite_id='satellite';run.id='run'
  async def empty():
   if False:yield None
  async for _ in run._speech_to_text_stream(empty(),VAD()):pass
  self.assertEqual(seen[0].silence_seconds,.5)

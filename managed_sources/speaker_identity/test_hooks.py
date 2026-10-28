from types import SimpleNamespace as NS
import unittest
from hooks import install

class HookTests(unittest.IsolatedAsyncioTestCase):
 async def test_only_target_pipeline_collects_real_pcm_and_releases_buffer(self):
  calls=[];hass=object()
  class Pipeline:
   async def _speech_to_text_stream(self,audio_stream,stt_vad,sample_rate=16000,sample_width=2):
    async for chunk in audio_stream:yield chunk.audio
   async def speech_to_text(self,metadata,stream):
    async for _ in self._speech_to_text_stream(stream,object()):pass
    return 'Mluvená věta'
  class Coordinator:
   async def complete(self,*args):calls.append(args)
  self.assertEqual(install(hass,Pipeline,Coordinator(),'2026.6.4','p','s'),'active')
  async def audio():
   for _ in range(4):yield NS(audio=bytes(32000),speech_probability=.9)
  run=Pipeline();run.hass=hass;run.pipeline=NS(id='other');run._satellite_id='s'
  await run.speech_to_text(NS(sample_rate=16000),audio());self.assertFalse(calls)
  run.pipeline.id='p'
  text=await run.speech_to_text(metadata=NS(sample_rate=16000),stream=audio())
  self.assertEqual(text,'Mluvená věta');self.assertEqual(len(calls[0][1]),128000)
  self.assertEqual(calls[0][2],4);self.assertFalse(hasattr(run,'_jarvis_identity_capture'))
 async def test_unsupported_core_never_modifies_pipeline(self):
  class Pipeline:pass
  self.assertEqual(install(None,Pipeline,None,'future','p','s'),'unsupported_core')
  self.assertFalse(hasattr(Pipeline,'_jarvis_speaker_adapter'))

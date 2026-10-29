import unittest
from types import SimpleNamespace as NS
from direct_wake import install

class DirectWakeTests(unittest.IsolatedAsyncioTestCase):
 def setup_input(self, phrase='rozsviť', satellite='sat', version='2026.6.4'):
  calls=[]
  class Input:
   async def execute(self,validate=False):
    calls.append((self.run.start_stage,self.intent_input,self.stt_stream,validate))
  hass=object()
  report=install(hass,Input,NS(STT='stt',INTENT='intent'),'2026.6.4' if version is None else version,'pipe','sat')
  value=Input();value.run=NS(hass=hass,pipeline=NS(id='pipe'),start_stage='stt')
  value.satellite_id=satellite;value.wake_word_phrase=phrase;value.intent_input=None;value.stt_stream=object()
  return value,calls,report
 async def test_light_wake_executes_once_without_cloud_transcription(self):
  value,calls,report=self.setup_input();stream=value.stt_stream
  await value.execute()
  self.assertEqual(calls,[('intent','rozsviť',None,False)])
  self.assertEqual(value.run.start_stage,'stt');self.assertIs(value.stt_stream,stream)
  self.assertEqual(report['commands'],1)
 async def test_zhasni_is_explicit_off_not_toggle(self):
  value,calls,_=self.setup_input('zhasni');await value.execute()
  self.assertEqual(calls[0][1],'zhasni')
 async def test_other_words_and_satellites_delegate_unchanged(self):
  for phrase,sat in [('Jarvis','sat'),('odemkni','sat'),('zhasni','other')]:
   value,calls,_=self.setup_input(phrase,sat);stream=value.stt_stream;await value.execute()
   self.assertEqual(calls,[('stt',None,stream,False)])
 async def test_unsupported_core_never_installs(self):
  value,calls,report=self.setup_input(version='2026.10.4');await value.execute()
  self.assertEqual(calls[0][0],'stt');self.assertEqual(report['status'],'unsupported_core')
 async def test_cancellation_restores_per_run_input(self):
  import asyncio
  class Input:
   async def execute(self,validate=False):raise asyncio.CancelledError()
  hass=object();install(hass,Input,NS(STT='stt',INTENT='intent'),'2026.6.4','pipe','sat')
  v=Input();v.run=NS(hass=hass,pipeline=NS(id='pipe'),start_stage='stt');v.satellite_id='sat';v.wake_word_phrase='zhasni';v.intent_input=None;v.stt_stream='stream'
  with self.assertRaises(asyncio.CancelledError):await v.execute()
  self.assertEqual((v.run.start_stage,v.intent_input,v.stt_stream),('stt',None,'stream'))

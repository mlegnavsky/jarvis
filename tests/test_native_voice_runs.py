import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from app import voice_settings
from app.policy import APIError


class NativeVoiceRunsTests(unittest.IsolatedAsyncioTestCase):
 async def test_reads_native_timing_without_exporting_transcripts_or_urls(self):
  self.assertTrue(callable(getattr(voice_settings, 'runs', None)))
  calls=[]
  async def ws(sup, command, arguments):
   calls.append((command, arguments))
   if command.endswith('/list'):
    return {'pipeline_runs':[{'pipeline_run_id':'r1','timestamp':'2026-11-08T07:29:40+00:00'}]}
   return {'events':[{'type':t,'timestamp':f'2026-11-08T07:29:{s:02d}+00:00','data':{'text':'PRIVATE','url':'SECRET','error':{'message':'PRIVATE'}}} for t,s in [('run-start',40),('stt-start',40),('stt-vad-end',42),('stt-end',43),('intent-start',43),('intent-end',45),('tts-start',45),('tts-end',46),('run-end',46)]]}
  with patch.object(voice_settings, 'websocket_query', ws):
   result=await voice_settings.runs(SimpleNamespace(sup=None),'p1')
  run=result['runs'][0]
  self.assertEqual(run['timings_s']['stt_processing'],1)
  self.assertEqual(run['timings_s']['intent'],2)
  self.assertEqual(run['timings_s']['tts'],1)
  self.assertEqual(run['timings_s']['vad_end_to_tts_ready'],4)
  self.assertNotIn('PRIVATE',json.dumps(result));self.assertNotIn('SECRET',json.dumps(result))
  self.assertEqual(calls[1][1],{'pipeline_id':'p1','pipeline_run_id':'r1'})
  self.assertFalse(result['physical_playback_measured'])

 async def test_bounds_history_and_rejects_arbitrary_targets(self):
  self.assertTrue(callable(getattr(voice_settings,'runs',None)))
  calls=[]
  async def ws(sup,command,arguments):
   calls.append(command)
   if command.endswith('/list'):return {'pipeline_runs':[{'pipeline_run_id':f'r{i}','timestamp':'2026-11-08T00:00:00Z'} for i in range(50)]}
   return {'events':[]}
  with patch.object(voice_settings,'websocket_query',ws):
   with self.assertRaises(APIError):await voice_settings.runs(SimpleNamespace(sup=None),'../private')
   result=await voice_settings.runs(SimpleNamespace(sup=None),'p1')
  self.assertEqual(len(result['runs']),5);self.assertEqual(len(calls),6)
  self.assertTrue(result['truncated'])

 async def test_missing_or_negative_timestamps_never_fabricate_duration(self):
  self.assertTrue(callable(getattr(voice_settings,'runs',None)))
  async def ws(sup,command,arguments):
   if command.endswith('/list'):return {'pipeline_runs':[{'pipeline_run_id':'r'}]}
   return {'events':[{'type':'stt-vad-end','timestamp':'2026-11-08T00:00:03Z'},{'type':'stt-end','timestamp':'2026-11-08T00:00:02Z'},{'type':'error','timestamp':'bad','data':{'code':'PRIVATE'}}]}
  with patch.object(voice_settings,'websocket_query',ws):
   result=await voice_settings.runs(SimpleNamespace(sup=None),'p1')
  self.assertIsNone(result['runs'][0]['timings_s']['stt_processing'])
  self.assertNotIn('PRIVATE',json.dumps(result))

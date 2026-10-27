import importlib.util
from pathlib import Path
import math
import struct
import unittest
SPEC=importlib.util.spec_from_file_location('voice_analysis',Path(__file__).with_name('analysis.py'))
class AnalysisTests(unittest.TestCase):
 def setUp(self):
  self.a=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(self.a)
 def test_silence_and_clipping(self):
  self.assertEqual(self.a.audio_metrics(bytes(32000))['duration_s'],1)
  self.assertTrue(self.a.audio_metrics(bytes(32000))['silent'])
  p=struct.pack('<h',32767)*16000
  self.assertEqual(self.a.audio_metrics(p)['clipping_percent'],100)
  self.assertFalse(self.a.audio_metrics(p)['silent'])
 def test_invalid_pcm_is_rejected(self):
  with self.assertRaises(ValueError):self.a.audio_metrics(b'x')
  with self.assertRaises(ValueError):self.a.audio_metrics(b'')
 def test_transcript_error_detects_observed_failure(self):
  self.assertEqual(self.a.word_error('Kolik je hodin?','kolik je hodin.'),0)
  self.assertGreater(self.a.word_error('Kolik je hodin?','Koleký a hodí.'),.5)
 def test_partial_run_does_not_claim_completion(self):
  r=self.a.summarize_run('r',[{'type':'run-start','timestamp':'2026-10-28T00:00:00+00:00'}, {'type':'stt-start','timestamp':'2026-10-28T00:00:01+00:00'}])
  self.assertFalse(r['complete']);self.assertIsNone(r['timings_s']['stt_processing']);self.assertIsNone(r['timings_s']['total_pipeline'])
 def test_vad_and_transcription_are_separate_and_secrets_excluded(self):
  ev=[{'type':t,'timestamp':f'2026-10-28T00:00:{s:02d}+00:00','data':d} for t,s,d in [('run-start',0,{'tts_output':{'token':'private'}}),('stt-start',1,{'engine':'stt.faster_whisper'}),('stt-vad-end',4,{}),('stt-end',7,{'stt_output':{'text':'Kolik je hodin?'}}),('intent-start',7,{}),('intent-end',8,{}),('tts-start',8,{}),('tts-end',9,{'url':'private'}),('run-end',10,{})]]
  r=self.a.summarize_run('r',ev)
  self.assertEqual(r['timings_s']['stt_processing'],3);self.assertEqual(r['timings_s']['capture_until_vad_end'],3)
  self.assertEqual(r['timings_s']['total_pipeline'],10);self.assertEqual(r['transcript'],'Kolik je hodin?');self.assertNotIn('private',str(r))

 def test_long_capture_keeps_full_duration_with_bounded_analysis(self):
  r=self.a.audio_metrics(bytes(640000),total_frames=480000)
  self.assertEqual(r['duration_s'],30)
  self.assertEqual(r['analyzed_duration_s'],20)
  self.assertTrue(r['truncated_analysis'])

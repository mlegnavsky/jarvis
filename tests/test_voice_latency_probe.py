import unittest
from types import SimpleNamespace
from unittest.mock import patch
from app import voice_settings
from app.admin import revision
from app.policy import APIError

class ProbeTests(unittest.IsolatedAsyncioTestCase):
 async def test_fixed_text_probe_never_starts_audio_or_exports_content(self):
  self.assertTrue(callable(getattr(voice_settings,'probe',None)))
  pipeline={'id':'p','conversation_engine':'conversation.openai_conversation'}
  events=[{'type':'result','id':1,'success':True}]+[{'type':'event','id':1,'event':{'type':kind,'timestamp':f'2026-11-08T08:00:0{sec}Z','data':{'text':'private','url':'secret'}}} for kind,sec in [('run-start',0),('intent-start',0),('intent-end',1),('run-end',1)]]
  sent=[];closed=[]
  class WS:
   async def send_json(self,v):sent.append(v)
   async def receive_json(self):return events.pop(0)
   async def close(self):closed.append(True)
  class Sup:
   timeout=1
   async def _websocket(self):return WS()
  with patch.object(voice_settings,'read',return_value={'pipeline':pipeline,'revision':revision(pipeline)}):
   r=await voice_settings.probe(SimpleNamespace(sup=Sup()),'key',{'pipeline_id':'p','expected_revision':revision(pipeline)})
  self.assertTrue(r['verified']);self.assertEqual(r['intent_s'],1)
  self.assertEqual(sent[0]['start_stage'],'intent');self.assertEqual(sent[0]['end_stage'],'intent')
  self.assertEqual(sent[0]['input']['text'],'Ahoj, jak se máš? Odpověz jednou krátkou větou.')
  self.assertFalse(r['physical_playback_performed']);self.assertNotIn('private',str(r));self.assertTrue(closed)

 async def test_stale_revision_does_not_invoke_provider(self):
  self.assertTrue(callable(getattr(voice_settings,'probe',None)))
  with patch.object(voice_settings,'read',return_value={'pipeline':{},'revision':'new'}):
   with self.assertRaises(APIError):await voice_settings.probe(SimpleNamespace(sup=None),'key',{'pipeline_id':'p','expected_revision':'old'})

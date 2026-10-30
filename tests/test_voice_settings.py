import unittest
from unittest.mock import patch
from types import SimpleNamespace
from app import voice_settings
from app.admin import revision
from app.policy import APIError

class VoiceSettingsTests(unittest.IsolatedAsyncioTestCase):
 async def test_only_voice_changes_and_readback_is_verified(self):
  pipeline={'id':'p1','name':'Jarvis','tts_voice':'onyx','tts_engine':'tts.openai_tts','conversation_engine':'conversation.extended_openai_conversation','language':'cs'}
  calls=[]
  async def ws(sup,command,args=None):
   calls.append((command,args))
   if command.endswith('/list'):return {'pipelines':[dict(pipeline)]}
   pipeline.update({k:v for k,v in args.items() if k!='pipeline_id'})
   return dict(pipeline)
  admin=SimpleNamespace(sup=None,remember=lambda *args:None)
  with patch.object(voice_settings,'websocket_query',ws):
   result=await voice_settings.change(admin,'key',{'pipeline_id':'p1','tts_voice':'ash','expected_revision':revision(pipeline)})
  self.assertTrue(result['verified']);self.assertEqual(pipeline['tts_voice'],'ash')
  self.assertEqual(pipeline['conversation_engine'],'conversation.extended_openai_conversation')
  self.assertEqual(calls[1],('assist_pipeline/pipeline/update',{'pipeline_id':'p1','tts_voice':'ash'}))
 async def test_stale_config_never_writes(self):
  calls=[]
  async def ws(*args):calls.append(args);return {'pipelines':[{'id':'p1','tts_voice':'onyx','tts_engine':'tts.openai_tts'}]}
  with patch.object(voice_settings,'websocket_query',ws):
   with self.assertRaises(APIError):await voice_settings.change(SimpleNamespace(sup=None),'key',{'pipeline_id':'p1','tts_voice':'ash','expected_revision':'0'*64})
  self.assertEqual(len(calls),1)
 async def test_concurrent_same_revision_allows_only_one_write(self):
  import asyncio
  pipeline={'id':'p1','tts_voice':'onyx','tts_engine':'tts.openai_tts'}
  writes=[]
  async def ws(sup,command,args=None):
   if command.endswith('/list'):
    value={'pipelines':[dict(pipeline)]}
    await asyncio.sleep(0)
    return value
   writes.append(args);pipeline['tts_voice']=args['tts_voice'];return dict(pipeline)
  admin=SimpleNamespace(sup=None,remember=lambda *args:None)
  rev=revision(pipeline)
  with patch.object(voice_settings,'websocket_query',ws):
   results=await asyncio.gather(*(voice_settings.change(admin,str(i),{'pipeline_id':'p1','tts_voice':voice,'expected_revision':rev}) for i,voice in enumerate(['ash','coral'])),return_exceptions=True)
  self.assertEqual(len(writes),1)
  self.assertEqual(sum(isinstance(r,APIError) for r in results),1)

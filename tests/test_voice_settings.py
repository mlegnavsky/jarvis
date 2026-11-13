import unittest
from unittest.mock import patch
from types import SimpleNamespace
import sqlite3,json
from app import voice_settings
from app.admin import revision
from app.policy import APIError

class VoiceSettingsTests(unittest.IsolatedAsyncioTestCase):
 async def test_native_agent_selection_preserves_audio_and_uses_local_intents(self):
  self.assertTrue(callable(getattr(voice_settings,'change_agent',None)))
  pipeline={'id':'p1','name':'Jarvis','language':'cs','conversation_language':'*','conversation_engine':'conversation.extended_openai_conversation','stt_engine':'stt.openai_stt','tts_engine':'tts.openai_tts','tts_voice':'marin','prefer_local_intents':False}
  async def ws(sup,command,args=None):
   if command.endswith('/list'):return {'pipelines':[dict(pipeline)]}
   pipeline.update({k:v for k,v in args.items() if k!='pipeline_id'});return dict(pipeline)
  class Supervisor:
   async def registry(self,kind):return [{'entity_id':'conversation.openai_conversation','config_entry_id':'official'}]
  admin=SimpleNamespace(sup=Supervisor(),remember=lambda *args:None)
  with patch.object(voice_settings,'websocket_query',ws),patch.object(voice_settings,'native_agent_entry',return_value={'domain':'openai_conversation','state':'loaded'}):
   result=await voice_settings.change_agent(admin,'agentkey',{'pipeline_id':'p1','conversation_engine':'conversation.openai_conversation','expected_revision':revision(pipeline)})
  self.assertTrue(result['verified']);self.assertEqual(pipeline['conversation_engine'],'conversation.openai_conversation')
  self.assertEqual(pipeline['stt_engine'],'stt.openai_stt');self.assertEqual(pipeline['tts_voice'],'marin');self.assertTrue(pipeline['prefer_local_intents'])
  self.assertEqual(pipeline['conversation_language'],'*')
 async def test_disabled_native_entity_is_rejected_before_provider_lookup(self):
  class Sup:
   async def registry(self,kind):return [{'entity_id':'conversation.native','config_entry_id':'official','disabled_by':'user'}]
  with patch.object(voice_settings.integration_admin,'entry',return_value={'domain':'openai_conversation','state':'loaded'}):
   with self.assertRaises(APIError):await voice_settings.native_agent_entry(SimpleNamespace(sup=Sup()),'conversation.native')
 async def test_owned_pipeline_before_image_can_be_restored_with_cas(self):
  self.assertTrue(callable(getattr(voice_settings,'restore',None)))
  old={'id':'p1','name':'Jarvis','language':'cs','conversation_engine':'conversation.extended_openai_conversation'}
  current={**old,'conversation_engine':'conversation.openai_conversation','prefer_local_intents':True}
  db=sqlite3.connect(':memory:');self.addCleanup(db.close)
  db.execute('CREATE TABLE jobs(key TEXT,operation TEXT,before_data TEXT)')
  db.execute('INSERT INTO jobs VALUES (?,?,?)',('owned','voice_pipeline_agent',json.dumps({'pipeline':old})))
  async def ws(sup,command,args=None):
   if command.endswith('/list'):return {'pipelines':[dict(current)]}
   current.clear();current.update({'id':'p1',**{k:v for k,v in args.items() if k!='pipeline_id'}});return dict(current)
  admin=SimpleNamespace(sup=None,db=lambda:db,remember=lambda *args:None)
  with patch.object(voice_settings,'websocket_query',ws):
   with self.assertRaises(APIError):await voice_settings.restore(admin,'new',{'backup_id':'owned','expected_revision':'0'*64})
   result=await voice_settings.restore(admin,'new',{'backup_id':'owned','expected_revision':revision(current)})
  self.assertTrue(result['verified']);self.assertEqual(current,old)
 async def test_native_agent_selection_rejects_custom_provider(self):
  self.assertTrue(callable(getattr(voice_settings,'change_agent',None)))
  with patch.object(voice_settings,'native_agent_entry',return_value={'domain':'extended_openai_conversation'}):
   with self.assertRaises(APIError):await voice_settings.change_agent(SimpleNamespace(),'key',{'pipeline_id':'p','conversation_engine':'conversation.extended_openai_conversation','expected_revision':'0'*64})
 async def test_only_voice_changes_and_readback_is_verified(self):
  pipeline={'id':'p1','name':'Jarvis','tts_voice':'onyx','tts_engine':'tts.openai_tts','conversation_engine':'conversation.extended_openai_conversation','language':'cs'}
  calls=[]
  async def ws(sup,command,args=None):
   calls.append((command,args))
   if command.endswith('/list'):return {'pipelines':[dict(pipeline)]}
   required={'name','language','tts_engine','conversation_engine'}
   if not required <= args.keys():raise ValueError('native_required_pipeline_fields_missing')
   pipeline.update({k:v for k,v in args.items() if k!='pipeline_id'})
   return dict(pipeline)
  admin=SimpleNamespace(sup=None,remember=lambda *args:None)
  with patch.object(voice_settings,'websocket_query',ws):
   result=await voice_settings.change(admin,'key',{'pipeline_id':'p1','tts_voice':'ash','expected_revision':revision(pipeline)})
  self.assertTrue(result['verified']);self.assertEqual(pipeline['tts_voice'],'ash')
  self.assertEqual(pipeline['conversation_engine'],'conversation.extended_openai_conversation')
  self.assertEqual(calls[1],('assist_pipeline/pipeline/update',{'pipeline_id':'p1',**{k:v for k,v in pipeline.items() if k!='id'}}))
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

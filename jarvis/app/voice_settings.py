"""Revision-bound native voice settings; no credential or prompt access."""
import asyncio
import re
import json
from .diagnostics import websocket_query
from .policy import APIError
from . import integration_admin

VOICES={'alloy','ash','ballad','coral','echo','fable','nova','onyx','sage','shimmer','verse','marin','cedar'}

async def native_agent_entry(admin,entity_id):
 registry=await admin.sup.registry('entity')
 item=next((x for x in registry if x.get('entity_id')==entity_id),None)
 if not item or not item.get('config_entry_id') or item.get('disabled_by'):raise APIError(400,'native_conversation_agent_required')
 state=await admin.sup.request('GET','/core/api/states/'+entity_id)
 # Conversation states can be unknown before first use; unavailable is not ready.
 if not isinstance(state,dict) or state.get('entity_id')!=entity_id or state.get('state')=='unavailable':raise APIError(400,'native_conversation_agent_unavailable')
 return await integration_admin.entry(admin,item['config_entry_id'])

async def change_agent(admin,key,args):
 if (not isinstance(args['pipeline_id'],str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}',args['pipeline_id'])
     or not isinstance(args['conversation_engine'],str) or not re.fullmatch(r'conversation\.[a-z0-9_]+',args['conversation_engine'])):raise APIError(400,'invalid_voice_settings')
 entry=await native_agent_entry(admin,args['conversation_engine'])
 if entry.get('domain')!='openai_conversation' or entry.get('state')!='loaded':raise APIError(400,'native_conversation_agent_required')
 if not hasattr(admin,'_voice_settings_lock'):admin._voice_settings_lock=asyncio.Lock()
 async with admin._voice_settings_lock:
  before=await read(admin,args['pipeline_id'])
  if before['revision']!=args['expected_revision']:raise APIError(409,'voice_pipeline_changed')
  admin.remember(key,before)
  expected={**before['pipeline'],'conversation_engine':args['conversation_engine'],'prefer_local_intents':True}
  await websocket_query(admin.sup,'assist_pipeline/pipeline/update',{'pipeline_id':args['pipeline_id'],**{k:v for k,v in expected.items() if k!='id'}})
  after=await read(admin,args['pipeline_id'])
  return {**after,'verified':after['pipeline']==expected,'restart_required':False}

async def restore(admin,key,args):
 with admin.db() as db:
  row=db.execute('SELECT operation,before_data FROM jobs WHERE key=?',(args['backup_id'],)).fetchone()
 before=json.loads(row[1]) if row and row[1] else {}
 allowed={'voice_pipeline_agent','voice_pipeline_settings','voice_pipeline_restore'}
 if not row or row[0] not in allowed or not isinstance(before.get('pipeline'),dict):raise APIError(404,'voice_pipeline_backup_not_found')
 saved=before['pipeline']
 if not hasattr(admin,'_voice_settings_lock'):admin._voice_settings_lock=asyncio.Lock()
 async with admin._voice_settings_lock:
  live=await read(admin,saved['id'])
  if live['revision']!=args['expected_revision']:raise APIError(409,'voice_pipeline_changed')
  admin.remember(key,live)
  await websocket_query(admin.sup,'assist_pipeline/pipeline/update',{'pipeline_id':saved['id'],**{k:v for k,v in saved.items() if k!='id'}})
  after=await read(admin,saved['id'])
  return {**after,'verified':after['pipeline']==saved,'restart_required':False}

async def read(admin,target):
 from .admin import revision
 values=await websocket_query(admin.sup,'assist_pipeline/pipeline/list')
 pipeline=next((p for p in values.get('pipelines',[]) if p.get('id')==target),None)
 if pipeline is None:raise APIError(404,'voice_pipeline_not_found')
 return {'pipeline':pipeline,'revision':revision(pipeline)}

async def change(admin,key,args):
 if not hasattr(admin,'_voice_settings_lock'):admin._voice_settings_lock=asyncio.Lock()
 async with admin._voice_settings_lock:
  return await _change(admin,key,args)

async def _change(admin,key,args):
 if not isinstance(args['pipeline_id'],str) or not re.fullmatch(r'[a-zA-Z0-9_-]{1,128}',args['pipeline_id']) or not isinstance(args['tts_voice'],str) or args['tts_voice'] not in VOICES:raise APIError(400,'invalid_voice_settings')
 before=await read(admin,args['pipeline_id'])
 if before['revision']!=args['expected_revision']:raise APIError(409,'voice_pipeline_changed')
 if before['pipeline'].get('tts_engine')!='tts.openai_tts':raise APIError(409,'unsupported_voice_provider')
 admin.remember(key,before)
 await websocket_query(admin.sup,'assist_pipeline/pipeline/update',{**{k:v for k,v in before['pipeline'].items() if k!='id'},'pipeline_id':args['pipeline_id'],'tts_voice':args['tts_voice']})
 after=await read(admin,args['pipeline_id'])
 expected={**before['pipeline'],'tts_voice':args['tts_voice']}
 return {**after,'verified':after['pipeline']==expected,'restart_required':False}

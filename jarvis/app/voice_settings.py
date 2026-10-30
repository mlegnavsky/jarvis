"""Revision-bound TTS voice changes; no provider, credential or prompt access."""
import asyncio
import re
from .diagnostics import websocket_query
from .policy import APIError

VOICES={'alloy','ash','ballad','coral','echo','fable','nova','onyx','sage','shimmer','verse','marin','cedar'}

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
 await websocket_query(admin.sup,'assist_pipeline/pipeline/update',{'pipeline_id':args['pipeline_id'],'tts_voice':args['tts_voice']})
 after=await read(admin,args['pipeline_id'])
 expected={**before['pipeline'],'tts_voice':args['tts_voice']}
 return {**after,'verified':after['pipeline']==expected,'restart_required':False}

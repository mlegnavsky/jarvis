"""Voice maintenance through the existing authenticated bridge, without raw audio."""
from .policy import APIError
from .ha import now, UpstreamError
import json

VOICE_SERVICES = {
 'tts.speak', 'select.select_option', 'number.set_value', 'switch.turn_on', 'switch.turn_off',
 'media_player.volume_set', 'media_player.media_stop', 'assist_satellite.announce',
 'jarvis_voice_diagnostics.arm_capture', 'jarvis_voice_diagnostics.run_self_test',
 'jarvis_voice_diagnostics.run_companion_test',
}
VOICE_DOMAINS = {'select', 'number', 'switch', 'media_player', 'assist_satellite','tts'}
ATTRIBUTES = {'friendly_name','options','min','max','step','unit_of_measurement','volume_level','is_volume_muted','supported_features'}

class VoiceBridge:
 def __init__(self,ha,options,actions,admin):
  self.ha,self.options,self.actions,self.admin=ha,options,actions,admin
 async def invoke(self,data,key):
  if self.options.get('maintenance_enabled') is not True:raise APIError(403,'maintenance_disabled')
  if not isinstance(data,dict):raise APIError(400,'invalid_voice_request')
  if data == {'action':'status'}:
   states=await self.ha.request('GET','/core/api/states')
   entities=[]
   for state in states:
    entity=state.get('entity_id','')
    if entity not in self.options.get('allowed_entities',[]) or entity.split('.')[0] not in VOICE_DOMAINS:continue
    attrs={k:v for k,v in state.get('attributes',{}).items() if k in ATTRIBUTES}
    entities.append({'entity_id':entity,'state':state.get('state'),'attributes':attrs,'last_updated':state.get('last_updated')})
   return {'captured_at':now(),'entities':entities,'raw_audio_exposed':False,'recording_started':False}
  if data == {'action':'diagnostics'}:
   async def read_report(path):
    try:
     value=await self.admin.read('file',path)
     value=json.loads(value.get('content'))
     if not isinstance(value,dict):return {},'unavailable'
     return value,'available'
    except (APIError,UpstreamError,TypeError,ValueError):return {},'unavailable'
   report,voice_status=await read_report('jarvis_workspace/voice_diagnostics/report.json')
   player,output_status=await read_report('jarvis_workspace/homepod_output/report.json')
   source=report.get('runs',[])
   runs=[{k:r.get(k) for k in ('id','started_at','complete','error','timings_s','outcome')} for r in (source[-20:] if isinstance(source,list) else []) if isinstance(r,dict)]
   return {'captured_at':now(),'updated_at':report.get('updated_at'),'runs':runs,
           'capture_expires_at':report.get('capture_expires_at'),
           'partial':voice_status!='available' or output_status!='available',
           'reports':{'voice':voice_status,'output':output_status},
           'output':{k:player.get(k) for k in ('status','speech_volume','observed_volume','playback','updated_at')},
           'transcripts_exposed':False,'raw_audio_exposed':False}
  if data == {'action':'pipelines'}:return await self.admin.read('voice_pipelines')
  if set(data)=={'action','entity_id','service','data'} and data['action']=='change':
   if data['service'] not in VOICE_SERVICES:raise APIError(403,'unsupported_voice_service')
   status,result=await self.actions.execute({k:data[k] for k in ('entity_id','service','data')},key)
   if status>=400:raise APIError(status,result['error'])
   return result
  raise APIError(400,'invalid_voice_request')

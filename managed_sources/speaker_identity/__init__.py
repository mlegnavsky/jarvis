"""Opt-in local voiceprints, scoped only to active Jarvis satellite speech."""
import asyncio
from datetime import timedelta
import hashlib
import io
import json
from pathlib import Path
import tempfile
import wave
import aiohttp
import voluptuous as vol
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
from .coordinator import Coordinator,admin_forget
from .hooks import install
from .policy import MODEL_ID,VoiceProfiles
from .transport import read_limited

DOMAIN='jarvis_speaker_identity'
CONFIG_SCHEMA=vol.Schema({vol.Optional(DOMAIN):vol.Schema({})},extra=vol.ALLOW_EXTRA)
SATELLITE='assist_satellite.home_assistant_voice_0a8bde_assist_satellite'
PIPELINE='01kw4sat65taw1y72xzrv2xyj4'
BACKEND='http://local-jarvis-core:8766'

async def async_setup(hass,config):
 root=Path(hass.config.path('jarvis_workspace','speaker_identity'))
 session=async_get_clientsession(hass)
 async def infer(pcm):
  async with session.post(BACKEND+'/embedding',data=pcm,headers={'Content-Type':'application/octet-stream'},
                          timeout=aiohttp.ClientTimeout(total=7),allow_redirects=False) as response:
   if response.status!=200:raise ValueError('embedding_http_'+str(response.status))
   if response.content_length and response.content_length>64000:raise ValueError('embedding_size')
   data=await response.json()
   if not isinstance(data,dict):raise ValueError('embedding_response')
   return data
 coordinator=Coordinator(hass,root/'profiles.sqlite',infer)
 hass.data[DOMAIN]=coordinator
 def clear_memory(memory_id):
  from custom_components.extended_openai_conversation.memory import MemoryStore
  for path in Path(hass.config.path('jarvis_workspace','companion_memory')).glob('*.sqlite'):
   if not path.is_symlink():MemoryStore(path).forget('voice:'+memory_id)
 async def forget_service(call):
  from homeassistant.exceptions import ServiceValidationError
  try:await admin_forget(hass,call.context.user_id,call.data['name'],coordinator,clear_memory)
  except PermissionError as exc:raise ServiceValidationError('Smazání profilu vyžaduje přihlášeného správce.') from exc
 hass.services.async_register(DOMAIN,'forget_profile',forget_service,schema=vol.Schema({vol.Required('name'):str}))
 registry=er.async_get(hass)
 entity=registry.async_get(SATELLITE)
 if entity and entity.device_id:coordinator.aliases[entity.device_id]=SATELLITE
 from homeassistant.const import __version__ as core_version
 from homeassistant.components.assist_pipeline.pipeline import PipelineRun
 adapter=install(hass,PipelineRun,coordinator,core_version,PIPELINE,SATELLITE)
 report={'version':3,'started_at':dt_util.utcnow().isoformat(),'model':MODEL_ID,'adapter':adapter,
         'enrollment_trigger_requires_embedding':False,
         'enrollment_policy':'reject_sample_keep_progress_v2',
         'raw_audio_saved':False,'voice_is_authentication':False,'household_accuracy_verified':False,
         'minimum_enrollment_samples':3,'match_threshold':.75,'match_margin':.12,
         'automatic_profile_adaptation':False,'backend_host_port_published':False}
 def save(snapshot):
  root.mkdir(parents=True,exist_ok=True,mode=0o700)
  temporary=root/'report.tmp'
  temporary.write_text(json.dumps(snapshot,ensure_ascii=False,indent=2));temporary.chmod(0o600)
  temporary.replace(root/'report.json')
 async def update(_now=None):
  try:
   async with session.get(BACKEND+'/health',timeout=aiohttp.ClientTimeout(total=3),allow_redirects=False) as response:
    if response.status!=200:raise ValueError('health_http')
    health=await response.json()
   healthy=health.get('model')==MODEL_ID and health.get('reference_probe',{}).get('passed') is True
   report['backend']=health
   coordinator.status='ready' if healthy and adapter=='active' and report.get('native_probe',{}).get('passed') is True else 'starting' if 'native_probe' not in report else 'not_ready'
  except Exception as exc:
   coordinator.status='backend_unavailable';report['backend_error']=type(exc).__name__
  try:count=await hass.async_add_executor_job(coordinator.profiles.count)
  except Exception as exc:
   count=None;coordinator.status='profile_store_error';report['profile_error']=type(exc).__name__
  report.update(updated_at=dt_util.utcnow().isoformat(),status=coordinator.status,
                captured_turns=coordinator.capture_count,last_turn=coordinator.last,
                profile_count=count,enrollment=coordinator.enrollment_state())
  await hass.async_add_executor_job(save,dict(report))
  hass.states.async_set('sensor.jarvis_rozpoznavani_hlasu',coordinator.status,
    {'friendly_name':'Jarvis · rozpoznávání mluvčího','profiles':report['profile_count'],
     'adapter':adapter,'captured_turns':coordinator.capture_count,'last_status':coordinator.last.get('status'),
     'raw_audio_saved':False,'household_accuracy_verified':False})
 async def native_probe():
  # Public upstream reference speech, never a household recording or fake family enrollment.
  url='https://github.com/k2-fsa/sherpa-onnx/releases/download/speaker-recongition-models/fangjun-test-sr-1.wav'
  stage='reference_download'
  try:
   async with session.get(url,timeout=aiohttp.ClientTimeout(total=30)) as response:
    response.raise_for_status();audio=await read_limited(response.content,256000)
   if hashlib.sha256(audio).hexdigest()!='9175e523081bf6a630ce72a55b05f92148eaafaf58cbbbe743686cd81c50848e':raise ValueError('reference_checksum')
   stage='reference_decode'
   with wave.open(io.BytesIO(audio)) as wav:pcm=wav.readframes(wav.getnframes())
   stage='local_model_inference'
   data=await infer(pcm)
   if data.get('status')!='ok' or data.get('model')!=MODEL_ID:raise ValueError('reference_embedding')
   stage='profile_policy'
   def policy_probe():
    with tempfile.TemporaryDirectory(prefix='jarvis-speaker-probe-') as directory:
     path=Path(directory)/'fixture.sqlite';db=VoiceProfiles(path)
     db.begin('fictional_device','Testovací Profil')
     for _ in range(3):db.sample('fictional_device',data['vector'],4)
     persisted=VoiceProfiles(path).identify(data['vector'])['status']=='recognized'
     db.forget('Testovací Profil')
     return persisted and db.count()==0
   report['native_probe']={'passed':await hass.async_add_executor_job(policy_probe),
       'embedding_dimensions':len(data['vector']),'inference_ms':data.get('inference_ms'),
       'scope':'HA HTTP -> real local embedding model -> temporary fictional profile persistence/deletion; no household profiles changed'}
  except Exception as exc:report['native_probe']={'passed':False,'stage':stage,'error':type(exc).__name__,
       'reason':str(exc)[:80] if isinstance(exc,ValueError) else type(exc).__name__}
  await update()
 async def start(_event=None):
  await update();await native_probe()
 if hass.is_running:hass.async_create_task(start())
 else:hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED,start)
 async_track_time_interval(hass,update,timedelta(seconds=60))
 return True



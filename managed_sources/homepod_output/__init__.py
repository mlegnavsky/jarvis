"""Route only Jarvis living-room responses to the existing HomePod entity."""
from datetime import timedelta
import asyncio
import time
import io
import json
from pathlib import Path
import wave
from aiohttp import web
from aioesphomeapi import VoiceAssistantFeature
import voluptuous as vol
from homeassistant.components.http import HomeAssistantView
from homeassistant.components.media_player import DATA_COMPONENT,async_process_play_media_url
from homeassistant.components.assist_satellite.const import DATA_COMPONENT as SATELLITE_COMPONENT
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED,__version__ as CORE_VERSION
from homeassistant.helpers.event import async_track_time_interval,async_track_state_change_event
from homeassistant.util import dt as dt_util
from pyatv.const import FeatureName
from .routing import Router,install,SILENT_URL,url_terminal_supported,play_at_current_volume

from .tv_session import TVSession
from .interrupt import install_abort_resume

DOMAIN='jarvis_homepod_output'
CONFIG_SCHEMA=vol.Schema({vol.Optional(DOMAIN):vol.Schema({vol.Optional('speech_volume',default=0.45):vol.All(vol.Coerce(float),vol.Range(min=0.05,max=0.8))})},extra=vol.ALLOW_EXTRA)
SPEAKER='media_player.homepod_obyvak_homepod_obyvak'
SATELLITE='assist_satellite.home_assistant_voice_0a8bde_assist_satellite'
PIPELINE='01kw4sat65taw1y72xzrv2xyj4'
TELEVISION='media_player.obyvaci_pokoj_obyvaci_pokoj'

def silence_wav():
 output=io.BytesIO()
 with wave.open(output,'wb') as wav:
  wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(16000);wav.writeframes(bytes(3200))
 return output.getvalue()

class SilenceView(HomeAssistantView):
 url=SILENT_URL;name='api:jarvis_homepod_output:silence';requires_auth=False
 async def get(self,request):return web.Response(body=silence_wav(),content_type='audio/wav')

async def async_setup(hass,config):
 speech_volume=config[DOMAIN]['speech_volume']
 last_volume={}
 hass.http.register_view(SilenceView())
 def satellite_url_supported():
  component=hass.data.get(SATELLITE_COMPONENT)
  entity=component.get_entity(SATELLITE) if component else None
  if entity is None:return False
  info=entity._entry_data.device_info
  flags=info.voice_assistant_feature_flags_compat(entity._entry_data.api_version) if info else 0
  return url_terminal_supported(flags,VoiceAssistantFeature.VOICE_ASSISTANT,VoiceAssistantFeature.SPEAKER)
 def player():
  if not satellite_url_supported():raise ValueError('satellite_media_player_url_required')
  component=hass.data.get(DATA_COMPONENT)
  entity=component.get_entity(SPEAKER) if component else None
  if (entity is None or not entity.available or not getattr(entity,'atv',None)
      or not entity._is_feature_available(FeatureName.StreamFile)):
   raise ValueError('homepod_raop_unavailable')
  return entity
 async def play(media_id):
  # Calling the native async entity method awaits the entire RAOP stream,
  # avoiding any generic service-call timeout being mistaken for audio end.
  if tv_prepare is not None:
   await asyncio.shield(tv_prepare)
  nonlocal last_volume
  last_volume=await play_at_current_volume(player(),media_id)
 async def stop():await player().async_media_stop()
 def read_tv():
  state=hass.states.get(TELEVISION)
  return state.as_dict() if state else None
 async def tv_call(service):
  await hass.services.async_call('media_player',service,{'entity_id':TELEVISION},blocking=True)
 television=TVSession(read_tv,tv_call)
 tv_prepare=None;active_run=None;lease_started=None;active_pipeline=False;pending_followup=False
 router=Router(play,stop)
 from homeassistant.components.assist_pipeline.pipeline import PipelineRun,TextToSpeechError
 adapter=install(hass,PipelineRun,router,CORE_VERSION,PIPELINE,SATELLITE,TextToSpeechError)
 from homeassistant.components.esphome.assist_satellite import EsphomeAssistSatellite
 from homeassistant.components.assist_satellite.entity import AssistSatelliteAnnouncement
 def can_resume(entity):
  mute=hass.states.get('switch.home_assistant_voice_0a8bde_mute')
  return bool(hass.is_running and entity.available and mute and mute.state=='off')
 def current_pending():
  controller=PipelineRun.__dict__.get('_jarvis_turn_adapter')
  return controller.pending if controller else None
 async def resume_dialogue(entity,pending):
  controller=PipelineRun.__dict__.get('_jarvis_turn_adapter')
  if controller is None:raise RuntimeError('conversation_controller_unavailable')
  # Direct native announcement preserves the current conversation ID. The HA
  # start_conversation service intentionally creates a new one, so do not use it.
  if controller.pending is not None:raise RuntimeError('newer_dialogue_pending')
  controller.pending=dict(pending)
  try:
   await entity.async_start_conversation(AssistSatelliteAnnouncement(
    message='',media_id=async_process_play_media_url(hass,SILENT_URL),original_media_id=SILENT_URL,
    tts_token=None,media_id_source='url',preannounce_media_id=None))
  except BaseException:
   if controller.pending==pending:controller.pending=None
   raise
 abort_resume=install_abort_resume(hass,EsphomeAssistSatellite,router,CORE_VERSION,
                                  SATELLITE,can_resume,resume_dialogue,current_pending) if adapter=='active' else None
 native_event=PipelineRun.process_event
 async def restore_tv(owner):
  if tv_prepare is not None:await asyncio.shield(tv_prepare)
  await television.release(if_current=lambda:active_run==owner and not active_pipeline and router.active is None)
 def session_event(run,event):
  nonlocal tv_prepare,active_run,lease_started,active_pipeline,pending_followup
  if run.hass is hass and run.pipeline.id==PIPELINE and run._satellite_id==SATELLITE and not str(run.id).startswith('synthetic-'):
   kind=str(event.type)
   if kind!='run-start' and active_run!=str(run.id):return native_event(run,event)
   if kind=='run-start':
    active_run=str(run.id);active_pipeline=True;pending_followup=False
    if not television.snapshot()['owned']:lease_started=time.monotonic()
    if tv_prepare is None or tv_prepare.done():tv_prepare=hass.async_create_task(television.acquire())
    run._jarvis_tv_continue=False
   elif kind=='intent-end':
    pending_followup=(event.data or {}).get('intent_output',{}).get('continue_conversation') is True
    run._jarvis_tv_continue=pending_followup
   elif kind=='error':
    active_pipeline=False;pending_followup=False
    hass.async_create_task(restore_tv(str(run.id)))
   elif kind=='run-end':
    active_pipeline=False
    if not getattr(run,'_jarvis_tv_continue',False):hass.async_create_task(restore_tv(str(run.id)))
  return native_event(run,event)
 if adapter=='active':PipelineRun.process_event=session_event
 async def television_state(event):
  state=event.data.get('new_state')
  television.observe(state.as_dict() if state else None)
 async def satellite_state(event):
  state=event.data.get('new_state')
  current=hass.states.get(SATELLITE)
  if adapter=='active' and state and state.state=='idle' and current and current.state=='idle' and not active_pipeline and not pending_followup and active_run is not None:
   await restore_tv(active_run)
 async_track_state_change_event(hass,[TELEVISION],television_state)
 async_track_state_change_event(hass,[SATELLITE],satellite_state)
 report={'version':3,'started_at':dt_util.utcnow().isoformat(),'adapter':adapter,'speaker':SPEAKER,
         'volume_policy':'follow_homepod','legacy_fixed_volume_ignored':speech_volume,
         'native_abort_resume':'active' if abort_resume else 'unavailable',
         'microphone':SATELLITE,'speech_volume':None,'terminal_spoken_output':False if adapter=='active' else 'native_uncontrolled','audible_test_performed':False,
         'arbitrary_speech_barge_in':False,'cancel_current_answer_hook':True,
         'wake_or_stop_word_physical_test':'deferred_until_user_home',
         'echo_reference_for_external_homepod':'not_available_on_stock_voice_pe',
         'followup_gate':'native_RAOP_completion_then_silent_satellite_completion'}
 root=Path(hass.config.path('jarvis_workspace','homepod_output'))
 def save(snapshot):
  root.mkdir(parents=True,exist_ok=True,mode=0o700)
  temporary=root/'report.tmp';temporary.write_text(json.dumps(snapshot,ensure_ascii=False,indent=2));temporary.chmod(0o600)
  temporary.replace(root/'report.json')
 async def update(_now=None):
  try:
   entity=player()
   report.update(player_available=True,raop_stream_file=True,player_state=entity.state,satellite_media_player_url=True,observed_volume=entity.volume_level,
                 observed_muted=getattr(entity,'is_volume_muted',None),speech_volume=entity.volume_level)
   report.pop('error',None);report.pop('reason',None)
   status='configured' if adapter=='active' else adapter
  except Exception as exc:
   report.update(player_available=False,error=type(exc).__name__,reason=str(exc)[:100] if isinstance(exc,ValueError) else type(exc).__name__);status='speaker_unavailable'
  if lease_started is not None and television.snapshot()['owned'] and not active_pipeline and router.active is None and time.monotonic()-lease_started>120:
   await television.release()
  report.update(status=status,updated_at=dt_util.utcnow().isoformat(),playback=router.snapshot(),television=television.snapshot(),television_entity=TELEVISION)
  report['interrupt_resume']=abort_resume.snapshot() if abort_resume else None
  report['last_volume_decision']=dict(last_volume)
  await hass.async_add_executor_job(save,dict(report))
  hass.states.async_set('sensor.jarvis_hlasovy_vystup',status,
    {'friendly_name':'Jarvis · hlasový výstup','speaker':SPEAKER,'adapter':adapter,
     'audible_test_performed':False,'arbitrary_speech_barge_in':False,**router.snapshot()})
 async def start(_event=None):await update()
 if hass.is_running:hass.async_create_task(start())
 else:hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED,start)
 async_track_time_interval(hass,update,timedelta(seconds=10))
 hass.data[DOMAIN]=router
 return True



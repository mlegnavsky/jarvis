"""Route only Jarvis living-room responses to the existing HomePod entity."""
from datetime import timedelta
import io
import json
from pathlib import Path
import wave
from aiohttp import web
from aioesphomeapi import VoiceAssistantFeature
import voluptuous as vol
from homeassistant.components.http import HomeAssistantView
from homeassistant.components.media_player import DATA_COMPONENT
from homeassistant.components.assist_satellite.const import DATA_COMPONENT as SATELLITE_COMPONENT
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED,__version__ as CORE_VERSION
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.util import dt as dt_util
from pyatv.const import FeatureName
from .routing import Router,install,SILENT_URL,url_terminal_supported,play_at_volume

DOMAIN='jarvis_homepod_output'
CONFIG_SCHEMA=vol.Schema({vol.Optional(DOMAIN):vol.Schema({vol.Optional('speech_volume',default=0.45):vol.All(vol.Coerce(float),vol.Range(min=0.05,max=0.8))})},extra=vol.ALLOW_EXTRA)
SPEAKER='media_player.homepod_obyvak_homepod_obyvak'
SATELLITE='assist_satellite.home_assistant_voice_0a8bde_assist_satellite'
PIPELINE='01kw4sat65taw1y72xzrv2xyj4'

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
  await play_at_volume(player(),media_id,speech_volume)
 async def stop():await player().async_media_stop()
 router=Router(play,stop)
 from homeassistant.components.assist_pipeline.pipeline import PipelineRun,TextToSpeechError
 adapter=install(hass,PipelineRun,router,CORE_VERSION,PIPELINE,SATELLITE,TextToSpeechError)
 report={'version':1,'started_at':dt_util.utcnow().isoformat(),'adapter':adapter,'speaker':SPEAKER,
         'microphone':SATELLITE,'speech_volume':speech_volume,'terminal_spoken_output':False if adapter=='active' else 'native_uncontrolled','audible_test_performed':False,
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
   report.update(player_available=True,raop_stream_file=True,player_state=entity.state,satellite_media_player_url=True,observed_volume=entity.volume_level)
   report.pop('error',None);report.pop('reason',None)
   status='configured' if adapter=='active' else adapter
  except Exception as exc:
   report.update(player_available=False,error=type(exc).__name__,reason=str(exc)[:100] if isinstance(exc,ValueError) else type(exc).__name__);status='speaker_unavailable'
  report.update(status=status,updated_at=dt_util.utcnow().isoformat(),playback=router.snapshot())
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

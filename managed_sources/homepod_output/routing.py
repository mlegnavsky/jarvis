"""Hold satellite completion until the explicitly selected HomePod has finished."""
import asyncio
import time
from dataclasses import replace
from math import isfinite

SILENT_URL='/api/jarvis_homepod_output/silence.wav'

def url_terminal_supported(flags,voice_flag=1,speaker_flag=2):
 return bool(flags & voice_flag) and not bool(flags & speaker_flag)

def raop_audio_takeover(entity):
 from pyatv.const import Protocol
 from pyatv.interface import Audio
 return entity.atv.takeover(Protocol.RAOP,Audio)

def current_volume(entity,*,takeover_audio=None):
 # Check availability before takeover, then read the stream protocol rather
 # than Companion's idle/stale zero. Never synthesize a positive fallback.
 level=entity.volume_level
 if isinstance(level,bool) or not isinstance(level,(int,float)) or not isfinite(level) or not 0<=level<=1:
  raise ValueError('homepod_volume_unavailable')
 if getattr(entity,'is_volume_muted',False) is True:return level
 release=(takeover_audio or raop_audio_takeover)(entity)
 try:level=entity.volume_level
 finally:release()
 if isinstance(level,bool) or not isinstance(level,(int,float)) or not isfinite(level) or not 0<=level<=1:
  raise ValueError('homepod_raop_volume_unavailable')
 return level

async def prime_startup_volume(entity,*,takeover_audio=None):
 release=(takeover_audio or raop_audio_takeover)(entity)
 try:
  await entity.async_set_volume_level(.45)
  level=entity.volume_level
  if isinstance(level,bool) or not isinstance(level,(int,float)) or not isfinite(level) or abs(level-.45)>.005:
   raise ValueError('homepod_startup_volume_unconfirmed')
  return level
 finally:release()

async def play_at_volume(entity,media_id,volume,*,takeover_audio=None):
 # Idle devices can prefer a non-responsive Companion/MRP volume path.
 # Prime the RAOP session volume through its own audio implementation, then
 # release before stream_file acquires its own protocol takeover lifecycle.
 release=(takeover_audio or raop_audio_takeover)(entity)
 try:await entity.async_set_volume_level(volume)
 finally:release()
 await entity.async_play_media('music',media_id)

async def play_at_current_volume(entity,media_id,*,takeover_audio=None):
 """Snapshot the device setting at answer start; never restore a fixed default.

 Reapplying that same level through RAOP primes its stream without switching
 to another protocol's stale default. A muted/zero-level device stays silent.
 """
 level=current_volume(entity,takeover_audio=takeover_audio)
 if isinstance(level,bool) or not isinstance(level,(int,float)) or not isfinite(level) or not 0<=level<=1:
  raise ValueError('homepod_volume_unavailable')
 muted=getattr(entity,'is_volume_muted',False) is True
 if muted or level==0:
  return {'volume':level,'muted':muted,'played':False,'reason':'muted' if muted else 'zero_volume'}
 await play_at_volume(entity,media_id,level,takeover_audio=takeover_audio)
 return {'volume':level,'muted':False,'played':True,'reason':'follow_homepod'}

class OutputError(Exception):
 def __init__(self,code,message):
  super().__init__(message);self.code=code

class Router:
 def __init__(self,play,stop):
  self.play=play;self.stop=stop;self.lock=asyncio.Lock();self.active=None;self.tasks={};self.runs={};self.latest=None
  self.started=0;self.completed=0;self.cancelled=0;self.failed=0;self.last_error=None;self.last_playback={}
 async def answer(self,run,output):
  async with self.lock:
   if self.latest is not None and self.latest!=str(run.id):raise asyncio.CancelledError()
   self.active=str(run.id);self.started+=1;started=time.monotonic()
   self.last_playback={'outcome':'playing'}
   run._jarvis_homepod_stop_confirmed=False
   try:
    async with asyncio.timeout(180):await self.play(output['media_id'])
    self.completed+=1;self.last_playback={'outcome':'completed'}
   except asyncio.CancelledError:
    self.cancelled+=1
    self.last_playback={'outcome':'cancelled','reason':getattr(run,'_jarvis_homepod_cancel_reason','unattributed_cancellation'),
                        'task_cancel_requests':asyncio.current_task().cancelling()}
    try:
     async with asyncio.timeout(3):await self.stop()
     run._jarvis_homepod_stop_confirmed=True
    except Exception as exc:self.last_error='stop_'+type(exc).__name__
    raise
   except Exception as exc:
    self.failed+=1;self.last_error=type(exc).__name__
    self.last_playback={'outcome':'failed','reason':type(exc).__name__}
    try:
     async with asyncio.timeout(3):await self.stop()
    except Exception:pass
    raise
   finally:
    self.last_playback['elapsed_s']=round(time.monotonic()-started,3)
    self.active=None
 def activate(self,run_id):
  self.latest=str(run_id)
  for owner,task in list(self.tasks.items()):
   if owner!=self.latest and not task.done():
    run=self.runs.get(owner)
    if run is not None:run._jarvis_homepod_cancel_reason='superseded_by_new_run'
    task.cancel()
 def begin(self,run):
  owner=str(run.id)
  if self.latest is None:self.latest=owner
  if owner!=self.latest:raise asyncio.CancelledError()
  self.tasks[owner]=asyncio.current_task()
  self.runs[owner]=run
 def end(self,run):
  owner=str(run.id)
  if self.tasks.get(owner) is asyncio.current_task():
   self.tasks.pop(owner,None);self.runs.pop(owner,None)
 def snapshot(self):
  return {'started':self.started,'completed':self.completed,'cancelled':self.cancelled,
          'failed':self.failed,'active':self.active is not None,'last_error':self.last_error,
          'last_playback':dict(self.last_playback)}

def install(hass,pipeline_class,router,core_version,pipeline_id,satellite_id,error_class=OutputError):
 if core_version!='2026.6.4':return 'unsupported_core'
 if '_jarvis_homepod_output' in pipeline_class.__dict__:return 'adapter_already_installed'
 original_event=pipeline_class.process_event;original_tts=pipeline_class.text_to_speech
 def matches(run):
  return (run.hass is hass and run.pipeline.id==pipeline_id and run._satellite_id==satellite_id
          and not str(run.id).startswith('synthetic-'))
 def process_event(run,event):
  if matches(run) and str(event.type)=='run-start' and not getattr(run,'_jarvis_suppressed_activation',False):router.activate(str(run.id))
  if matches(run) and getattr(run,'_jarvis_homep…14567 tokens truncated…tional_observation_allowed'],
                'scope':'fictional clock and exposed entity; no physical device or audio',
                'minimum_delay_s':300,'cooldown_s':2400,'automatic_announcements':False}
            import hashlib
            report['personality_memory_test']['prompt_sha256']=hashlib.sha256(COMPANION_INSTRUCTIONS.encode()).hexdigest()
            # A separate synthetic identity turn verifies the deployed prompt.
            async with asyncio.timeout(60):
                identity=await conversation.async_converse(hass,'Jak se jmenuješ?',None,Context(),language='cs',agent_id='conversation.extended_openai_conversation')
            answer=identity.response.as_dict().get('speech',{}).get('plain',{}).get('speech','')
            report['identity_test']={'status':'complete','response':answer,
                'tts_input':spoken_name(answer),'expected_name':'Anička','passed':'anicka' in normalized(answer)}
        except Exception as exc:
            result_report.update(status='error',error=type(exc).__name__,passed=False)
        report['status']='companion_ready' if result_report.get('passed') and report.get('personality_memory_test',{}).get('passed') and report.get('device_awareness_test',{}).get('passed') and report.get('identity_test',{}).get('passed') else 'companion_test_failed'
        await save()

    async def arm(_call=None):
        arm_capture()
        await save()
    hass.services.async_register(DOMAIN,'run_self_test',self_test,schema=vol.Schema({}))
    hass.services.async_register(DOMAIN,'arm_capture',arm,schema=vol.Schema({}))
    hass.services.async_register(DOMAIN,'run_companion_test',companion_test,schema=vol.Schema({}))
    async_track_time_interval(hass,poll,timedelta(seconds=5))
    async_track_state_change_event(hass,[PLAYER,SATELLITE],state_changed)
    async def start(_event=None):
        # No automatic microphone recording after reboot; capture stays opt-in.
        try:
            report['native_turn_probe']=await native_probe(hass,PipelineRun,VoiceCommandSegmenter)
        except Exception as exc:
            report['native_turn_probe']={'status':'error','error':type(exc).__name__}
        report['status']='monitoring'
        await poll()
        report['status']='monitoring' if controller.status=='active' else controller.status
        report['companion_test']={'status':'not_run','reason':'explicit_service_required'}
        report['pipeline_configuration_changed']=False
        try:
            from custom_components.extended_openai_conversation.room_commands import native_resolution_probe
            report['room_commands']=native_resolution_probe(hass)
        except Exception as exc:
            report['room_commands']={'status':'error','error':type(exc).__name__}
        await save()
    if hass.is_running:hass.async_create_task(start())
    else:hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED,start)
    await save()
    return True


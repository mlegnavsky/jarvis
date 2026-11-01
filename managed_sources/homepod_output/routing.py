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
  if matches(run) and getattr(run,'_jarvis_homepod_hold',False):
   if str(event.type)=='tts-start':
    # This satellite is not the speaker. Native TTS_START arms its firmware
    # stop-word detector without an echo reference for the external HomePod.
    # Keep Core diagnostics/controller events, suppress only the native device
    # callback for this synchronous notification; always restore it.
    callback=run.event_callback
    try:
     run.event_callback=lambda _event:None
     return original_event(run,event)
    finally:run.event_callback=callback
   if str(event.type)=='tts-end':
    run._jarvis_homepod_event=event;return None
  if matches(run) and str(event.type)=='intent-progress' and (event.data or {}).get('tts_start_streaming'):
   return None
  return original_event(run,event)
 async def text_to_speech(run,tts_input,override_media_path=None):
  if not matches(run):return await original_tts(run,tts_input,override_media_path)
  router.begin(run)
  run._jarvis_homepod_hold=True;run._jarvis_homepod_event=None
  try:
   await original_tts(run,tts_input,override_media_path)
   event=run._jarvis_homepod_event
   if event is None or not event.data.get('tts_output'):
    router.failed+=1;router.last_error='missing_tts_output';raise ValueError('missing_tts_output')
   await router.answer(run,event.data['tts_output'])
   silent={'media_id':SILENT_URL,'token':'jarvis-homepod-silent','url':SILENT_URL,'mime_type':'audio/wav'}
   original_event(run,replace(event,data={'tts_output':silent}))
  except asyncio.CancelledError:
   control=pipeline_class.__dict__.get('_jarvis_turn_adapter')
   if control is not None and (control.pending or {}).get('run_id')==str(run.id):control.pending=None
   raise
  except Exception as exc:
   control=pipeline_class.__dict__.get('_jarvis_turn_adapter')
   if control is not None and (control.pending or {}).get('run_id')==str(run.id):control.pending=None
   raise error_class(code='tts-failed',message='HomePod output failed; terminal speech remains disabled') from exc
  finally:
   router.end(run)
   del run._jarvis_homepod_hold;del run._jarvis_homepod_event
 pipeline_class.process_event=process_event
 pipeline_class.text_to_speech=text_to_speech
 pipeline_class._jarvis_homepod_output=router
 return 'active'



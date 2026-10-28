"""Hold satellite completion until the explicitly selected HomePod has finished."""
import asyncio
from dataclasses import replace

SILENT_URL='/api/jarvis_homepod_output/silence.wav'

def url_terminal_supported(flags,voice_flag=1,speaker_flag=2):
 return bool(flags & voice_flag) and not bool(flags & speaker_flag)

class OutputError(Exception):
 def __init__(self,code,message):
  super().__init__(message);self.code=code

class Router:
 def __init__(self,play,stop):
  self.play=play;self.stop=stop;self.lock=asyncio.Lock();self.active=None
  self.started=0;self.completed=0;self.cancelled=0;self.failed=0;self.last_error=None
 async def answer(self,run,output):
  async with self.lock:
   self.active=str(run.id);self.started+=1
   try:
    async with asyncio.timeout(180):await self.play(output['media_id'])
    self.completed+=1
   except asyncio.CancelledError:
    self.cancelled+=1
    try:
     async with asyncio.timeout(3):await self.stop()
    except Exception as exc:self.last_error='stop_'+type(exc).__name__
    raise
   except Exception as exc:
    self.failed+=1;self.last_error=type(exc).__name__
    try:
     async with asyncio.timeout(3):await self.stop()
    except Exception:pass
    raise
   finally:self.active=None
 def snapshot(self):
  return {'started':self.started,'completed':self.completed,'cancelled':self.cancelled,
          'failed':self.failed,'active':self.active is not None,'last_error':self.last_error}

def install(hass,pipeline_class,router,core_version,pipeline_id,satellite_id,error_class=OutputError):
 if core_version!='2026.6.4':return 'unsupported_core'
 if '_jarvis_homepod_output' in pipeline_class.__dict__:return 'adapter_already_installed'
 original_event=pipeline_class.process_event;original_tts=pipeline_class.text_to_speech
 def matches(run):
  return (run.hass is hass and run.pipeline.id==pipeline_id and run._satellite_id==satellite_id
          and not str(run.id).startswith('synthetic-'))
 def process_event(run,event):
  if matches(run) and getattr(run,'_jarvis_homepod_hold',False):
   if str(event.type)=='tts-end':
    run._jarvis_homepod_event=event;return None
  if matches(run) and str(event.type)=='intent-progress' and (event.data or {}).get('tts_start_streaming'):
   return None
  return original_event(run,event)
 async def text_to_speech(run,tts_input,override_media_path=None):
  if not matches(run):return await original_tts(run,tts_input,override_media_path)
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
   if control is not None:control.pending=None
   raise
  except Exception as exc:
   control=pipeline_class.__dict__.get('_jarvis_turn_adapter')
   if control is not None:control.pending=None
   raise error_class(code='tts-failed',message='HomePod output failed; terminal speech remains disabled') from exc
  finally:
   del run._jarvis_homepod_hold;del run._jarvis_homepod_event
 pipeline_class.process_event=process_event
 pipeline_class.text_to_speech=text_to_speech
 pipeline_class._jarvis_homepod_output=router
 return 'active'

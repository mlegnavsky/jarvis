"""Version-scoped active Assist PCM tee; no recorder or background microphone."""
from contextlib import aclosing
import inspect

def install(hass,pipeline_class,coordinator,core_version,pipeline_id,satellite_id):
 if core_version!='2026.6.4':return 'unsupported_core'
 required={'audio_stream','stt_vad','sample_rate','sample_width'}
 if not required<=set(inspect.signature(pipeline_class._speech_to_text_stream).parameters):return 'unsupported_stream_api'
 if '_jarvis_speaker_adapter' in pipeline_class.__dict__:return 'adapter_already_installed'
 speech=pipeline_class.speech_to_text;stream=pipeline_class._speech_to_text_stream
 def matches(run):return run.hass is hass and run.pipeline.id==pipeline_id and run._satellite_id==satellite_id
 async def capture_stream(run,audio_stream,stt_vad,sample_rate=16000,sample_width=2):
  capture=getattr(run,'_jarvis_identity_capture',None)
  if capture is None or sample_rate!=16000 or sample_width!=2:
   async with aclosing(stream(run,audio_stream,stt_vad,sample_rate,sample_width)) as native:
    async for chunk in native:yield chunk
   return
  async def tee():
   async with aclosing(aiter(audio_stream)) as source:
    async for chunk in source:
     probability=getattr(chunk,'speech_probability',None) or 0
     if probability>.6:capture['started']=True
     if capture['started']:
      remaining=384000-len(capture['pcm'])
      if remaining:
       part=chunk.audio[:remaining];capture['pcm'].extend(part)
       if probability>.6:capture['voiced']+=len(part)/32000
      elif probability>.6:capture['truncated']=True
     yield chunk
  async with aclosing(tee()) as source:
   async with aclosing(stream(run,source,stt_vad,sample_rate,sample_width)) as native:
    async for chunk in native:yield chunk
 async def capture_speech(run,metadata,stream):
  if not matches(run) or metadata.sample_rate!=16000:return await speech(run,metadata,stream)
  run._jarvis_identity_capture={'pcm':bytearray(),'voiced':0.,'started':False,'truncated':False}
  try:
   text=await speech(run,metadata,stream)
   capture=run._jarvis_identity_capture
   # An overlong/mixed interval is never assigned using just its first speaker.
   if capture['truncated']:
    await coordinator.complete(satellite_id,b'',0,text)
   else:
    await coordinator.complete(satellite_id,bytes(capture['pcm']),capture['voiced'],text)
   return text
  finally:
   run._jarvis_identity_capture['pcm'].clear()
   del run._jarvis_identity_capture
 pipeline_class._speech_to_text_stream=capture_stream
 pipeline_class.speech_to_text=capture_speech
 pipeline_class._jarvis_speaker_adapter=coordinator
 return 'active'

"""Version-scoped active Assist PCM tee; no recorder or background microphone."""
from contextlib import aclosing
import inspect
from dataclasses import replace

def install(hass,pipeline_class,coordinator,core_version,pipeline_id,satellite_id):
 if core_version!='2026.6.4':return 'unsupported_core'
 required={'audio_stream','stt_vad','sample_rate','sample_width'}
 if not required<=set(inspect.signature(pipeline_class._speech_to_text_stream).parameters):return 'unsupported_stream_api'
 if '_jarvis_speaker_adapter' in pipeline_class.__dict__:return 'adapter_already_installed'
 speech=pipeline_class.speech_to_text;stream=pipeline_class._speech_to_text_stream
 native_intent=getattr(pipeline_class,'recognize_intent',None)
 async def recognize_intent(run,*args,**kwargs):
  if not (run.hass is hass and run._satellite_id==satellite_id):return await native_intent(run,*args,**kwargs)
  if run.pipeline.id!=pipeline_id or getattr(run.intent_agent,'id',None)!='conversation.extended_openai_conversation':
   from homeassistant.components.assist_pipeline.pipeline import IntentRecognitionError
   raise IntentRecognitionError(code='voice-authorization-route-required',message='Use the voice-authorized Jarvis pipeline')
  original_pipeline=run.pipeline;original_agent_only=run._intent_agent_only
  try:
   run.pipeline=replace(run.pipeline,prefer_local_intents=False);run._intent_agent_only=True
   return await native_intent(run,*args,**kwargs)
  finally:run.pipeline=original_pipeline;run._intent_agent_only=original_agent_only
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
  # Do not learn from any turn overlapping the TV or our own speaker output.
  def playback_active():
   states=getattr(hass,'states',None)
   if states is None:return None
   values=[states.get(e) for e in ('media_player.homepod_obyvak_homepod_obyvak','media_player.obyvaci_pokoj_obyvaci_pokoj')]
   return any(s and s.state in ('playing','buffering','on') for s in values)
  playback=playback_active()
  try:
   text=await speech(run,metadata,stream)
   capture=run._jarvis_identity_capture
   # An overlong/mixed interval is never assigned using just its first speaker.
   if capture['truncated']:
    await coordinator.complete(satellite_id,b'',0,text)
   else:
    options={'playback':playback or playback_active(),'context_id':getattr(getattr(run,'context',None),'id',None)} if hasattr(coordinator,'enforce') else {}
    await coordinator.complete(satellite_id,bytes(capture['pcm']),capture['voiced'],text,**options)
   return text
  finally:
   run._jarvis_identity_capture['pcm'].clear()
   del run._jarvis_identity_capture
 pipeline_class._speech_to_text_stream=capture_stream
 pipeline_class.speech_to_text=capture_speech
 if native_intent is not None:
  pipeline_class.recognize_intent=recognize_intent
  pipeline_class._jarvis_voice_intent_guard=True
 pipeline_class._jarvis_speaker_adapter=coordinator
 return 'active'

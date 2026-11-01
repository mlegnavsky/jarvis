"""Resume one existing dialogue after a native ESPHome abort during playback.

This observes the device's explicit abort signal; it does not detect acoustic
speech. Generic task cancellations, errors, replacement pipelines and shutdown
never create listening. No audio, transcript or identity is kept here.
"""
import asyncio


class AbortResume:
 def __init__(self,router,allowed,resume,pending,cleanup=None):
  self.router=router;self.allowed=allowed;self.resume=resume;self.pending=pending;self.cleanup=cleanup;self.cleaned=0
  self.jobs={};self.native_aborts=0;self.resumed=0;self.blocked=0;self.failed=0;self.last_reason=None

 def snapshot(self):
  return {'cleaned':self.cleaned,'native_aborts':self.native_aborts,'resumed':self.resumed,'blocked':self.blocked,'failed':self.failed,
          'pending':bool(self.jobs),'last_reason':self.last_reason}

 def capture(self,entity):
  owner=self.router.active
  run=self.router.runs.get(owner)
  task=getattr(entity,'_pipeline_task',None)
  output_task=self.router.tasks.get(owner)
  # Native satellite wrappers and inner output tasks can differ. Bind the run
  # by its actual bound native event receiver, never by task equality alone.
  if (not run or not task or not output_task or
      getattr(getattr(run,'event_callback',None),'__self__',None) is not entity):
   self.last_reason='no_owned_native_run';return None
  conversation=getattr(entity,'_conversation_id',None)
  pending=self.pending()
  if (not getattr(run,'_jarvis_tv_continue',False) or not pending or
      pending.get('run_id')!=owner or not pending.get('conversation_id') or
      conversation!=pending['conversation_id']):pending=None
  return owner,run,task,output_task,conversation,dict(pending) if pending else None

 def schedule(self,entity,captured):
  if captured is None:return
  owner,run,task,output_task,conversation,pending=captured
  if owner in self.jobs:return
  # At most one pending resume; an explicit later interruption supersedes it.
  for old in list(self.jobs.values()):old.cancel()
  job=entity.hass.async_create_task(self._after(entity,owner,run,task,output_task,conversation,pending))
  self.jobs[owner]=job
  def done(_):
   if self.jobs.get(owner) is job:self.jobs.pop(owner,None)
  job.add_done_callback(done)

 async def _after(self,entity,owner,run,task,output_task,conversation,pending):
  try:
   async with asyncio.timeout(6):
    for owned in dict.fromkeys((task,output_task)):
     try:await asyncio.shield(owned)
     except asyncio.CancelledError:
      if asyncio.current_task().cancelling():raise
   await asyncio.sleep(0)
   current=getattr(entity,'_pipeline_task',None)
   if (self.router.latest!=owner or self.router.active is not None or
       not getattr(run,'_jarvis_homepod_stop_confirmed',False) or
       current is not None and current is not task or
       getattr(entity,'_conversation_id',None)!=conversation or
       getattr(entity,'_is_announcing',False) or not getattr(entity.hass,'is_running',True) or not getattr(entity,'available',True)):
    self.blocked+=1;self.last_reason='session_changed_or_output_not_stopped';return
   entity.tts_response_finished()
   self.cleaned+=1
   continuing=pending is not None and self.allowed(entity)
   if self.cleanup:await self.cleanup(run,continuing)
   if not continuing:
    self.last_reason='native_abort_cleaned_no_continuation';return
   async with asyncio.timeout(15):await self.resume(entity,pending)
   self.resumed+=1;self.last_reason='native_abort_resumed'
  except asyncio.CancelledError:raise
  except Exception as exc:
   self.failed+=1;self.last_reason=type(exc).__name__
   if self.cleanup:await self.cleanup(run,False)


def install_abort_resume(hass,satellite_class,router,core_version,satellite_id,
                         allowed,resume,pending,cleanup=None):
 if core_version!='2026.6.4' or not hasattr(satellite_class,'_abort_pipeline'):
  return None
 if '_jarvis_homepod_abort_resume' in satellite_class.__dict__:return None
 original=satellite_class._abort_pipeline
 gate=AbortResume(router,allowed,resume,pending,cleanup)
 def abort(entity):
  matches=entity.hass is hass and entity.entity_id==satellite_id
  captured=gate.capture(entity) if matches else None
  if matches:
   gate.native_aborts+=1
   run=router.runs.get(router.active)
   if run is not None:run._jarvis_homepod_cancel_reason='native_satellite_abort'
  # Native subscribed handle_pipeline_stop may already be a bound method.
  # Its dynamic _abort_pipeline call reaches this hook regardless of setup order.
  original(entity)
  gate.schedule(entity,captured)
 satellite_class._abort_pipeline=abort
 satellite_class._jarvis_homepod_abort_resume=gate
 return gate

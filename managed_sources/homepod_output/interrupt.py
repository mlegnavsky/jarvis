"""Resume one existing dialogue after a native ESPHome abort during playback.

This observes the device's explicit abort signal; it does not detect acoustic
speech. Generic task cancellations, errors, replacement pipelines and shutdown
never create listening. No audio, transcript or identity is kept here.
"""
import asyncio


class AbortResume:
 def __init__(self,router,allowed,resume,pending):
  self.router=router;self.allowed=allowed;self.resume=resume;self.pending=pending
  self.jobs={};self.resumed=0;self.blocked=0;self.failed=0;self.last_reason=None

 def snapshot(self):
  return {'resumed':self.resumed,'blocked':self.blocked,'failed':self.failed,
          'pending':bool(self.jobs),'last_reason':self.last_reason}

 def capture(self,entity):
  owner=self.router.active
  run=self.router.runs.get(owner)
  task=getattr(entity,'_pipeline_task',None)
  pending=self.pending()
  if (not run or not task or self.router.tasks.get(owner) is not task or
      not getattr(run,'_jarvis_tv_continue',False) or not pending or
      pending.get('run_id')!=owner or not pending.get('conversation_id') or
      getattr(entity,'_conversation_id',None)!=pending['conversation_id']):
   return None
  return owner,run,task,dict(pending)

 def schedule(self,entity,captured):
  if captured is None:return
  owner,run,task,pending=captured
  if owner in self.jobs:return
  # At most one pending resume; an explicit later interruption supersedes it.
  for old in list(self.jobs.values()):old.cancel()
  job=entity.hass.async_create_task(self._after(entity,owner,run,task,pending))
  self.jobs[owner]=job
  def done(_):
   if self.jobs.get(owner) is job:self.jobs.pop(owner,None)
  job.add_done_callback(done)

 async def _after(self,entity,owner,run,task,pending):
  try:
   try:
    async with asyncio.timeout(6):await asyncio.shield(task)
   except asyncio.CancelledError:
    if asyncio.current_task().cancelling():raise
   # Let the native satellite await/finally clear the old task reference.
   await asyncio.sleep(0)
   current=getattr(entity,'_pipeline_task',None)
   if (self.router.latest!=owner or self.router.active is not None or
       not getattr(run,'_jarvis_homepod_stop_confirmed',False) or
       current is not None and current is not task or
       getattr(entity,'_conversation_id',None)!=pending['conversation_id'] or
       getattr(entity,'_is_announcing',False) or not self.allowed(entity)):
    self.blocked+=1;self.last_reason='session_changed_or_output_not_stopped';return
   async with asyncio.timeout(15):await self.resume(entity,pending)
   self.resumed+=1;self.last_reason='native_abort_resumed'
  except asyncio.CancelledError:raise
  except Exception as exc:
   self.failed+=1;self.last_reason=type(exc).__name__


def install_abort_resume(hass,satellite_class,router,core_version,satellite_id,
                         allowed,resume,pending):
 if core_version!='2026.6.4' or not hasattr(satellite_class,'handle_pipeline_stop'):
  return None
 if '_jarvis_homepod_abort_resume' in satellite_class.__dict__:return None
 original=satellite_class.handle_pipeline_stop
 gate=AbortResume(router,allowed,resume,pending)
 async def stop(entity,abort):
  matches=entity.hass is hass and entity.entity_id==satellite_id
  captured=gate.capture(entity) if matches and abort else None
  await original(entity,abort)
  gate.schedule(entity,captured)
 satellite_class.handle_pipeline_stop=stop
 satellite_class._jarvis_homepod_abort_resume=gate
 return gate

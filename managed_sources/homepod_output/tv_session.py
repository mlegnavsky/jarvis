"""Own only the television pause introduced for a Jarvis speech session."""
import asyncio

FINGERPRINT_KEYS=('media_content_id','media_title','app_id','app_name','source')

def fingerprint(state):
 attributes=(state or {}).get('attributes') or {}
 return tuple(attributes.get(key) for key in FINGERPRINT_KEYS)

class TVSession:
 def __init__(self,read_state,call_service):
  self.read_state=read_state;self.call_service=call_service
  self._owner=None;self._lock=asyncio.Lock()
  self.paused=0;self.resumed=0;self.resume_requested=0;self.discarded=0;self.failed=0;self.last_error=None
 def observe(self,state):
  """Call for state updates, including intermediate external play/off changes."""
  if self._owner is not None and ((state or {}).get('state')!='paused' or fingerprint(state)!=self._owner):
   self._owner=None;self.discarded+=1
 async def acquire(self):
  async with self._lock:
   state=self.read_state()
   if self._owner is not None:
    self.observe(state)
    # A second answer never replaces an invalidated lease in the same call.
    return
   if not state or state.get('state')!='playing':return
   original=fingerprint(state)
   try:
    async with asyncio.timeout(3):await self.call_service('media_pause')
    async with asyncio.timeout(1.2):
     while True:
      state=self.read_state()
      if fingerprint(state)!=original:
       self.discarded+=1;return
      if (state or {}).get('state')=='paused':break
      if not state or state.get('state') not in ('playing','buffering'):
       self.discarded+=1;return
      await asyncio.sleep(.05)
    self._owner=original;self.paused+=1
   except Exception as exc:
    self.failed+=1;self.last_error='pause_'+type(exc).__name__
 async def release(self,*,if_current=None):
  async with self._lock:
   if if_current is not None and not if_current():return
   owner=self._owner;self._owner=None
   if owner is None:return
   state=self.read_state()
   if not state or state.get('state')!='paused' or fingerprint(state)!=owner:
    self.discarded+=1;return
   try:
    async with asyncio.timeout(3):await self.call_service('media_play')
    self.resume_requested+=1
    async with asyncio.timeout(1.2):
     while True:
      state=self.read_state()
      if not state or fingerprint(state)!=owner:
       self.discarded+=1;return
      if state.get('state')=='playing':break
      if state.get('state') not in ('paused','buffering'):
       self.discarded+=1;return
      await asyncio.sleep(.05)
    self.resumed+=1
   except Exception as exc:
    self.failed+=1;self.last_error='resume_'+type(exc).__name__
 def snapshot(self):
  return {'owned':self._owner is not None,'paused':self.paused,'resumed':self.resumed,
          'resume_requested':self.resume_requested,'discarded':self.discarded,'failed':self.failed,'last_error':self.last_error}

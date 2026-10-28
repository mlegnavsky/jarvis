"""On-turn observations only; no event subscriptions, announcements or services."""
from datetime import datetime
import re
import time
import unicodedata


def norm(text):return ''.join(c for c in unicodedata.normalize('NFKD',text.casefold()) if not unicodedata.combining(c))

class ConversationAwareness:
 def __init__(self,clock=time.time):
  self.sessions={};self.clock=clock;self.episodes={};self.last_offer=None
 def context(self,conversation,entities,text):
  now=self.clock()
  slot=self.sessions.setdefault(conversation,{'turns':0})
  while len(self.sessions)>32:self.sessions.pop(next(iter(self.sessions)))
  slot['turns']+=1
  current=[];candidates=[]
  refusal=bool(re.match(r'^\s*(ne\b|nechci\b|nepotrebuji\b|nepotrebuju\b)',norm(text)))
  casual=bool(re.fullmatch(r'\s*(ahoj|jak se mas|co noveho|povidej|tak co)[?.! ]*',norm(text)))
  related=bool(re.search(r'\b(varim|varime|vareni|recept|jidlo|veceri|obed|pecu|peceme)\b',norm(text)))
  for item in entities:
   entity=str(item.get('entity_id',''))
   if entity.split('.',1)[0] not in {'light','switch','sensor','binary_sensor','climate','fan','media_player'}:continue
   state=str(item.get('state','unknown'))[:80]
   entry={'entity_id':entity[:160],'name':str(item.get('name',entity))[:120],'state':state,
          'last_changed':str(item.get('last_changed',''))[:40]}
   if state not in {'unknown','unavailable'}:current.append(entry)
   cooking=bool(re.search(r'sporak|troub|plotyn|varna deska',norm(entry['name'])))
   if not cooking or state.casefold() not in {'on','heating','cooking','running'}:continue
   try:
    changed=datetime.fromisoformat(entry['last_changed'].replace('Z','+00:00'))
    if changed.tzinfo is None:continue
    started=changed.timestamp()
    if not 0<=now-started<=86400:continue
   except (ValueError,OverflowError):continue
   episode=self.episodes.get(entity)
   if not episode or episode['started']!=started:
    episode={'started':started,'seen_at':now,'offered':False}
    self.episodes[entity]=episode
   if refusal:episode['offered']=True
   if not episode['offered'] and now-max(started,episode['seen_at'])>=300:candidates.append(entry)
  self.episodes={key:value for key,value in self.episodes.items() if 0<=now-value['seen_at']<=86400}
  while len(self.episodes)>128:self.episodes.pop(next(iter(self.episodes)))
  direct=bool(re.match(r'\s*(kolik|zhasni|zapni|vypni|nastav|odemkni|zamkni)\b',norm(text)))
  allowed=bool(candidates and (casual or related) and not direct and slot['turns']>=2
               and (self.last_offer is None or now-self.last_offer>=2400))
  if allowed:
   candidates=candidates[:1];self.last_offer=now
   self.episodes[candidates[0]['entity_id']]['offered']=True
  return {'scope':'current explicitly exposed states; conversation only',
          'current_devices':current[:30],
          'observation_candidates':candidates if allowed else [],
          'optional_observation_allowed':allowed,
          'minimum_observation_delay_s':300,'offer_cooldown_s':2400,
          'cooking_contents_known':False,'missing_device_is_not_proof_of_absence':True}

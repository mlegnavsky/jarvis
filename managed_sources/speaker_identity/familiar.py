"""Bounded optional names from recurring active speech; never authorization.

Private embeddings only, no transcripts/audio. Original identity banks are never
changed. Similarity and repeat counts are familiarity heuristics, not certainty.
"""
import json
import re
import hashlib
from uuid import uuid4
if __package__:
 from .policy import unit,similarity,norm,MODEL_ID
else:
 from policy import unit,similarity,norm,MODEL_ID

class FamiliarVoices:
 def __init__(self,profiles):self.profiles=profiles;self.pending={}
 def db(self):
  db=self.profiles._db()
  db.execute('CREATE TABLE IF NOT EXISTS familiar_voices (id TEXT PRIMARY KEY,name TEXT,samples TEXT,seen REAL,asked REAL,ticks INTEGER)')
  db.execute('DELETE FROM familiar_voices WHERE seen<?',(self.profiles.clock()-30*86400,))
  db.commit();return db
 def score(self,v,refs):
  values=sorted((similarity(v,r) for r in refs),reverse=True)
  return sum(values[:2])/min(2,len(values)) if values and min(values)>=.60 else -1
 def observe(self,item,conversation):
  data=item.get('result') or {};q=data.get('quality') or {}
  if (data.get('status')!='ok' or data.get('model')!=MODEL_ID or item.get('voiced',0)<3 or item.get('playback') is not False
      or q.get('status')!='ok' or q.get('rms',0)<.004 or q.get('clipped_fraction',1)>.02):return {}
  try:
   v=unit(data['vector']);windows=[unit(w) for w in data.get('windows',[])]
   if len(windows)<2 or any(similarity(v,w)<.65 for w in windows):return {}
  except (ValueError,TypeError,KeyError):return {}
  stamp=item.get('utterance')
  text=norm(item.get('text') or '')
  if not isinstance(stamp,str) or not stamp or not conversation or not text:return {}
  text_hash=hashlib.sha256(text.encode()).hexdigest()
  with self.db() as db:
   db.execute('BEGIN IMMEDIATE')
   rows=[(key,name,json.loads(raw),seen,asked,ticks) for key,name,raw,seen,asked,ticks in db.execute('SELECT * FROM familiar_voices')]
   if any(s['hash']==stamp for _,_,ss,_,_,_ in rows for s in ss):return {}
   ranked=sorted(((self.score(v,[s['v'] for s in samples]),key,name,samples,asked,ticks)
                  for key,name,samples,seen,asked,ticks in rows),reverse=True)
   if ranked and ranked[0][0]>=.75:
    score,key,name,samples,asked,ticks=ranked[0]
    if len(ranked)>1 and score-ranked[1][0]<.12:return {}
    refs=[s['v'] for s in samples]
    for w in windows:
     if self.score(w,refs)<.70:return {}
     for other_id,_,other,_,_,_ in rows:
      if other_id!=key and self.score(w,refs)-self.score(w,[s['v'] for s in other])<.12:return {}
   else:
    # A nearby ambiguous cluster is not a new identity.
    if ranked and ranked[0][0]>=.60:return {}
    if len(rows)>=16:return {}
    key=uuid4().hex;name=None;samples=[];asked=0;ticks=0
   if not any(s.get('text_hash')==text_hash for s in samples):
    samples=(samples+[{'v':v,'hash':stamp,'text_hash':text_hash,'session':str(conversation)}])[-12:]
   ready=len(samples)>=6 and len({s['session'] for s in samples})>=3
   # Query must match the pre-existing references; no promotion/grants follow.
   db.execute('INSERT OR REPLACE INTO familiar_voices VALUES (?,?,?,?,?,?)',
              (key,name,json.dumps(samples),self.profiles.clock(),asked,ticks))
   return {'id':key,'name':name,'ready':ready}
 def dialog(self,device,text,match,*,allow_ask):
  now=self.profiles.clock();self.pending={k:v for k,v in self.pending.items() if 0<=now-v['at']<=120}
  if not allow_ask or not match or not match.get('ready'):return {}
  key=match['id'];slot=self.pending.get(device)
  introduction=re.fullmatch(r'(?:jsem|jmenuji se) ([^\W\d_]{2,20}(?: [^\W\d_]{2,20})?)',text.strip().rstrip('.!?'),flags=re.I)
  with self.db() as db:
   row=db.execute('SELECT name,asked,ticks FROM familiar_voices WHERE id=?',(key,)).fetchone()
   if row is None:return {}
   name,asked,ticks=row
   if slot and slot['id']==key and introduction and not name:
    name=introduction[1];db.execute('UPDATE familiar_voices SET name=? WHERE id=?',(name,key));self.pending.pop(device,None)
    return {'local_reply':'Děkuji, uložila jsem si oslovení '+name+'.'}
   if name:
    db.execute('UPDATE familiar_voices SET ticks=ticks+1 WHERE id=?',(key,))
    return {'familiar_address':name} if ticks%6==0 else {}
   if now-asked>=86400 or asked==0:
    db.execute('UPDATE familiar_voices SET asked=? WHERE id=?',(now,key))
    self.pending[device]={'id':key,'at':now}
    while len(self.pending)>4:self.pending.pop(next(iter(self.pending)))
    return {'ask_name':True}
  return {}
 def summary(self):
  with self.db() as db:
   rows=db.execute('SELECT name,samples FROM familiar_voices').fetchall()
  return {'mode':'personalization_only','clusters':len(rows),'named':sum(bool(r[0]) for r in rows),
          'samples':sum(len(json.loads(r[1])) for r in rows),'raw_audio_saved':False,'grants_permissions':False}
 def forget(self,name):
  with self.db() as db:
   for key,label in db.execute('SELECT id,name FROM familiar_voices').fetchall():
    if label and norm(label)==norm(name):db.execute('DELETE FROM familiar_voices WHERE id=?',(key,))
  self.pending.clear()

"""Explicit enrollment and conservative local voiceprint matching. Not authentication."""
import json
import math
from pathlib import Path
import re
import sqlite3
import time
import unicodedata
from uuid import uuid4

MODEL_ID='campplus-aa3cfc16-v1'
def norm(text):
 return ' '.join(re.findall(r'\w+', ''.join(c for c in unicodedata.normalize('NFKD',text.casefold()) if not unicodedata.combining(c))))
def unit(vector):
 if not isinstance(vector,(list,tuple)) or not 2<=len(vector)<=1024:raise ValueError('invalid_vector')
 values=[float(v) for v in vector]
 if not all(math.isfinite(v) for v in values):raise ValueError('invalid_vector')
 size=math.sqrt(sum(v*v for v in values))
 if size<1e-8:raise ValueError('invalid_vector')
 return [v/size for v in values]
def similarity(a,b):return sum(x*y for x,y in zip(a,b)) if len(a)==len(b) else -1
def centroid(vectors):return unit([sum(v[i] for v in vectors)/len(vectors) for i in range(len(vectors[0]))])

class VoiceProfiles:
 def __init__(self,path,clock=time.time):
  self.path=Path(path);self.clock=clock;self.pending={}
 def _db(self):
  self.path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
  if self.path.is_symlink():raise ValueError('unsafe_profile_path')
  db=sqlite3.connect(self.path,timeout=3)
  self.path.chmod(0o600)
  db.execute('CREATE TABLE IF NOT EXISTS voices (name TEXT PRIMARY KEY, label TEXT, model TEXT, samples TEXT, created REAL, voice_id TEXT)')
  if 'voice_id' not in {row[1] for row in db.execute('PRAGMA table_info(voices)')}:
   db.execute('ALTER TABLE voices ADD COLUMN voice_id TEXT')
  for (name,) in db.execute('SELECT name FROM voices WHERE voice_id IS NULL').fetchall():
   db.execute('UPDATE voices SET voice_id=? WHERE name=?',(uuid4().hex,name))
  return db
 def count(self):
  with self._db() as db:return db.execute('SELECT count(*) FROM voices WHERE model=?',(MODEL_ID,)).fetchone()[0]
 def begin(self,device,name):
  if not device or not isinstance(name,str) or not re.fullmatch(r'[^\W\d_][^\W\d_ -]*(?:[ -][^\W\d_]+){0,2}',name,re.UNICODE) or len(name)>40:
   return {'status':'invalid_name'}
  key=norm(name)
  with self._db() as db:
   if db.execute('SELECT 1 FROM voices WHERE name=?',(key,)).fetchone():return {'status':'exists'}
   if self.count()>=16:return {'status':'full'}
  self.pending[device]={'name':key,'label':name,'at':self.clock(),'samples':[]}
  while len(self.pending)>4:self.pending.pop(next(iter(self.pending)))
  return {'status':'enrolling','samples':0,'name':name}
 def cancel(self,device):self.pending.pop(device,None)
 def sample(self,device,vector,seconds):
  slot=self.pending.get(device)
  if not slot or not 0<=self.clock()-slot['at']<=300:
   self.cancel(device);return {'status':'not_enrolling'}
  v=unit(vector)
  if seconds<3:return {'status':'too_short','samples':len(slot['samples'])}
  if slot['samples'] and min(similarity(v,x) for x in slot['samples'])<.65:
   # Reject only this sample. Keep the accepted anchor so repeated unrelated
   # voices can neither replace it nor silently become a new profile.
   return {'status':'inconsistent','samples':len(slot['samples'])}
  slot['samples'].append(v)
  if len(slot['samples'])<3:return {'status':'enrolling','samples':len(slot['samples']),'name':slot['label']}
  with self._db() as db:
   # Another active device may have enrolled the same label meanwhile.
   if db.execute('SELECT 1 FROM voices WHERE name=?',(slot['name'],)).fetchone():
    self.cancel(device);return {'status':'exists'}
   voice_id=uuid4().hex
   db.execute('INSERT INTO voices VALUES (?,?,?,?,?,?)',(slot['name'],slot['label'],MODEL_ID,json.dumps(slot['samples']),self.clock(),voice_id))
  self.cancel(device)
  return {'status':'enrolled','name':slot['label'],'profile':slot['name'],'memory_id':voice_id}
 def identify(self,vector):
  v=unit(vector);scores=[]
  with self._db() as db:
   for name,label,samples,voice_id in db.execute('SELECT name,label,samples,voice_id FROM voices WHERE model=?',(MODEL_ID,)):
    vectors=json.loads(samples)
    scores.append((similarity(v,centroid(vectors)),name,label,voice_id))
  scores.sort(reverse=True)
  if not scores or scores[0][0]<.75:return {'status':'unknown'}
  if len(scores)>1 and scores[0][0]-scores[1][0]<.12:return {'status':'ambiguous'}
  score,name,label,voice_id=scores[0]
  return {'status':'recognized','profile':name,'name':label,'memory_id':voice_id,'score':round(score,4)}
 def improve(self,name,vector,seconds):
  result=self.identify(vector)
  if seconds<3 or result.get('profile')!=norm(name) or result.get('score',0)<.85:return False
  with self._db() as db:
   samples=json.loads(db.execute('SELECT samples FROM voices WHERE name=?',(norm(name),)).fetchone()[0])
   samples=(samples+[unit(vector)])[-8:]
   db.execute('UPDATE voices SET samples=? WHERE name=?',(json.dumps(samples),norm(name)))
  return True
 def forget(self,name):
  key=norm(name)
  with self._db() as db:
   row=db.execute('SELECT voice_id FROM voices WHERE name=?',(key,)).fetchone()
   db.execute('DELETE FROM voices WHERE name=?',(key,))
  for device,slot in list(self.pending.items()):
   if slot['name']==key:self.cancel(device)
  return row[0] if row else None


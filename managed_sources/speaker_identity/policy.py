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

def profile_score(vector,vectors,policy='centroid'):
 v=unit(vector);refs=[unit(x) for x in vectors]
 if not refs or any(len(x)!=len(v) for x in refs):raise ValueError('embedding_dimensions')
 if policy=='centroid':return similarity(v,centroid(refs))
 if policy not in ('top_two_mean_v1','top_two_mean_calibrated_v1'):raise ValueError('invalid_matching_policy')
 refs=list({tuple(round(x,12) for x in ref):ref for ref in refs}.values())
 if len(refs)<2:raise ValueError('independent_references_required')
 scores=sorted((similarity(v,x) for x in refs),reverse=True)
 if policy=='top_two_mean_calibrated_v1' and scores[1]<.6:return scores[1]
 return sum(scores[:2])/2

def profile_threshold(policy):
 if policy=='top_two_mean_calibrated_v1':return .65
 if policy in ('centroid','top_two_mean_v1'):return .75
 raise ValueError('invalid_matching_policy')

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
  db.execute('CREATE TABLE IF NOT EXISTS voice_anchors (voice_id TEXT PRIMARY KEY,samples TEXT NOT NULL)')
  db.execute('INSERT OR IGNORE INTO voice_anchors SELECT voice_id,samples FROM voices')
  db.execute('CREATE TABLE IF NOT EXISTS voice_authorizations (voice_id TEXT PRIMARY KEY)')
  db.execute('CREATE TABLE IF NOT EXISTS voice_matching_policies (voice_id TEXT PRIMARY KEY,policy TEXT NOT NULL)')
  db.execute('CREATE TABLE IF NOT EXISTS voice_meta (key TEXT PRIMARY KEY,value TEXT)')
  db.commit()
  return db
 def anchors(self,voice_id):
  with self._db() as db:
   row=db.execute('SELECT samples FROM voice_anchors WHERE voice_id=?',(voice_id,)).fetchone()
   return json.loads(row[0]) if row else []
 def is_authorized(self,voice_id):
  with self._db() as db:
   return db.execute('SELECT 1 FROM voice_authorizations a JOIN voices v ON v.voice_id=a.voice_id WHERE a.voice_id=?',(voice_id,)).fetchone() is not None
 def bootstrap_authorization(self,name):
  # Explicit deployment option, consumed once. Re-enrollment cannot inherit it.
  with self._db() as db:
   db.execute('BEGIN IMMEDIATE')
   if db.execute("SELECT 1 FROM voice_meta WHERE key='authorization_bootstrap'").fetchone():return False
   rows=db.execute('SELECT voice_id FROM voices WHERE name=? AND model=?',(norm(name),MODEL_ID)).fetchall()
   if len(rows)!=1:raise ValueError('explicit_existing_profile_required')
   db.execute('INSERT INTO voice_authorizations VALUES (?)',(rows[0][0],))
   db.execute("INSERT INTO voice_meta VALUES ('authorization_bootstrap','consumed')")
   return True
 def authorization_summary(self):
  with self._db() as db:
   return {'authorized_profiles':db.execute('SELECT count(*) FROM voice_authorizations a JOIN voices v ON v.voice_id=a.voice_id').fetchone()[0],
           'anchor_profiles':db.execute('SELECT count(*) FROM voice_anchors a JOIN voices v ON v.voice_id=a.voice_id').fetchone()[0]}
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
 def match_diagnostics(self,vector):
  """Numeric match evidence only: no names, stable IDs or embeddings."""
  v=unit(vector);scores=[]
  with self._db() as db:
   for samples,policy in db.execute("SELECT v.samples,COALESCE(p.policy,'centroid') FROM voices v LEFT JOIN voice_matching_policies p ON p.voice_id=v.voice_id WHERE v.model=?",(MODEL_ID,)):
    scores.append((profile_score(v,json.loads(samples),policy),profile_threshold(policy)))
  scores.sort(reverse=True)
  margin=scores[0][0]-scores[1][0] if len(scores)>1 else None
  return {'best_score':round(scores[0][0],4) if scores else None,
          'margin':round(margin,4) if margin is not None else None,
          'threshold':scores[0][1] if scores else .75,'required_margin':.12}
 def identify(self,vector):
  v=unit(vector);scores=[]
  with self._db() as db:
   for name,label,samples,voice_id,policy in db.execute("SELECT v.name,v.label,v.samples,v.voice_id,COALESCE(p.policy,'centroid') FROM voices v LEFT JOIN voice_matching_policies p ON p.voice_id=v.voice_id WHERE v.model=?",(MODEL_ID,)):
    vectors=json.loads(samples)
    scores.append((profile_score(v,vectors,policy),name,label,voice_id,profile_threshold(policy)))
  scores.sort(reverse=True)
  if not scores or scores[0][0]<scores[0][4]:return {'status':'unknown'}
  if len(scores)>1 and scores[0][0]-scores[1][0]<.12:return {'status':'ambiguous'}
  score,name,label,voice_id,threshold=scores[0]
  return {'status':'recognized','profile':name,'name':label,'memory_id':voice_id,'score':score}
 def improve(self,name,vector,seconds):
  # Explicit improvement now goes through staged adaptation, never live mutation.
  return False
 def forget(self,name):
  key=norm(name)
  with self._db() as db:
   row=db.execute('SELECT voice_id FROM voices WHERE name=?',(key,)).fetchone()
   db.execute('DELETE FROM voices WHERE name=?',(key,))
   if row:
    if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='owner_calibration_sessions'").fetchone():
     db.execute('DELETE FROM owner_calibration_samples WHERE session IN (SELECT id FROM owner_calibration_sessions WHERE voice_id=?)',(row[0],))
     db.execute('DELETE FROM owner_calibration_sessions WHERE voice_id=?',(row[0],))
    db.execute('DELETE FROM voice_authorizations WHERE voice_id=?',(row[0],))
    db.execute('DELETE FROM voice_anchors WHERE voice_id=?',(row[0],))
    for table in ('voice_candidates','voice_validation','voice_versions','voice_aliases','voice_provenance','voice_matching_policies','voice_matching_versions','voice_matching_requests'):
     if db.execute('SELECT 1 FROM sqlite_master WHERE type=? AND name=?',('table',table)).fetchone():
      db.execute('DELETE FROM '+table+' WHERE voice_id=?',(row[0],))
  for device,slot in list(self.pending.items()):
   if slot['name']==key:self.cancel(device)
  return row[0] if row else None


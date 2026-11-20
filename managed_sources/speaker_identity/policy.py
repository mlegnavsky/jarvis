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

COHORT_POLICY='cohort_margin_v1'
COHORT_PARAMETERS={'whole_threshold':.55,'window_threshold':.50,'second_reference_floor':.50,'exclusion_margin':.20,'inter_profile_margin':.12,'strict_threshold':.75}
def cohort_bank(bank):
 if not isinstance(bank,dict) or set(bank) not in ({'positive','negative'},{'positive','negative','negative_sources'}):raise ValueError('invalid_cohort_bank')
 if not isinstance(bank['positive'],list) or not 2<=len(bank['positive'])<=64 or not isinstance(bank['negative'],list) or not 3<=len(bank['negative'])<=16:raise ValueError('invalid_cohort_bank')
 if 'negative_sources' in bank and (not isinstance(bank['negative_sources'],list) or len(bank['negative_sources'])!=len(bank['negative']) or any(not isinstance(x,str) or not re.fullmatch(r'(?:session:)?[a-f0-9]{32}',x) for x in bank['negative_sources'])):raise ValueError('invalid_cohort_provenance')
 positive=[unit(v) for v in bank['positive']];negative=[unit(v) for v in bank['negative']]
 dimension=len(positive[0])
 if any(len(v)!=dimension for v in positive+negative):raise ValueError('embedding_dimensions')
 positive=list({tuple(round(x,12) for x in v):v for v in positive}.values())
 if len(positive)<2:raise ValueError('independent_references_required')
 return positive,negative

def cohort_evidence(vector,bank,*,window=False):
 v=unit(vector);positive,negative=cohort_bank(bank)
 if len(v)!=len(positive[0]):raise ValueError('embedding_dimensions')
 scores=sorted((similarity(v,r) for r in positive),reverse=True)
 score=sum(scores[:2])/2;excluded=max(similarity(v,r) for r in negative)
 threshold=COHORT_PARAMETERS['window_threshold' if window else 'whole_threshold']
 return {'score':score,'threshold':threshold,'second_reference_score':scores[1],
         'cohort_score':excluded,'exclusion_margin':score-excluded,
         'required_exclusion_margin':COHORT_PARAMETERS['exclusion_margin'],
         'accepted':score>=threshold and scores[1]>=COHORT_PARAMETERS['second_reference_floor'] and score-excluded>=COHORT_PARAMETERS['exclusion_margin']}

def profile_evidence(vector,samples,policy,*,window=False):
 if policy==COHORT_POLICY:return cohort_evidence(vector,samples,window=window)
 score=profile_score(vector,samples,policy);threshold=profile_threshold(policy)
 return {'score':score,'threshold':threshold,'accepted':score>=threshold}

def profile_score(vector,vectors,policy='centroid'):
 if policy==COHORT_POLICY:return cohort_evidence(vector,vectors)['score']
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
 if policy==COHORT_POLICY:return COHORT_PARAMETERS['whole_threshold']
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
  db.execute('CREATE TABLE IF NOT EXISTS voice_control_scopes (voice_id TEXT PRIMARY KEY,scope TEXT NOT NULL)')
  db.execute('CREATE TABLE IF NOT EXISTS voice_family_validations (voice_id TEXT PRIMARY KEY,owner_id TEXT,revision TEXT,report TEXT)')
  db.execute('CREATE TABLE IF NOT EXISTS voice_family_requests (request_id TEXT PRIMARY KEY,voice_id TEXT,fingerprint TEXT,result TEXT)')
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
 def can_control(self,voice_id,domain):
  with self._db() as db:
   row=db.execute('SELECT s.scope FROM voice_authorizations a LEFT JOIN voice_control_scopes s ON s.voice_id=a.voice_id WHERE a.voice_id=?',(voice_id,)).fetchone()
   return bool(row and (row[0] is None or row[0]=='lights' and domain=='light'))
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
 def match_diagnostics(self,vector,*,window=False):
  """Anonymous numeric evidence; never expose either reference bank."""
  v=unit(vector);scores=[]
  with self._db() as db:
   for samples,policy in db.execute("SELECT v.samples,COALESCE(p.policy,'centroid') FROM voices v LEFT JOIN voice_matching_policies p ON p.voice_id=v.voice_id WHERE v.model=?",(MODEL_ID,)):
    try:e=profile_evidence(v,json.loads(samples),policy,window=window)
    except (ValueError,TypeError,KeyError):continue
    scores.append(e)
  scores.sort(key=lambda e:e['score'],reverse=True)
  best=scores[0] if scores else {'score':None,'threshold':.75}
  result={'best_score':round(best['score'],4) if best['score'] is not None else None,
          'margin':round(scores[0]['score']-scores[1]['score'],4) if len(scores)>1 else None,
          'threshold':best['threshold'],'required_margin':.12}
  for key in ('second_reference_score','cohort_score','exclusion_margin','required_exclusion_margin'):
   if key in best:result[key]=round(best[key],4)
  return result
 def identify(self,vector,*,window=False):
  v=unit(vector);scores=[]
  with self._db() as db:
   for name,label,samples,voice_id,policy in db.execute("SELECT v.name,v.label,v.samples,v.voice_id,COALESCE(p.policy,'centroid') FROM voices v LEFT JOIN voice_matching_policies p ON p.voice_id=v.voice_id WHERE v.model=?",(MODEL_ID,)):
    try:e=profile_evidence(v,json.loads(samples),policy,window=window)
    except (ValueError,TypeError,KeyError):return {'status':'unknown'}
    scores.append((e['score'],name,label,voice_id,e['accepted']))
  scores.sort(reverse=True)
  if not scores or not scores[0][4]:return {'status':'unknown'}
  if len(scores)>1 and scores[0][0]-scores[1][0]<.12:return {'status':'ambiguous'}
  score,name,label,voice_id,_=scores[0]
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
     if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='owner_calibration_windows'").fetchone():db.execute('DELETE FROM owner_calibration_windows WHERE session IN (SELECT id FROM owner_calibration_sessions WHERE voice_id=?)',(row[0],))
     db.execute('DELETE FROM owner_calibration_samples WHERE session IN (SELECT id FROM owner_calibration_sessions WHERE voice_id=?)',(row[0],))
     db.execute('DELETE FROM owner_calibration_sessions WHERE voice_id=?',(row[0],))
    if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='voice_family_enrollment'").fetchone():db.execute('DELETE FROM voice_family_enrollment WHERE owner_id=?',(row[0],))
    db.execute('DELETE FROM voice_authorizations WHERE voice_id=?',(row[0],))
    db.execute('DELETE FROM voice_anchors WHERE voice_id=?',(row[0],))
    db.execute('DELETE FROM voice_family_validations WHERE voice_id=?',(row[0],))
    for table in ('voice_candidates','voice_validation','voice_versions','voice_aliases','voice_provenance','voice_matching_policies','voice_matching_versions','voice_matching_requests','voice_control_scopes','voice_family_requests'):
     if db.execute('SELECT 1 FROM sqlite_master WHERE type=? AND name=?',('table',table)).fetchone():
      db.execute('DELETE FROM '+table+' WHERE voice_id=?',(row[0],))
    def scrub(raw):
     bank=json.loads(raw)
     if not isinstance(bank,dict) or row[0] not in bank.get('negative_sources',[]):return raw
     pairs=[(v,k) for v,k in zip(bank['negative'],bank['negative_sources']) if k!=row[0]]
     bank['negative']=[v for v,k in pairs];bank['negative_sources']=[k for v,k in pairs]
     return json.dumps(bank)
    for other_id,raw in db.execute('SELECT voice_id,samples FROM voices').fetchall():
     cleaned=scrub(raw)
     if cleaned!=raw:db.execute('UPDATE voices SET samples=? WHERE voice_id=?',(cleaned,other_id))
    if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='voice_matching_versions'").fetchone():
     for version_id,before,after in db.execute('SELECT rowid,before_samples,after_samples FROM voice_matching_versions').fetchall():
      db.execute('UPDATE voice_matching_versions SET before_samples=?,after_samples=? WHERE rowid=?',(scrub(before),scrub(after),version_id))
  for device,slot in list(self.pending.items()):
   if slot['name']==key:self.cancel(device)
  return row[0] if row else None


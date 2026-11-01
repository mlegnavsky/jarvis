"""Bounded quarantined embeddings, immutable anchors and revisioned promotion.

No raw audio. No promotion without independent genuine/negative validation and
positive replay evidence. Scores are similarities, never probabilities.
"""
import hashlib
import json
if __package__:
 from .policy import unit, similarity, centroid
else:
 from policy import unit, similarity, centroid

def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()

class Adaptation:
 def __init__(self,profiles):self.profiles=profiles
 def db(self):
  db=self.profiles._db()
  db.execute('CREATE TABLE IF NOT EXISTS voice_candidates (voice_id TEXT,utterance TEXT,conversation TEXT,vector TEXT,live INTEGER,at REAL,PRIMARY KEY(voice_id,utterance))')
  db.execute('CREATE TABLE IF NOT EXISTS voice_validation (voice_id TEXT,utterance TEXT,vector TEXT,genuine INTEGER,PRIMARY KEY(voice_id,utterance))')
  db.execute('CREATE TABLE IF NOT EXISTS voice_versions (voice_id TEXT,revision TEXT,previous TEXT,current TEXT,at REAL,PRIMARY KEY(voice_id,revision))')
  db.execute('CREATE TABLE IF NOT EXISTS voice_provenance (voice_id TEXT,utterance TEXT,role TEXT,PRIMARY KEY(voice_id,utterance))')
  db.execute("INSERT OR IGNORE INTO voice_provenance SELECT voice_id,utterance,'candidate' FROM voice_candidates")
  db.execute("INSERT OR IGNORE INTO voice_provenance SELECT voice_id,utterance,'validation' FROM voice_validation")
  db.commit();return db
 def offer(self,voice_id,evidence):
  if not self.profiles.is_authorized(voice_id):return {'status':'rejected','reason':'not_authorized'}
  quality=evidence.get('quality') or {}
  if (evidence.get('seconds',0)<3 or evidence.get('playback') is not False or quality.get('status')!='ok'
      or quality.get('clipped_fraction',1)>.02 or quality.get('rms',0)<.004):
   return {'status':'rejected','reason':'quality'}
  anchors=self.profiles.anchors(voice_id)
  try:
   v=unit(evidence['vector']);windows=[unit(x) for x in evidence.get('windows',[])]
   if len(windows)<2 or min(similarity(x,centroid(anchors)) for x in [v,*windows])<.85:
    return {'status':'rejected','reason':'anchor_or_window_mismatch'}
  except (KeyError,ValueError,IndexError):return {'status':'rejected','reason':'invalid_vector'}
  utterance=evidence.get('utterance');conversation=evidence.get('conversation')
  if not isinstance(utterance,str) or not utterance or not isinstance(conversation,str) or not conversation:return {'status':'rejected','reason':'missing_provenance'}
  with self.db() as db:
   db.execute('BEGIN IMMEDIATE')
   if db.execute('SELECT 1 FROM voice_candidates WHERE voice_id=? AND (utterance=? OR conversation=?)',(voice_id,utterance,conversation)).fetchone():return {'status':'duplicate'}
   if db.execute('SELECT 1 FROM voice_validation WHERE voice_id=? AND utterance=?',(voice_id,utterance)).fetchone():return {'status':'rejected','reason':'holdout'}
   if db.execute('SELECT 1 FROM voice_provenance WHERE voice_id=? AND utterance=?',(voice_id,utterance)).fetchone():return {'status':'rejected','reason':'used_utterance'}
   db.execute("INSERT INTO voice_provenance VALUES (?,?,'candidate')",(voice_id,utterance))
   db.execute('INSERT INTO voice_candidates VALUES (?,?,?,?,?,?)',(voice_id,utterance,conversation,json.dumps(v),int(evidence.get('replay_live') is True),self.profiles.clock()))
   db.execute('DELETE FROM voice_candidates WHERE voice_id=? AND rowid NOT IN (SELECT rowid FROM voice_candidates WHERE voice_id=? ORDER BY rowid DESC LIMIT 8)',(voice_id,voice_id))
  return {'status':'quarantined','reason':'independent_validation_required'}
 def add_validation(self,voice_id,utterance,vector,genuine):
  if not self.profiles.is_authorized(voice_id):raise ValueError('not_authorized')
  with self.db() as db:
   db.execute('BEGIN IMMEDIATE')
   if db.execute('SELECT 1 FROM voice_provenance WHERE voice_id=? AND utterance=?',(voice_id,utterance)).fetchone():raise ValueError('holdout_contamination')
   if db.execute('SELECT 1 FROM voice_candidates WHERE voice_id=? AND utterance=?',(voice_id,utterance)).fetchone():raise ValueError('holdout_contamination')
   db.execute('INSERT INTO voice_validation VALUES (?,?,?,?)',(voice_id,utterance,json.dumps(unit(vector)),int(genuine)))
   db.execute("INSERT INTO voice_provenance VALUES (?,?,'validation')",(voice_id,utterance))
   db.execute('DELETE FROM voice_validation WHERE voice_id=? AND rowid NOT IN (SELECT rowid FROM voice_validation WHERE voice_id=? ORDER BY rowid DESC LIMIT 64)',(voice_id,voice_id))
 def _evaluate(self,db,voice_id):
  row=db.execute('SELECT samples FROM voices WHERE voice_id=?',(voice_id,)).fetchone()
  if not row:raise ValueError('profile_missing')
  old=json.loads(row[0])
  policy=db.execute('SELECT policy FROM voice_matching_policies WHERE voice_id=?',(voice_id,)).fetchone()
  if policy and policy[0]!='centroid':return {'status':'manual_matching_policy_requires_owner_control','revision':digest([old,policy[0]])},None,old
  anchors=json.loads(db.execute('SELECT samples FROM voice_anchors WHERE voice_id=?',(voice_id,)).fetchone()[0])
  candidates=db.execute('SELECT vector,live,utterance FROM voice_candidates WHERE voice_id=? ORDER BY rowid',(voice_id,)).fetchall()
  validation=db.execute('SELECT vector,genuine,utterance FROM voice_validation WHERE voice_id=? ORDER BY rowid',(voice_id,)).fetchall()
  revision=digest([old,candidates,validation])
  result={'status':'awaiting_validation','revision':revision,'candidates':len(candidates),'genuine_holdouts':sum(bool(x[1]) for x in validation),'negative_holdouts':sum(not x[1] for x in validation)}
  if not candidates or not all(x[1] for x in candidates) or result['genuine_holdouts']<5 or result['negative_holdouts']<5:return result,None,old
  base=centroid(anchors);new=unit([.9*a+.1*b for a,b in zip(base,centroid([json.loads(x[0]) for x in candidates]))])
  before=centroid(old)
  old_genuine=sum(similarity(before,json.loads(x[0]))>=.75 for x in validation if x[1])
  new_genuine=sum(similarity(new,json.loads(x[0]))>=.75 for x in validation if x[1])
  # Require zero observed impostor accepts, not merely no increase.
  false_accepts=sum(similarity(new,json.loads(x[0]))>=.75 for x in validation if not x[1])
  result.update(status='eligible' if new_genuine>old_genuine and false_accepts==0 else 'rejected',old_genuine_accepts=old_genuine,new_genuine_accepts=new_genuine,observed_false_accepts=false_accepts)
  return result,[new],old
 def evaluate(self,voice_id):
  if not self.profiles.is_authorized(voice_id):return {'status':'not_authorized'}
  with self.db() as db:return self._evaluate(db,voice_id)[0]
 def promote(self,voice_id,expected_revision):
  if not self.profiles.is_authorized(voice_id):raise ValueError('not_authorized')
  with self.db() as db:
   db.execute('BEGIN IMMEDIATE');result,new,old=self._evaluate(db,voice_id)
   if result['revision']!=expected_revision:raise ValueError('revision_conflict')
   if result['status']!='eligible':raise ValueError('validation_required')
   revision=digest(new)
   db.execute('INSERT INTO voice_versions VALUES (?,?,?,?,?)',(voice_id,revision,json.dumps(old),json.dumps(new),self.profiles.clock()))
   db.execute('DELETE FROM voice_versions WHERE voice_id=? AND rowid NOT IN (SELECT rowid FROM voice_versions WHERE voice_id=? ORDER BY rowid DESC LIMIT 8)',(voice_id,voice_id))
   db.execute('UPDATE voices SET samples=? WHERE voice_id=?',(json.dumps(new),voice_id))
   db.execute('DELETE FROM voice_candidates WHERE voice_id=?',(voice_id,))
  return {'status':'promoted','revision':revision}
 def rollback(self,voice_id,expected_revision):
  with self.db() as db:
   db.execute('BEGIN IMMEDIATE')
   policy=db.execute('SELECT policy FROM voice_matching_policies WHERE voice_id=?',(voice_id,)).fetchone()
   if policy and policy[0]!='centroid':raise ValueError('manual_matching_policy_requires_owner_control')
   row=db.execute('SELECT samples FROM voices WHERE voice_id=?',(voice_id,)).fetchone()
   version=db.execute('SELECT previous FROM voice_versions WHERE voice_id=? AND revision=?',(voice_id,expected_revision)).fetchone()
   if not row or not version or digest(json.loads(row[0]))!=expected_revision:raise ValueError('revision_conflict')
   db.execute('UPDATE voices SET samples=? WHERE voice_id=?',(version[0],voice_id))
  return {'status':'rolled_back'}
 def summary(self):
  with self.db() as db:
   db.execute('DELETE FROM voice_candidates WHERE voice_id NOT IN (SELECT voice_id FROM voices)')
   db.execute('DELETE FROM voice_validation WHERE voice_id NOT IN (SELECT voice_id FROM voices)')
   db.execute('DELETE FROM voice_versions WHERE voice_id NOT IN (SELECT voice_id FROM voices)')
   return {'mode':'quarantined_candidates','candidates':db.execute('SELECT count(*) FROM voice_candidates').fetchone()[0],
           'validation_samples':db.execute('SELECT count(*) FROM voice_validation').fetchone()[0],
           'promotion':'requires_independent_validation_and_replay_evidence','raw_audio_saved':False}

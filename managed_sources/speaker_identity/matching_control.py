"""Fresh authenticated file-control activation/rollback of supervised matching.

No permission grants or device actions. Every live change is CAS-bound to the
reviewed evidence and has a private, bounded before-image. Replay detection is
not implemented; the explicit acknowledgement is operator consent, not evidence.
"""
import json,math,re,sqlite3
if __package__:
 from .policy import MODEL_ID,norm
 from .review import digest,model_revision,evidence_snapshot
else:
 from policy import MODEL_ID,norm
 from review import digest,model_revision,evidence_snapshot

class MatchingControl:
 def __init__(self,profiles,review,path):self.profiles=profiles;self.review=review;self.path=path
 def db(self):
  db=self.profiles._db()
  db.execute('CREATE TABLE IF NOT EXISTS voice_matching_versions(voice_id TEXT,revision TEXT,before_samples TEXT,before_policy TEXT,after_samples TEXT,after_policy TEXT,created REAL,PRIMARY KEY(voice_id,revision))')
  db.execute('CREATE TABLE IF NOT EXISTS voice_matching_requests(request_id TEXT PRIMARY KEY,voice_id TEXT,fingerprint TEXT,result TEXT,created REAL)')
  db.commit();return db
 def process(self):
  if not self.path.exists():return {'status':'not_requested'}
  try:
   if self.path.is_symlink() or self.path.stat().st_size>4096:raise ValueError('unsafe_control')
   body=json.loads(self.path.read_text())
   if not isinstance(body,dict) or set(body)!={'request_id','action','profile','expected_revision','issued_at','acknowledge_replay_risk'}:raise ValueError('invalid_control')
   key=body['request_id'];expected=body['expected_revision'];issued=body['issued_at'];fingerprint=digest(body)
   if not isinstance(key,str) or not re.fullmatch('[a-f0-9]{32}',key):raise ValueError('invalid_request_id')
   if not isinstance(expected,str) or not re.fullmatch('[a-f0-9]{64}',expected):raise ValueError('invalid_revision')
   if body['action'] not in ('activate','rollback') or not isinstance(body['profile'],str) or not 0<len(body['profile'])<=40:raise ValueError('invalid_control')
   if body['acknowledge_replay_risk'] is not True:raise ValueError('replay_limitation_ack_required')
   if type(issued) not in (int,float) or not math.isfinite(issued):raise ValueError('invalid_timestamp')
   with self.db() as db:
    prior=db.execute('SELECT fingerprint,result FROM voice_matching_requests WHERE request_id=?',(key,)).fetchone()
   if prior:
    if prior[0]!=fingerprint:raise ValueError('request_id_conflict')
    return {'status':'already_applied','verified':True,'replayed':True,'result':json.loads(prior[1])}
   if not 0<=self.profiles.clock()-issued<=120:raise ValueError('stale_control')
   proposal=None
   if body['action']=='activate':
    report=self.review.evaluate();proposal=self.review.proposal
    if report.get('status')!='eligible_for_controlled_activation' or report.get('revision')!=expected or proposal is None:raise ValueError('supervised_validation_or_revision_failed')
    if norm(proposal['plan']['reference_profile'])!=norm(body['profile']):raise ValueError('reference_mismatch')
   with self.db() as db:
    db.execute('BEGIN IMMEDIATE')
    if db.execute('SELECT 1 FROM voice_matching_requests WHERE request_id=?',(key,)).fetchone():raise ValueError('request_changed')
    if db.execute('SELECT count(*) FROM voice_matching_requests').fetchone()[0]>=512:raise ValueError('request_limit')
    row=db.execute("SELECT v.voice_id,v.samples,COALESCE(p.policy,'centroid') FROM voices v JOIN voice_authorizations a ON a.voice_id=v.voice_id LEFT JOIN voice_matching_policies p ON p.voice_id=v.voice_id WHERE v.name=? AND v.model=?",(norm(body['profile']),MODEL_ID)).fetchone()
    if not row:raise ValueError('existing_authorized_profile_required')
    current=model_revision(json.loads(row[1]),row[2])
    if proposal is not None:
     # Re-read both file and database evidence under the same write lock.
     if self.review.path.is_symlink() or self.review.path.stat().st_size>16384:raise ValueError('unsafe_evidence_plan')
     if row[0]!=proposal['voice_id'] or digest(json.loads(self.review.path.read_text()))!=digest(proposal['plan']) or digest(evidence_snapshot(db,proposal['plan']))!=expected:raise ValueError('evidence_revision_conflict')
     samples=json.dumps(proposal['samples']);policy=proposal['policy'];revision=model_revision(proposal['samples'],policy)
     db.execute('INSERT OR REPLACE INTO voice_matching_versions VALUES (?,?,?,?,?,?,?)',(row[0],revision,row[1],row[2],samples,policy,self.profiles.clock()))
     db.execute('DELETE FROM voice_matching_versions WHERE voice_id=? AND rowid NOT IN (SELECT rowid FROM voice_matching_versions WHERE voice_id=? ORDER BY rowid DESC LIMIT 8)',(row[0],row[0]))
     status='activated'
    else:
     if current!=expected:raise ValueError('profile_revision_conflict')
     version=db.execute('SELECT before_samples,before_policy FROM voice_matching_versions WHERE voice_id=? AND revision=?',(row[0],expected)).fetchone()
     if not version:raise ValueError('rollback_before_image_missing')
     samples,policy=version;revision=model_revision(json.loads(samples),policy);status='rolled_back'
    db.execute('UPDATE voices SET samples=? WHERE voice_id=?',(samples,row[0]))
    db.execute('INSERT OR REPLACE INTO voice_matching_policies VALUES (?,?)',(row[0],policy))
    result={'status':status,'verified':True,'current_profile_revision':revision,'active_policy':policy,'original_anchors_preserved':True,'permissions_changed':False}
    db.execute('INSERT INTO voice_matching_requests VALUES (?,?,?,?,?)',(key,row[0],fingerprint,json.dumps(result),self.profiles.clock()))
   return result
  except (OSError,ValueError,TypeError,KeyError,sqlite3.Error) as exc:
   return {'status':'rejected','verified':False,'reason':str(exc) if isinstance(exc,ValueError) else type(exc).__name__,'permissions_changed':False}

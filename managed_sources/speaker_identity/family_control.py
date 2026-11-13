"""Authenticated operator file controls for validated family light permissions.

Voice enrollment itself never grants persistent permissions or lock access.
"""
import json,math,re,sqlite3
if __package__:
 from .policy import MODEL_ID,COHORT_POLICY,norm,cohort_evidence,profile_evidence
 from .review import digest,model_revision
else:
 from policy import MODEL_ID,COHORT_POLICY,norm,cohort_evidence,profile_evidence
 from review import digest,model_revision

def permission_revision(identity,bank,policy,owner):return digest([identity,model_revision(bank,policy),owner])

def validate_holdout(db,sample,bank,exclude_id=None):
 rivals=[(identity,json.loads(raw),policy) for identity,raw,policy in db.execute("SELECT v.voice_id,v.samples,COALESCE(p.policy,'centroid') FROM voices v LEFT JOIN voice_matching_policies p ON p.voice_id=v.voice_id WHERE v.model=?",(MODEL_ID,)) if identity!=exclude_id]
 def matches(vector,window=False):
  evidence=cohort_evidence(vector,bank,window=window)
  return evidence['accepted'] and all(evidence['score']-profile_evidence(vector,other,policy,window=window)['score']>=.12 for identity,other,policy in rivals)
 return matches(sample['vector']) and all(matches(v,True) for v in sample['windows'])

class FamilyControl:
 def __init__(self,profiles,path):self.profiles=profiles;self.path=path
 def process(self):
  if not self.path.exists():return {'status':'not_requested'}
  try:
   if self.path.is_symlink() or self.path.stat().st_size>4096:raise ValueError('unsafe_control')
   body=json.loads(self.path.read_text())
   if not isinstance(body,dict) or set(body)!={'request_id','action','profile','expected_revision','issued_at'}:raise ValueError('invalid_control')
   key=body['request_id'];expected=body['expected_revision'];issued=body['issued_at'];fingerprint=digest(body)
   if not isinstance(key,str) or not re.fullmatch('[a-f0-9]{32}',key) or not isinstance(expected,str) or not re.fullmatch('[a-f0-9]{64}',expected):raise ValueError('invalid_control')
   if body['action'] not in ('authorize_lights','revoke_lights') or not isinstance(body['profile'],str) or not 0<len(body['profile'])<=40:raise ValueError('invalid_control')
   if type(issued) not in (int,float) or not math.isfinite(issued):raise ValueError('invalid_timestamp')
   with self.profiles._db() as db:
    db.execute('BEGIN IMMEDIATE')
    prior=db.execute('SELECT fingerprint,result FROM voice_family_requests WHERE request_id=?',(key,)).fetchone()
    if prior:
     if prior[0]!=fingerprint:raise ValueError('request_id_conflict')
     return {'status':'already_applied','replayed':True,'result':json.loads(prior[1])}
    if not 0<=self.profiles.clock()-issued<=120:raise ValueError('stale_control')
    if db.execute('SELECT count(*) FROM voice_family_requests').fetchone()[0]>=256:raise ValueError('request_limit')
    row=db.execute('SELECT v.voice_id,v.samples,p.policy FROM voices v JOIN voice_matching_policies p ON p.voice_id=v.voice_id WHERE v.name=? AND v.model=?',(norm(body['profile']),MODEL_ID)).fetchone()
    if not row or row[2]!=COHORT_POLICY:raise ValueError('validated_family_profile_required')
    proof=db.execute('SELECT owner_id,revision,report FROM voice_family_validations WHERE voice_id=?',(row[0],)).fetchone()
    if not proof or expected!=proof[1]:raise ValueError('profile_revision_conflict')
    scope=db.execute('SELECT scope FROM voice_control_scopes WHERE voice_id=?',(row[0],)).fetchone()
    if body['action']=='authorize_lights':
     if permission_revision(row[0],json.loads(row[1]),row[2],proof[0])!=expected:raise ValueError('profile_revision_conflict')
     report=json.loads(proof[2])
     if (report.get('training_utterances',0)<5 or report.get('validation_utterances',0)<3 or report.get('validation_windows',0)<2 or
         not db.execute('SELECT 1 FROM voice_authorizations a LEFT JOIN voice_control_scopes s ON s.voice_id=a.voice_id WHERE a.voice_id=? AND s.scope IS NULL',(proof[0],)).fetchone()):raise ValueError('family_validation_required')
     holdouts=report.get('holdouts')
     if not isinstance(holdouts,list) or len(holdouts)<3 or not all(validate_holdout(db,s,json.loads(row[1]),row[0]) for s in holdouts):raise ValueError('current_validation_required')
     if db.execute('SELECT 1 FROM voice_authorizations WHERE voice_id=?',(row[0],)).fetchone() and (not scope or scope[0]!='lights'):raise ValueError('existing_full_scope_unchanged')
     db.execute('INSERT OR IGNORE INTO voice_authorizations VALUES (?)',(row[0],))
     db.execute('INSERT OR REPLACE INTO voice_control_scopes VALUES (?,?)',(row[0],'lights'))
     status='authorized_lights'
    else:
     if not scope or scope[0]!='lights':raise ValueError('lights_scope_required')
     db.execute('DELETE FROM voice_authorizations WHERE voice_id=?',(row[0],))
     db.execute('DELETE FROM voice_control_scopes WHERE voice_id=?',(row[0],));status='revoked_lights'
    result={'status':status,'verified':True,'lock_access':False,'profile_revision':expected}
    db.execute('INSERT INTO voice_family_requests VALUES (?,?,?,?)',(key,row[0],fingerprint,json.dumps(result)))
   return result
  except (OSError,ValueError,TypeError,KeyError,sqlite3.Error):return {'status':'rejected','verified':False}

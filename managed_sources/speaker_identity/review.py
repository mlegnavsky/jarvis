"""Read-only, supervised calibration review. Never changes identity or permission."""
import hashlib,json,re,sqlite3
if __package__:
 from .policy import MODEL_ID,norm,unit,centroid,similarity,profile_score,profile_threshold
else:
 from policy import MODEL_ID,norm,unit,centroid,similarity,profile_score,profile_threshold

REPAIR_ROLE='owner_duration_repair_unreviewed'
ROLES=('owner_provided_calibration_unreviewed','other_speaker_comparison_unreviewed','owner_validation_unreviewed')
def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()
def model_revision(samples,policy):return digest([samples,policy])
def evidence_snapshot(db,plan):
 ids=[x['session_id'] for x in plan['sessions']];marks=','.join('?' for _ in ids)
 voices=db.execute("SELECT v.voice_id,v.model,v.samples,COALESCE(p.policy,'centroid'),CASE WHEN a.voice_id IS NULL THEN 0 ELSE 1 END FROM voices v LEFT JOIN voice_matching_policies p ON p.voice_id=v.voice_id LEFT JOIN voice_authorizations a ON a.voice_id=v.voice_id ORDER BY v.voice_id").fetchall()
 anchors=db.execute('SELECT voice_id,samples FROM voice_anchors ORDER BY voice_id').fetchall()
 sessions=db.execute('SELECT id,voice_id,device,status,mode FROM owner_calibration_sessions WHERE id IN ('+marks+') ORDER BY id',ids).fetchall()
 samples=db.execute('SELECT session,utterance,vector FROM owner_calibration_samples WHERE session IN ('+marks+') ORDER BY session,utterance',ids).fetchall()
 windows=db.execute('SELECT session,utterance,windows FROM owner_calibration_windows WHERE session IN ('+marks+') ORDER BY session,utterance',ids).fetchall()
 return [{'candidate_policy':'top_two_mean_calibrated_v1','threshold':.65,'required_margin':.12,'second_reference_floor':.6,'required_gap':.2},plan,voices,anchors,sessions,samples,windows]

class CalibrationReview:
 def __init__(self,profiles,path,satellite):self.profiles=profiles;self.path=path;self.satellite=satellite;self.proposal=None
 def evaluate(self):
  self.proposal=None
  try:
   if not self.path.exists():return {'status':'not_prepared','live_profile_changed':False}
   if self.path.is_symlink() or self.path.stat().st_size>16384:raise ValueError('unsafe_plan')
   plan=json.loads(self.path.read_text())
   if not isinstance(plan,dict):raise ValueError('invalid_plan')
   if not isinstance(plan.get('reference_profile'),str) or not 0<len(plan['reference_profile'])<=40:raise ValueError('invalid_reference')
   if plan.get('schema') not in (1,2) or plan.get('automatic_profile_update') is not False:raise ValueError('invalid_plan')
   slots=plan.get('sessions');repair=plan['schema']==2;roles=ROLES+(REPAIR_ROLE,) if repair else ROLES
   if not isinstance(slots,list) or len(slots)!=len(roles) or any(not isinstance(s,dict) for s in slots) or {s.get('role') for s in slots}!=set(roles):raise ValueError('three_distinct_roles_required')
   if len({s.get('session_id') for s in slots})!=len(roles):raise ValueError('holdout_session_overlap')
   for s in slots:
    if s.get('speaker_identity_confirmed_by_owner') is not True:raise ValueError('owner_attestation_required')
    if not isinstance(s.get('session_id'),str) or not re.fullmatch('[a-f0-9]{32}',s['session_id']):raise ValueError('invalid_session')
   with self.profiles._db() as db:
    db.execute('BEGIN')
    row=db.execute("SELECT v.voice_id,v.samples,COALESCE(p.policy,'centroid') FROM voices v JOIN voice_authorizations a ON a.voice_id=v.voice_id LEFT JOIN voice_matching_policies p ON p.voice_id=v.voice_id WHERE v.name=? AND v.model=?",(norm(plan['reference_profile']),MODEL_ID)).fetchone()
    if not row:raise ValueError('existing_authorized_profile_required')
    anchor=db.execute('SELECT samples FROM voice_anchors WHERE voice_id=?',(row[0],)).fetchone()
    if not anchor:raise ValueError('anchor_missing')
    groups={};used=set();provenance=[];repair_windows=[]
    for slot in slots:
     sid=slot['session_id'];session=db.execute('SELECT voice_id,device,status,mode FROM owner_calibration_sessions WHERE id=?',(sid,)).fetchone()
     if not session or session[:3]!=(row[0],self.satellite,'awaiting_review') or (slot['role']==REPAIR_ROLE and session[3]!='repair'):raise ValueError('completed_same_reference_and_satellite_required')
     samples=db.execute('SELECT utterance,vector FROM owner_calibration_samples WHERE session=? ORDER BY rowid',(sid,)).fetchall()
     if len(samples)!=(2 if slot['role']==REPAIR_ROLE else 5):raise ValueError('required_samples_missing')
     vectors=[]
     for key,value in samples:
      if not isinstance(key,str) or not key:raise ValueError('invalid_utterance')
      if key in used:raise ValueError('utterance_overlap')
      used.add(key);vectors.append(unit(json.loads(value)))
      if slot['role']==REPAIR_ROLE:
       parts=db.execute('SELECT windows FROM owner_calibration_windows WHERE session=? AND utterance=?',(sid,key)).fetchone()
       if not parts:raise ValueError('repair_windows_missing')
       parts=json.loads(parts[0])
       if not isinstance(parts,list) or len(parts)!=2:raise ValueError('two_repair_windows_required')
       parts=[unit(v) for v in parts]
       if any(len(w)!=len(vectors[-1]) for w in parts) or similarity(*parts)<.55 or any(similarity(vectors[-1],w)<.55 for w in parts):raise ValueError('inconsistent_repair_parts')
       repair_windows.append(parts)
     groups[slot['role']]=vectors;provenance.append((sid,samples))
    live=[unit(v) for v in json.loads(row[1])];anchors=[unit(v) for v in json.loads(anchor[0])]
    other_rows=[x for x in db.execute("SELECT v.voice_id,v.samples,COALESCE(p.policy,'centroid') FROM voices v LEFT JOIN voice_matching_policies p ON p.voice_id=v.voice_id WHERE v.model=?",(MODEL_ID,)) if x[0]!=row[0]]
    other_vectors=[[unit(v) for v in json.loads(x[1])] for x in other_rows]
    all_groups=[live,anchors,*groups.values(),*other_vectors,*repair_windows]
    if any(not vs for vs in all_groups):raise ValueError('empty_templates')
    dimension=len(live[0])
    if any(len(v)!=dimension for vs in all_groups for v in vs):raise ValueError('embedding_dimensions')
    pool=anchors+groups[ROLES[0]]
    if repair:pool+=groups[REPAIR_ROLE][:1]+repair_windows[0]
    def score(v):return profile_score(v,pool,'top_two_mean_calibrated_v1')
    def accepted(v):
     value=score(v)
     other=[profile_score(v,vs,x[2]) for vs,x in zip(other_vectors,other_rows)]
     return value>=.65 and (not other or value-max(other)>=.12)
    validation=groups[ROLES[2]]+(groups[REPAIR_ROLE][1:] if repair else []);negative=groups[ROLES[1]]
    query_parts=[[] for _ in groups[ROLES[2]]]+([repair_windows[1]] if repair else [])
    baseline=[profile_score(v,live,row[2]) for v in validation]
    def baseline_accept(w):
     value=profile_score(w,live,row[2]);other=[profile_score(w,vs,x[2]) for vs,x in zip(other_vectors,other_rows)]
     return value>=profile_threshold(row[2]) and (not other or value-max(other)>=.12)
    old_count=sum(baseline_accept(w) and all(baseline_accept(p) for p in parts) for w,parts in zip(validation,query_parts))
    new_count=sum(accepted(v) and all(accepted(p) for p in parts) for v,parts in zip(validation,query_parts));false_accepts=sum(score(v)>=.65 for v in negative)
    snapshot=evidence_snapshot(db,plan);revision=digest(snapshot)
    active=row[2]=='top_two_mean_calibrated_v1' and len(live)==len(pool) and all(similarity(a,b)>1-1e-10 for a,b in zip(live,pool))
    separation=min(score(v) for v in validation+[p for parts in query_parts for p in parts])-max(score(v) for v in negative)
    eligible=new_count==len(validation) and new_count>old_count and false_accepts==0 and separation>=.2
    if eligible:self.proposal={'voice_id':row[0],'samples':pool,'policy':'top_two_mean_calibrated_v1','plan':plan,'snapshot':snapshot,'revision':revision}
    return {'status':('active_supervised_profile' if new_count==len(validation) and false_accepts==0 else 'active_profile_validation_failed') if active else 'eligible_for_controlled_activation' if eligible else 'rejected',
            'revision':revision,'current_profile_revision':model_revision(json.loads(row[1]),row[2]),'active_policy':row[2],
            'candidate_policy':'top_two_mean_calibrated_v1','required_second_reference_score':.6,'positive_negative_gap':round(separation,4),'required_gap':.2,'threshold_calibrated_on_household_samples':True,'threshold':.65,'strict_lock_threshold':.75,'required_margin':.12,
            'training_samples':6 if repair else 5,'owner_validation_samples':len(validation),'other_validation_samples':5,
            'baseline_owner_accepts':old_count,'candidate_owner_accepts':new_count,'candidate_other_accepts':false_accepts,
            'baseline_owner_scores':[round(v,4) for v in baseline],'candidate_owner_scores':[round(score(v),4) for v in validation],
            'candidate_other_scores':[round(score(v),4) for v in negative],'live_profile_changed':False,
            'window_validation':'repair_holdout_only' if repair else 'not_performed','repair_holdout_windows':2 if repair else 0,'replay_detection':'not_installed','household_accuracy_verified':False}
  except (OSError,ValueError,TypeError,KeyError,sqlite3.Error):return {'status':'blocked','reason':'invalid_or_incomplete_independent_evidence','live_profile_changed':False}

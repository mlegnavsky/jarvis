"""Read-only, supervised calibration review. Never changes identity or permission."""
import hashlib,json,re,sqlite3
if __package__:
 from .policy import MODEL_ID,norm,unit,centroid,similarity
else:
 from policy import MODEL_ID,norm,unit,centroid,similarity

ROLES=('owner_provided_calibration_unreviewed','other_speaker_comparison_unreviewed','owner_validation_unreviewed')
class CalibrationReview:
 def __init__(self,profiles,path,satellite):self.profiles=profiles;self.path=path;self.satellite=satellite
 def evaluate(self):
  try:
   if not self.path.exists():return {'status':'not_prepared','live_profile_changed':False}
   if self.path.is_symlink() or self.path.stat().st_size>16384:raise ValueError('unsafe_plan')
   plan=json.loads(self.path.read_text())
   if not isinstance(plan,dict):raise ValueError('invalid_plan')
   if not isinstance(plan.get('reference_profile'),str) or not 0<len(plan['reference_profile'])<=40:raise ValueError('invalid_reference')
   if plan.get('schema')!=1 or plan.get('automatic_profile_update') is not False:raise ValueError('invalid_plan')
   slots=plan.get('sessions')
   if not isinstance(slots,list) or len(slots)!=3 or any(not isinstance(s,dict) for s in slots) or {s.get('role') for s in slots}!=set(ROLES):raise ValueError('three_distinct_roles_required')
   if len({s.get('session_id') for s in slots})!=3:raise ValueError('holdout_session_overlap')
   for s in slots:
    if s.get('speaker_identity_confirmed_by_owner') is not True:raise ValueError('owner_attestation_required')
    if not isinstance(s.get('session_id'),str) or not re.fullmatch('[a-f0-9]{32}',s['session_id']):raise ValueError('invalid_session')
   with self.profiles._db() as db:
    row=db.execute('SELECT v.voice_id,v.samples FROM voices v JOIN voice_authorizations a ON a.voice_id=v.voice_id WHERE v.name=? AND v.model=?',(norm(plan['reference_profile']),MODEL_ID)).fetchone()
    if not row:raise ValueError('existing_authorized_profile_required')
    anchor=db.execute('SELECT samples FROM voice_anchors WHERE voice_id=?',(row[0],)).fetchone()
    if not anchor:raise ValueError('anchor_missing')
    groups={};used=set();provenance=[]
    for slot in slots:
     sid=slot['session_id'];session=db.execute('SELECT voice_id,device,status FROM owner_calibration_sessions WHERE id=?',(sid,)).fetchone()
     if not session or session!=(row[0],self.satellite,'awaiting_review'):raise ValueError('completed_same_reference_and_satellite_required')
     samples=db.execute('SELECT utterance,vector FROM owner_calibration_samples WHERE session=? ORDER BY rowid',(sid,)).fetchall()
     if len(samples)!=5:raise ValueError('five_samples_required')
     vectors=[]
     for key,value in samples:
      if not isinstance(key,str) or not key:raise ValueError('invalid_utterance')
      if key in used:raise ValueError('utterance_overlap')
      used.add(key);vectors.append(unit(json.loads(value)))
     groups[slot['role']]=vectors;provenance.append((sid,samples))
    live=[unit(v) for v in json.loads(row[1])];anchors=[unit(v) for v in json.loads(anchor[0])]
    other_vectors=[[unit(v) for v in json.loads(x[1])] for x in db.execute('SELECT voice_id,samples FROM voices WHERE model=?',(MODEL_ID,)) if x[0]!=row[0]]
    all_groups=[live,anchors,*groups.values(),*other_vectors]
    if any(not vs for vs in all_groups):raise ValueError('empty_templates')
    dimension=len(live[0])
    if any(len(v)!=dimension for vs in all_groups for v in vs):raise ValueError('embedding_dimensions')
    original=centroid(live);base=centroid(anchors);trained=centroid(groups[ROLES[0]])
    # Fixed before observing holdout results. No threshold search or selection
    # on the comparison person; the immutable anchor contributes one half.
    candidate=unit([.5*a+.5*b for a,b in zip(base,trained)])
    others=[centroid(vs) for vs in other_vectors]
    def accepted(template,v):
     score=similarity(template,v)
     return score>=.75 and (not others or score-max(similarity(o,v) for o in others)>=.12)
    validation=groups[ROLES[2]];negative=groups[ROLES[1]]
    old_count=sum(accepted(original,v) for v in validation);new_count=sum(accepted(candidate,v) for v in validation)
    false_accepts=sum(similarity(candidate,v)>=.75 for v in negative)
    revision=hashlib.sha256(json.dumps([row,anchor,provenance,others,slots],sort_keys=True).encode()).hexdigest()
    scores=lambda t,vs:[round(similarity(t,v),4) for v in vs]
    return {'status':'eligible_for_window_test' if new_count==5 and new_count>old_count and false_accepts==0 else 'rejected',
            'revision':revision,'candidate_policy':'equal_immutable_anchor_and_training_centroid',
            'threshold':.75,'required_margin':.12,'training_samples':5,'owner_validation_samples':5,'other_validation_samples':5,
            'baseline_owner_accepts':old_count,'candidate_owner_accepts':new_count,'candidate_other_accepts':false_accepts,
            'baseline_owner_scores':scores(original,validation),'candidate_owner_scores':scores(candidate,validation),
            'candidate_other_scores':scores(candidate,negative),'live_profile_changed':False,
            'window_validation':'not_performed','replay_detection':'not_installed','household_accuracy_verified':False}
  except (OSError,ValueError,TypeError,KeyError,sqlite3.Error):return {'status':'blocked','reason':'invalid_or_incomplete_independent_evidence','live_profile_changed':False}

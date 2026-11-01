"""Independent supervised review of a positive/exclusion household voice bank."""
import json,re
if __package__:
 from .policy import MODEL_ID,COHORT_POLICY,COHORT_PARAMETERS,unit,norm,similarity,cohort_evidence,profile_evidence
 from .review import ROLES,digest,model_revision,evidence_snapshot
else:
 from policy import MODEL_ID,COHORT_POLICY,COHORT_PARAMETERS,unit,norm,similarity,cohort_evidence,profile_evidence
 from review import ROLES,digest,model_revision,evidence_snapshot

def evaluate(profiles,plan,satellite):
 if (plan.get('automatic_profile_update') is not False or plan.get('candidate_policy')!=COHORT_POLICY or
     plan.get('policy_parameters')!=COHORT_PARAMETERS or plan.get('allow_non_regressing_policy_migration') is not True):raise ValueError('explicit_policy_migration_required')
 slots=plan.get('sessions')
 if (not isinstance(slots,list) or len(slots)!=3 or any(not isinstance(s,dict) for s in slots) or
     {s.get('role') for s in slots}!=set(ROLES) or len({s.get('session_id') for s in slots})!=3):raise ValueError('independent_roles_required')
 for s in slots:
  if s.get('speaker_identity_confirmed_by_owner') is not True or not isinstance(s.get('session_id'),str) or not re.fullmatch('[a-f0-9]{32}',s['session_id']):raise ValueError('owner_attestation_required')
 if not isinstance(plan.get('reference_profile'),str) or not 0<len(plan['reference_profile'])<=40:raise ValueError('invalid_reference')
 with profiles._db() as db:
  db.execute('BEGIN')
  row=db.execute("SELECT v.voice_id,v.samples,COALESCE(p.policy,'centroid') FROM voices v JOIN voice_authorizations a ON a.voice_id=v.voice_id LEFT JOIN voice_matching_policies p ON p.voice_id=v.voice_id WHERE v.name=? AND v.model=?",(norm(plan['reference_profile']),MODEL_ID)).fetchone()
  if not row:raise ValueError('existing_authorized_profile_required')
  saved=db.execute('SELECT samples FROM voice_anchors WHERE voice_id=?',(row[0],)).fetchone()
  if not saved:raise ValueError('anchor_missing')
  anchors=[unit(v) for v in json.loads(saved[0])];groups={};used=set()
  for slot in slots:
   sid=slot['session_id'];session=db.execute('SELECT voice_id,device,status FROM owner_calibration_sessions WHERE id=?',(sid,)).fetchone()
   if session!=(row[0],satellite,'awaiting_review'):raise ValueError('completed_same_reference_required')
   samples=db.execute('SELECT utterance,vector FROM owner_calibration_samples WHERE session=? ORDER BY rowid',(sid,)).fetchall()
   if len(samples)!=5:raise ValueError('five_samples_required')
   values=[]
   for key,value in samples:
    if not isinstance(key,str) or not key or key in used:raise ValueError('utterance_overlap')
    used.add(key);values.append(unit(json.loads(value)))
   groups[slot['role']]=values
  bank={'positive':anchors+groups[ROLES[0]],'negative':groups[ROLES[1]]}
  validation=groups[ROLES[2]];negative=groups[ROLES[1]];live=json.loads(row[1])
  dimension=len(anchors[0])
  if any(len(v)!=dimension for v in bank['positive']+negative+validation):raise ValueError('embedding_dimensions')
  others=db.execute("SELECT samples,COALESCE(p.policy,'centroid') FROM voices v LEFT JOIN voice_matching_policies p ON p.voice_id=v.voice_id WHERE model=? AND v.voice_id!=?",(MODEL_ID,row[0])).fetchall()
  def margin_pass(v,score):
   rivals=[profile_evidence(v,json.loads(samples),policy)['score'] for samples,policy in others]
   return not rivals or score-max(rivals)>=.12
  owner=[cohort_evidence(v,bank) for v in validation]
  base=[profile_evidence(v,live,row[2]) for v in validation]
  old_count=sum(e['accepted'] and margin_pass(v,e['score']) for v,e in zip(validation,base))
  new_count=sum(e['accepted'] and margin_pass(v,e['score']) for v,e in zip(validation,owner))
  folds=[cohort_evidence(v,{'positive':bank['positive'],'negative':negative[:i]+negative[i+1:]}) for i,v in enumerate(negative)]
  false_accepts=sum(e['accepted'] for e in folds)
  separation=min(e['score'] for e in owner)-max(e['score'] for e in folds)
  snapshot=evidence_snapshot(db,plan);revision=digest(snapshot)
  def same_bank():
   return isinstance(live,dict) and set(live)==set(bank) and all(len(live[k])==len(bank[k]) and all(similarity(unit(a),b)>1-1e-10 for a,b in zip(live[k],bank[k])) for k in bank)
  active=row[2]==COHORT_POLICY and same_bank()
  qualifies=new_count==5 and new_count>=old_count and false_accepts==0 and separation>=.2
  proposal={'voice_id':row[0],'samples':bank,'policy':COHORT_POLICY,'plan':plan,'snapshot':snapshot,'revision':revision} if qualifies and not active else None
  report={'status':('active_cohort_profile' if qualifies else 'active_profile_validation_failed') if active else 'eligible_for_controlled_activation' if qualifies else 'rejected',
          'revision':revision,'current_profile_revision':model_revision(live,row[2]),'active_policy':row[2],'candidate_policy':COHORT_POLICY,
          'threshold':.55,'window_threshold':.5,'required_second_reference_score':.5,'required_exclusion_margin':.2,'required_margin':.12,'strict_lock_threshold':.75,
          'training_samples':5,'owner_validation_samples':5,'other_validation_samples':5,'negative_validation_mode':'leave_one_utterance_out',
          'baseline_owner_accepts':old_count,'candidate_owner_accepts':new_count,'candidate_other_accepts':false_accepts,
          'baseline_owner_scores':[round(e['score'],4) for e in base],'candidate_owner_scores':[round(e['score'],4) for e in owner],
          'candidate_other_scores':[round(e['score'],4) for e in folds],'owner_exclusion_margins':[round(e['exclusion_margin'],4) for e in owner],
          'positive_negative_gap':round(separation,4),'required_gap':.2,'live_profile_changed':False,
          'window_validation':'not_performed_on_private_holdouts','physical_validation':'pending_ordinary_use','replay_detection':'not_installed','household_accuracy_verified':False}
  return report,proposal

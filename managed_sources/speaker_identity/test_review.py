import json,math,tempfile,unittest
from pathlib import Path
from policy import VoiceProfiles
from owner_calibration import OwnerCalibration
from review import CalibrationReview

class ReviewTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.p=VoiceProfiles(self.root/'profiles.sqlite')
  self.p.begin('mic','Martin')
  for _ in range(3):self.p.sample('mic',[1.,0.],4)
  self.p.bootstrap_authorization('Martin');self.identity=self.p.identify([1.,0.])
  self.c=OwnerCalibration(self.p,'mic');self.plan=self.root/'review-plan.json';roles=[]
  for i,role in enumerate(('owner_provided_calibration_unreviewed','other_speaker_comparison_unreviewed','owner_validation_unreviewed')):
   sid=f'{i:032x}';angle=(.8,2.3,.82)[i]
   with self.c.db() as db:
    db.execute('INSERT INTO owner_calibration_sessions(id,voice_id,device,created,expires,status) VALUES (?,?,?,?,?,?)',(sid,self.identity['memory_id'],'mic',0,600,'awaiting_review'))
    for n in range(5):db.execute('INSERT INTO owner_calibration_samples VALUES (?,?,?,?)',(sid,role+str(n),json.dumps([math.cos(angle),math.sin(angle)]),'{}'))
   roles.append({'session_id':sid,'role':role,'speaker_identity_confirmed_by_owner':True})
  self.config={'schema':1,'reference_profile':'Martin','sessions':roles,'automatic_profile_update':False};self.save();self.r=CalibrationReview(self.p,self.plan,'mic')
 def save(self):self.plan.write_text(json.dumps(self.config))
 def tearDown(self):self.tmp.cleanup()
 def prepare_repair(self):
  current=self.r.evaluate();proposal=self.r.proposal
  with self.c.db() as db:
   db.execute('UPDATE voices SET samples=? WHERE voice_id=?',(json.dumps(proposal['samples']),self.identity['memory_id']))
   db.execute('INSERT INTO voice_matching_policies VALUES (?,?)',(self.identity['memory_id'],'top_two_mean_calibrated_v1'))
   db.execute('UPDATE owner_calibration_samples SET vector=? WHERE session=?',(json.dumps([math.cos(3.4),math.sin(3.4)]),f'{1:032x}'))
   sid='e'*32
   db.execute('INSERT INTO owner_calibration_sessions(id,voice_id,device,created,expires,status,mode) VALUES (?,?,?,?,?,?,?)',(sid,self.identity['memory_id'],'mic',0,600,'awaiting_review','repair'))
   for name,angle,parts in [('fresh-training',1.85,[1.80,1.90]),('fresh-holdout',1.95,[1.92,1.98])]:
    db.execute('INSERT INTO owner_calibration_samples VALUES (?,?,?,?)',(sid,name,json.dumps([math.cos(angle),math.sin(angle)]),'{}'))
    db.execute('INSERT INTO owner_calibration_windows VALUES (?,?,?)',(sid,name,json.dumps([[math.cos(a),math.sin(a)] for a in parts])))
  self.config['schema']=2;self.config['sessions'].append({'session_id':sid,'role':'owner_duration_repair_unreviewed','speaker_identity_confirmed_by_owner':True});self.save()
 def test_repair_uses_training_parts_but_independently_validates_new_whole_and_windows(self):
  self.prepare_repair();result=self.r.evaluate()
  self.assertEqual(result['status'],'eligible_for_controlled_activation')
  self.assertEqual(result['baseline_owner_accepts'],5);self.assertEqual(result['candidate_owner_accepts'],6)
  self.assertEqual(result['candidate_other_accepts'],0)
  self.assertEqual(result['repair_holdout_windows'],2)
  heldout=[math.cos(1.95),math.sin(1.95)]
  self.assertNotIn(heldout,self.r.proposal['samples'])
 def test_repair_revision_binds_private_training_windows(self):
  self.prepare_repair();old=self.r.evaluate()['revision']
  with self.c.db() as db:db.execute('UPDATE owner_calibration_windows SET windows=? WHERE utterance=?',(json.dumps([[math.cos(1.81),math.sin(1.81)],[math.cos(1.90),math.sin(1.90)]]),'fresh-training'))
  self.assertNotEqual(old,self.r.evaluate()['revision'])
 def test_repair_bad_holdout_window_or_missing_evidence_blocks_activation(self):
  self.prepare_repair()
  with self.c.db() as db:db.execute('UPDATE owner_calibration_windows SET windows=? WHERE utterance=?',(json.dumps([[math.cos(1.92),math.sin(1.92)],[math.cos(2.8),math.sin(2.8)]]),'fresh-holdout'))
  self.assertEqual(self.r.evaluate()['status'],'rejected')
  with self.c.db() as db:db.execute('DELETE FROM owner_calibration_windows WHERE utterance=?',('fresh-holdout',))
  self.assertEqual(self.r.evaluate()['status'],'blocked')
 def test_reports_independent_validation_improvement_without_modifying_profile(self):
  before=self.p.anchors(self.identity['memory_id']);result=self.r.evaluate()
  self.assertEqual(result['status'],'eligible_for_controlled_activation')
  self.assertEqual(result['baseline_owner_accepts'],0);self.assertEqual(result['candidate_owner_accepts'],5)
  self.assertEqual(result['candidate_other_accepts'],0);self.assertFalse(result['live_profile_changed'])
  self.assertEqual(self.p.identify([1.,0.])['score'],1)
  self.assertEqual(before,self.p.anchors(self.identity['memory_id']))
  for private in ('Martin','memory_id','vector'):self.assertNotIn(private,str(result))
 def test_holdout_reuse_and_unconfirmed_roles_are_blocked(self):
  self.config['sessions'][2]['session_id']=self.config['sessions'][0]['session_id'];self.save()
  self.assertEqual(self.r.evaluate()['status'],'blocked')
  self.config['sessions'][2]['session_id']=f'{2:032x}';self.config['sessions'][2]['speaker_identity_confirmed_by_owner']=False;self.save()
  self.assertEqual(self.r.evaluate()['status'],'blocked')
 def test_candidate_that_accepts_other_speaker_is_rejected(self):
  with self.c.db() as db:db.execute('UPDATE owner_calibration_samples SET vector=? WHERE session=?',(json.dumps([math.cos(.8),math.sin(.8)]),f'{1:032x}'))
  self.assertEqual(self.r.evaluate()['status'],'rejected')
 def test_same_utterance_cannot_train_and_validate(self):
  with self.c.db() as db:db.execute('UPDATE owner_calibration_samples SET utterance=? WHERE session=? AND utterance=?',('owner_provided_calibration_unreviewed0',f'{2:032x}','owner_validation_unreviewed0'))
  self.assertEqual(self.r.evaluate()['status'],'blocked')
 def test_mixed_training_dimensions_return_blocked_instead_of_raising(self):
  with self.c.db() as db:db.execute('UPDATE owner_calibration_samples SET vector=? WHERE session=? AND utterance=?',(json.dumps([1.,0.,0.]),f'{0:032x}','owner_provided_calibration_unreviewed0'))
  self.assertEqual(self.r.evaluate()['status'],'blocked')
 def test_distinct_voice_variants_are_not_lost_by_blending_with_anchor(self):
  with self.c.db() as db:
   for n in range(5):db.execute('UPDATE owner_calibration_samples SET vector=? WHERE session=? AND utterance=?',(json.dumps([math.cos(1.2+n*.01),math.sin(1.2+n*.01)]),f'{0:032x}','owner_provided_calibration_unreviewed'+str(n)))
   db.execute('UPDATE owner_calibration_samples SET vector=? WHERE session=?',(json.dumps([math.cos(1.4),math.sin(1.4)]),f'{2:032x}'))
   db.execute('UPDATE owner_calibration_samples SET vector=? WHERE session=?',(json.dumps([math.cos(2.8),math.sin(2.8)]),f'{1:032x}'))
  self.assertEqual(self.r.evaluate()['candidate_owner_accepts'],5)
 def test_review_uses_one_snapshot_when_other_writer_changes_holdout(self):
  import review as implementation
  import sqlite3,threading
  from unittest.mock import patch
  expected=self.r.evaluate()['revision'];original=implementation.evidence_snapshot
  modified=threading.Event();errors=[];threads=[]
  def write():
   try:
    with sqlite3.connect(self.p.path,timeout=5) as db:
     db.execute('UPDATE owner_calibration_samples SET vector=? WHERE session=?',(json.dumps([math.cos(.8),math.sin(.8)]),f'{1:032x}'))
     modified.set()
   except Exception as exc:errors.append(exc);modified.set()
  def concurrent_snapshot(db,plan):
   worker=threading.Thread(target=write);threads.append(worker);worker.start()
   self.assertTrue(modified.wait(2))
   return original(db,plan)
  try:
   with patch.object(implementation,'evidence_snapshot',side_effect=concurrent_snapshot):result=self.r.evaluate()
  finally:
   for worker in threads:worker.join(6)
  self.assertFalse(errors)
  self.assertEqual(result['revision'],expected)
  self.assertEqual(self.r.evaluate()['status'],'rejected')

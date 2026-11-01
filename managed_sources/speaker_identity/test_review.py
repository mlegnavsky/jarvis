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
 def test_reports_independent_validation_improvement_without_modifying_profile(self):
  before=self.p.anchors(self.identity['memory_id']);result=self.r.evaluate()
  self.assertEqual(result['status'],'eligible_for_window_test')
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

import tempfile, unittest
from pathlib import Path
from policy import VoiceProfiles
from adaptation import Adaptation

class AdaptationTests(unittest.TestCase):
 def test_retention_never_relabels_training_sample_as_independent_holdout(self):
  for n in range(10):self.a.offer(self.identity['memory_id'],self.evidence(conversation=str(n),utterance=str(n)))
  with self.assertRaises(ValueError):self.a.add_validation(self.identity['memory_id'],'0',[1.,0.],True)
 def test_validated_promotion_and_rollback_keep_original_anchors(self):
  import math
  v=lambda angle:[math.cos(angle),math.sin(angle)]
  original=self.db.anchors(self.identity['memory_id'])
  self.a.offer(self.identity['memory_id'],self.evidence(vector=v(.3),windows=[v(.3),v(.3)],replay_live=True))
  for n in range(5):
   self.a.add_validation(self.identity['memory_id'],'g'+str(n),v(.74+n*.001),True)
   self.a.add_validation(self.identity['memory_id'],'n'+str(n),v(2+n*.01),False)
  result=self.a.evaluate(self.identity['memory_id']);self.assertEqual(result['status'],'eligible')
  receipt=self.a.promote(self.identity['memory_id'],result['revision'])
  self.assertEqual(original,self.db.anchors(self.identity['memory_id']))
  self.assertEqual(self.a.rollback(self.identity['memory_id'],receipt['revision'])['status'],'rolled_back')
  with self.db._db() as db:self.assertEqual(__import__('json').loads(db.execute('SELECT samples FROM voices').fetchone()[0]),original)
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.db=VoiceProfiles(Path(self.tmp.name)/'profiles.sqlite')
  self.db.begin('mic','Martin')
  for _ in range(3):self.db.sample('mic',[1.,0.],4)
  self.db.bootstrap_authorization('Martin');self.identity=self.db.identify([1.,0.])
  self.a=Adaptation(self.db)
 def tearDown(self):self.tmp.cleanup()
 def evidence(self,**kw):
  d=dict(vector=[.99,.1],seconds=6,quality={'status':'ok','clipped_fraction':0,'rms':.1},windows=[[1.,0.],[1.,0.]],playback=False,conversation='c',utterance='u',replay_live=False)
  return d|kw
 def test_candidate_never_overwrites_enrollment_or_live_profile(self):
  anchors=self.db.anchors(self.identity['memory_id'])
  result=self.a.offer(self.identity['memory_id'],self.evidence())
  self.assertEqual(result['status'],'quarantined')
  self.assertEqual(anchors,self.db.anchors(self.identity['memory_id']))
  self.assertEqual(self.a.evaluate(self.identity['memory_id'])['status'],'awaiting_validation')
 def test_short_mixed_noisy_playback_and_unauthorized_rejected(self):
  for patch in ({'seconds':1},{'windows':[[0.,1.],[1.,0.]]},{'playback':True},{'quality':{'status':'clipped'}},{'quality':None}):
   self.assertEqual(self.a.offer(self.identity['memory_id'],self.evidence(**patch))['status'],'rejected')
  self.assertEqual(self.a.offer('unknown',self.evidence())['status'],'rejected')
 def test_duplicate_conversation_does_not_dominate_profile(self):
  self.a.offer(self.identity['memory_id'],self.evidence())
  self.assertEqual(self.a.offer(self.identity['memory_id'],self.evidence(utterance='v'))['status'],'duplicate')
 def test_holdout_cannot_be_candidate_and_revision_is_required(self):
  self.a.offer(self.identity['memory_id'],self.evidence())
  with self.assertRaises(ValueError):self.a.add_validation(self.identity['memory_id'],'u',[1.,0.],True)
  with self.assertRaises(ValueError):self.a.promote(self.identity['memory_id'],'wrong')
 def test_candidates_are_bounded_and_survive_restart(self):
  for n in range(20):self.a.offer(self.identity['memory_id'],self.evidence(conversation=str(n),utterance=str(n),vector=[1.,n*.001]))
  self.assertLessEqual(Adaptation(self.db).summary()['candidates'],8)
 def test_centroid_adaptation_cannot_overwrite_manual_multireference_model(self):
  with self.db._db() as db:db.execute('INSERT INTO voice_matching_policies VALUES (?,?)',(self.identity['memory_id'],'top_two_mean_v1'))
  result=self.a.evaluate(self.identity['memory_id'])
  self.assertEqual(result['status'],'manual_matching_policy_requires_owner_control')
  with self.assertRaises(ValueError):self.a.promote(self.identity['memory_id'],result['revision'])

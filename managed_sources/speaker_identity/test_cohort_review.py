import json,math,unittest
from unittest.mock import patch
import test_review as fixtures
import test_matching_control as controls
from policy import COHORT_POLICY,COHORT_PARAMETERS

class CohortReviewTests(unittest.TestCase):
 tearDown=fixtures.ReviewTests.tearDown
 save=fixtures.ReviewTests.save
 request=controls.MatchingControlTests.request
 def setUp(self):
  fixtures.ReviewTests.setUp(self)
  self.config.update(schema=3,candidate_policy=COHORT_POLICY,policy_parameters=COHORT_PARAMETERS,allow_non_regressing_policy_migration=True)
  with self.c.db() as db:
   for n in range(5):db.execute('UPDATE owner_calibration_samples SET vector=? WHERE session=? AND utterance=?',(json.dumps([math.cos(2.2+n*.05),math.sin(2.2+n*.05)]),f'{1:032x}','other_speaker_comparison_unreviewed'+str(n)))
  self.save()
 def test_owner_holdouts_and_other_leave_one_out_qualify_without_live_mutation(self):
  result=self.r.evaluate()
  self.assertEqual(result['status'],'eligible_for_controlled_activation')
  self.assertEqual(result['candidate_owner_accepts'],5);self.assertEqual(result['candidate_other_accepts'],0)
  self.assertEqual(result['negative_validation_mode'],'leave_one_utterance_out')
  self.assertFalse(result['household_accuracy_verified']);self.assertEqual(self.p.identify([1,0])['status'],'recognized')
 def test_negative_fold_does_not_include_query_utterance(self):
  import cohort_review
  original=cohort_review.cohort_evidence;folds=[]
  def record(v,bank,**kwargs):
   if len(bank['negative'])==4:
    folds.append(bank)
    self.assertTrue(all(sum(a*b for a,b in zip(v,w))<1-1e-10 for w in bank['negative']))
   return original(v,bank,**kwargs)
  with patch.object(cohort_review,'cohort_evidence',side_effect=record):self.r.evaluate()
  self.assertEqual(len(folds),5)
 def test_overlapping_other_speaker_rejects_and_missing_owner_migration_flag_blocks(self):
  with self.c.db() as db:db.execute('UPDATE owner_calibration_samples SET vector=? WHERE session=?',(json.dumps([math.cos(.8),math.sin(.8)]),f'{1:032x}'))
  self.assertEqual(self.r.evaluate()['status'],'rejected')
  self.config['allow_non_regressing_policy_migration']=False;self.save()
  self.assertEqual(self.r.evaluate()['status'],'blocked')
 def test_activation_and_rollback_preserve_identity_permissions_and_anchor(self):
  anchor=self.p.anchors(self.identity['memory_id']);r=self.request()
  self.assertEqual(r['status'],'activated')
  self.assertEqual(self.p.identify([math.cos(.82),math.sin(.82)])['memory_id'],self.identity['memory_id'])
  self.assertEqual(self.r.evaluate()['status'],'active_cohort_profile')
  restored=self.request('rollback',r['current_profile_revision'],key='b'*32)
  self.assertEqual(restored['status'],'rolled_back');self.assertEqual(anchor,self.p.anchors(self.identity['memory_id']))
  self.assertTrue(self.p.is_authorized(self.identity['memory_id']))
 def test_changed_exclusion_evidence_rejects_activation(self):
  original=self.r.evaluate;expected=original()['revision']
  def changed():
   result=original()
   with self.c.db() as db:db.execute('UPDATE owner_calibration_samples SET vector=? WHERE session=?',(json.dumps([0.,-1.]),f'{1:032x}'))
   return result
  self.r.evaluate=changed
  self.assertEqual(self.request(expected=expected)['status'],'rejected')

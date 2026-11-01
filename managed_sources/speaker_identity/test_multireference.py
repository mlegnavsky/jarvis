import json,tempfile,unittest,math
from pathlib import Path
from policy import VoiceProfiles,profile_score

class MultiReferenceTests(unittest.TestCase):
 def test_one_close_example_is_not_enough(self):
  self.assertLess(profile_score([1.,0.],[[1.,0.],[0.,1.],[0.,1.]],'top_two_mean_v1'),.75)
 def test_two_close_examples_recognize_variant_without_lowering_threshold(self):
  refs=[[1.,0.],[1.,.1],[-1.,0.],[-1.,.1]]
  self.assertGreater(profile_score([1.,0.],refs,'top_two_mean_v1'),.75)
  self.assertLess(profile_score([1.,0.],refs,'centroid'),.75)
 def test_unknown_policy_and_dimension_mismatch_fail_closed(self):
  for policy,refs in [('invalid',[[1.,0.],[1.,0.]]),('top_two_mean_v1',[[1.,0.]]),('top_two_mean_v1',[[1.,0.],[1.,0.,0.]])]:
   with self.assertRaises(ValueError):profile_score([1.,0.],refs,policy)
 def test_legacy_profile_keeps_centroid_until_explicit_policy_selected(self):
  with tempfile.TemporaryDirectory() as d:
   p=VoiceProfiles(Path(d)/'voices.sqlite');p.begin('mic','Martin')
   for _ in range(3):p.sample('mic',[1.,0.],4)
   before=p.identify([1.,0.]);self.assertEqual(before['status'],'recognized')
   with p._db() as db:
    db.execute('UPDATE voices SET samples=?',(json.dumps([[1.,0.],[1.,.1],[-1.,0.],[-1.,.1]]),))
    db.execute('INSERT INTO voice_matching_policies VALUES (?,?)',(before['memory_id'],'top_two_mean_v1'))
   self.assertEqual(p.identify([1.,0.])['memory_id'],before['memory_id'])
   self.assertGreater(p.match_diagnostics([1.,0.])['best_score'],.75)

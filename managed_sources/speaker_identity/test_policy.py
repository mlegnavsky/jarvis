import math
from pathlib import Path
import tempfile
import unittest
from policy import VoiceProfiles

def vector(angle):return [math.cos(angle),math.sin(angle)]

class VoiceProfileTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'profiles.sqlite'
  self.db=VoiceProfiles(self.path,clock=lambda:1000)
 def tearDown(self):self.tmp.cleanup()
 def enroll(self,name='Martin',angle=0):
  self.db.begin('device',name)
  for n in range(3):result=self.db.sample('device',vector(angle+n*.01),4)
  return result
 def test_three_explicit_samples_required_and_survive_restart(self):
  self.db.begin('device','Martin')
  self.assertEqual(self.db.sample('device',vector(0),4)['status'],'enrolling')
  self.assertEqual(self.db.sample('device',vector(.01),4)['status'],'enrolling')
  self.assertEqual(self.db.sample('device',vector(.02),4)['status'],'enrolled')
  self.assertEqual(VoiceProfiles(self.path).identify(vector(.03))['name'],'Martin')
 def test_no_automatic_profiles_from_unknown_audio(self):
  self.assertEqual(self.db.identify(vector(0))['status'],'unknown')
  self.assertEqual(self.db.count(),0)
 def test_different_voice_and_ambiguous_profiles_stay_unknown(self):
  self.enroll()
  self.assertEqual(self.db.identify(vector(2))['status'],'unknown')
  self.enroll('Iris',.2)
  self.assertEqual(self.db.identify(vector(.1))['status'],'ambiguous')
 def test_short_low_quality_and_mixed_enrollment_are_not_saved(self):
  self.db.begin('device','Martin')
  self.assertEqual(self.db.sample('device',vector(0),1)['status'],'too_short')
  self.db.sample('device',vector(0),4)
  self.assertEqual(self.db.sample('device',vector(2),4)['status'],'inconsistent')
  self.assertEqual(self.db.count(),0)
 def test_expired_enrollment_does_not_continue(self):
  self.db.begin('device','Martin');self.db.clock=lambda:2000
  self.assertEqual(self.db.sample('device',vector(0),4)['status'],'not_enrolling')
 def test_existing_profile_cannot_be_overwritten_by_same_name(self):
  self.enroll()
  self.assertEqual(self.db.begin('other','Martin')['status'],'exists')
 def test_delete_clears_embedding_and_pending_enrollment(self):
  self.enroll();self.db.forget('Martin')
  self.assertEqual(self.db.count(),0)
  self.assertEqual(self.db.identify(vector(0))['status'],'unknown')
 def test_invalid_vectors_are_rejected(self):
  for v in [[0,0],[float('nan'),1],[float('inf'),0]]:
   with self.assertRaises(ValueError):self.db.identify(v)
 def test_reenrollment_never_reuses_previous_memory_identity(self):
  self.enroll();before=self.db.identify(vector(0))
  self.assertIn('memory_id',before)
  self.db.forget('Martin');self.enroll()
  self.assertNotEqual(before['memory_id'],self.db.identify(vector(0))['memory_id'])

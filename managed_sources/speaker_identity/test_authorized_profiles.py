import json
import tempfile
import unittest
from pathlib import Path
from policy import VoiceProfiles

class AuthorizedProfilesTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.db=VoiceProfiles(Path(self.tmp.name)/'profiles.sqlite')
  self.enroll()
 def tearDown(self):self.tmp.cleanup()
 def enroll(self):
  self.db.begin('mic','Martin')
  for _ in range(3):self.db.sample('mic',[1.,0.],4)
 def test_enrollment_does_not_grant_permission(self):
  identity=self.db.identify([1.,0.])
  self.assertFalse(self.db.is_authorized(identity['memory_id']))
 def test_explicit_bootstrap_is_stable_and_never_reauthorizes_same_name(self):
  self.db.bootstrap_authorization('Martin')
  before=self.db.identify([1.,0.])
  self.assertTrue(self.db.is_authorized(before['memory_id']))
  self.db.forget('Martin');self.enroll();self.db.bootstrap_authorization('Martin')
  after=self.db.identify([1.,0.])
  self.assertNotEqual(before['memory_id'],after['memory_id'])
  self.assertFalse(self.db.is_authorized(after['memory_id']))
 def test_original_anchors_survive_manual_improvement(self):
  before=self.db.anchors(self.db.identify([1.,0.])['memory_id'])
  self.db.improve('Martin',[.99,.1],4)
  self.assertEqual(before,self.db.anchors(self.db.identify([1.,0.])['memory_id']))
 def test_permission_survives_restart(self):
  self.db.bootstrap_authorization('Martin')
  identity=self.db.identify([1.,0.])
  self.assertTrue(VoiceProfiles(self.db.path).is_authorized(identity['memory_id']))

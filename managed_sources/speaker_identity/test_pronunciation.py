import tempfile,unittest
from pathlib import Path
from policy import VoiceProfiles
from pronunciation import Pronunciation
class PronunciationTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.db=VoiceProfiles(Path(self.tmp.name)/'p.sqlite');self.db.begin('m','Martin')
  for _ in range(3):self.db.sample('m',[1.,0.],4)
  self.db.bootstrap_authorization('Martin');self.id=self.db.identify([1.,0.])['memory_id'];self.p=Pronunciation(self.db)
 def tearDown(self):self.tmp.cleanup()
 def test_explicit_confirmed_alias_never_grants_identity(self):
  self.p.propose(self.id,'rosviť','rozsviť')
  self.assertEqual(self.p.resolve(self.id,'rosviť'),'rosvit')
  self.p.confirm(self.id,'rosviť','rozsviť')
  self.assertEqual(self.p.resolve(self.id,'rosviť'),'rozsvit')
  self.assertEqual(self.p.resolve('other','rosviť'),'rosvit')
 def test_unknown_speaker_cannot_add_alias_or_map_arbitrary_actions(self):
  with self.assertRaises(ValueError):self.p.propose('other','rosvit','rozsvit')
  with self.assertRaises(ValueError):self.p.propose(self.id,'ahoj','vypni alarm')

import unittest
from manifest import build_manifest

class ManifestTests(unittest.TestCase):
 def test_history_changes_only_when_code_changes_and_does_not_copy_private_data(self):
  report={'runtime_version':'1.1.0','status':'ready','authorization':{'authorized_profiles':1},'adaptation':{'candidates':2},'vector':[1,0],'name':'private'}
  a=build_manifest(report,{'policy.py':'aaa'},None,'first',{})
  b=build_manifest(report,{'policy.py':'aaa'},a,'second',{})
  c=build_manifest(report,{'policy.py':'bbb'},b,'third',{})
  self.assertEqual(len(b['change_history']),1);self.assertEqual(len(c['change_history']),2)
  self.assertNotIn('private',str(c));self.assertNotIn('vector',c)
  self.assertEqual(c['procedures']['admin']['service'],'jarvis.admin')
 def test_manifest_never_claims_wake_or_replay_accuracy(self):
  m=build_manifest({'status':'ready'},{},None,'now',{})
  self.assertFalse(m['verification']['household_accuracy_verified'])
  self.assertEqual(m['verification']['replay_detection'],'not_installed')

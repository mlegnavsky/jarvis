import importlib.util
from pathlib import Path
import unittest
class NotificationTests(unittest.TestCase):
 def module(self):
  p=Path('scripts/notify_plesk.py');self.assertTrue(p.exists(),'notification helper missing')
  spec=importlib.util.spec_from_file_location('notify',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
 def test_rewrites_known_panel_alias_preserving_uuid(self):
  m=self.module();self.assertEqual(m.canonical_url('https://give-get.com:8443/modules/git/public/web-hook.php?uuid=test%2Bvalue'),'https://lister.thajsky-raj.cz/modules/git/public/web-hook.php?uuid=test%2Bvalue')
 def test_rejects_unrelated_host(self):
  m=self.module()
  with self.assertRaises(ValueError):m.canonical_url('https://other.example/modules/git/public/web-hook.php?uuid=x')
 def test_rejects_credentials(self):
  m=self.module()
  with self.assertRaises(ValueError):m.canonical_url('https://user:pass@lister.thajsky-raj.cz/modules/git/public/web-hook.php?uuid=x')

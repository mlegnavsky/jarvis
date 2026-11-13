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

 def test_sends_post_and_accepts_204(self):
  from unittest.mock import patch,MagicMock
  m=self.module();response=MagicMock();response.status=204;response.__enter__.return_value=response
  opener=MagicMock();opener.open.return_value=response
  with patch.dict(m.os.environ,{'LAB_WEBHOOK':'https://give-get.com:8443/modules/git/public/web-hook.php?uuid=test'}),patch.object(m.urllib.request,'build_opener',return_value=opener):
   self.assertEqual(m.main(),0)
  self.assertEqual(opener.open.call_args.args[0].get_method(),'POST')

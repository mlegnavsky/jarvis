import json
from pathlib import Path
import tempfile
from types import SimpleNamespace as NS
import unittest

class VoicePolicyTests(unittest.TestCase):
 def test_only_designated_voice_uses_selected_model(self):
  import voice_policy as p
  policy={'status':'selected','model':'gpt-4.1-mini'}
  primary=NS(device_id=None,satellite_id=p.SATELLITE)
  self.assertEqual(p.request_policy(primary,'gpt-4o',300,policy)[:2],('gpt-4.1-mini',512))
  for user in (NS(device_id=None,satellite_id=None),NS(device_id='other',satellite_id='other')):
   self.assertEqual(p.request_policy(user,'gpt-4o',300,policy)[:2],('gpt-4o',300))
 def test_invalid_missing_and_symlink_policy_use_configured_model(self):
  import voice_policy as p
  with tempfile.TemporaryDirectory() as d:
   path=Path(d)/'voice-settings.json'
   self.assertEqual(p.read_policy(str(path))['model'],None)
   for value in ({'schema':1,'model':'private-model'},{'schema':1,'model':'gpt-4.1-mini','url':'private'}, {'schema':True,'model':'gpt-4.1-mini'}):
    path.write_text(json.dumps(value));self.assertEqual(p.read_policy(str(path))['model'],None)
   path.write_text(json.dumps({'schema':1,'model':'gpt-4.1-mini'}))
   self.assertEqual(p.read_policy(str(path))['model'],'gpt-4.1-mini')
   link=Path(d)/'link.json';link.symlink_to(path)
   self.assertEqual(p.read_policy(str(link))['model'],None)
 def test_model_metadata_exposes_no_arbitrary_private_identifier(self):
  import voice_policy as p
  self.assertEqual(p.safe_model('sk-PRIVATE-secret-value'),'custom_model')
  self.assertEqual(p.safe_model('gpt-4.1-mini'),'gpt-4.1-mini')

 def test_non_regular_policy_cannot_block_query(self):
  import os,subprocess,sys
  with tempfile.TemporaryDirectory() as d:
   path=Path(d)/'voice-settings.json';os.mkfifo(path)
   source=Path(__file__).with_name('voice_policy.py')
   code="import importlib.util; s=importlib.util.spec_from_file_location('p', %r); p=importlib.util.module_from_spec(s); s.loader.exec_module(p); assert p.read_policy(%r)['model'] is None" % (str(source),str(path))
   try:result=subprocess.run([sys.executable,'-c',code],timeout=.5,capture_output=True)
   except subprocess.TimeoutExpired:self.fail('FIFO policy blocked query')
   self.assertEqual(result.returncode,0,result.stderr.decode())

 def test_selected_model_preserves_existing_long_answer_budget(self):
  import voice_policy as p
  user=NS(device_id=None,satellite_id=p.SATELLITE)
  selected=p.request_policy(user,'gpt-4o',4096,{'status':'selected','model':'gpt-4.1-mini'})
  self.assertEqual(selected[1],4096)

import base64,hashlib,tempfile,unittest
from pathlib import Path
from app.firmware import FirmwareStore
from app.policy import APIError

TARGET='home-assistant-voice-0a8bde.yaml'
CONFIG='''api:
  encryption:
    key: !secret device_key
wifi:
  password: !secret wifi_password
micro_wake_word:
  models:
    - model: old.json # keep comment
      id: jarvis_cz
'''
class StoreTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);(self.root/'esphome').mkdir();(self.root/'esphome'/TARGET).write_text(CONFIG)
  self.store=FirmwareStore(self.root,[TARGET])
 def tearDown(self):self.tmp.cleanup()
 def payload(self):
  binary=b'\x20\x00\x00\x00TFL3'+b'\x00'*128
  return {'target':TARGET,'model_id':'jarvis_cz','model_base64':base64.b64encode(binary).decode(),'sha256':hashlib.sha256(binary).hexdigest(),'manifest':{'wake_word':'Jarvis','micro':{'probability_cutoff':.98,'sliding_window_size':5,'feature_step_size':10,'tensor_arena_size':65536}},'expected_revision':self.store.metadata(TARGET)['revision']}
 def test_private_model_install_preserves_credentials_and_comments(self):
  args=self.payload();result=self.store.install_model(args)
  content=(self.root/'esphome'/TARGET).read_text()
  self.assertIn('key: !secret device_key',content);self.assertIn('password: !secret wifi_password',content);self.assertIn('# keep comment',content)
  self.assertEqual(content.replace(result['manifest_path'],'old.json').replace('"old.json"','old.json'),CONFIG)
  self.assertEqual((self.root/'esphome'/result['model_path']).read_bytes()[4:8],b'TFL3')
  self.assertNotIn('device_key',str(self.store.metadata(TARGET)))
 def test_revision_conflict_does_not_write_anything(self):
  args=self.payload();args['expected_revision']='0'*64
  with self.assertRaises(APIError):self.store.install_model(args)
  self.assertFalse((self.root/'esphome/jarvis_models').exists())
 def test_invalid_digest_model_and_unknown_id_rejected(self):
  for patch in [{'sha256':'0'*64},{'model_base64':base64.b64encode(b'not a model').decode()},{'model_id':'unknown'}]:
   args=self.payload();args.update(patch)
   with self.assertRaises(APIError):self.store.install_model(args)
 def test_target_traversal_and_symlinks_rejected(self):
  for target in ['../secrets.yaml','secrets.yaml','other.yaml']:
   with self.assertRaises(APIError):self.store.metadata(target)
  p=self.root/'esphome'/TARGET;p.unlink();p.symlink_to('/etc/passwd')
  with self.assertRaises(APIError):self.store.metadata(TARGET)
 def test_alias_model_cannot_corrupt_another_model(self):
  (self.root/'esphome'/TARGET).write_text('micro_wake_word:\n  models:\n    - model: &m old.json\n      id: first\n    - model: *m\n      id: jarvis_cz\n')
  before=(self.root/'esphome'/TARGET).read_text();args=self.payload()
  with self.assertRaises(APIError):self.store.install_model(args)
  self.assertEqual((self.root/'esphome'/TARGET).read_text(),before)
 def test_same_weights_can_get_new_manifest_without_overwrite(self):
  args=self.payload();first=self.store.install_model(args)
  args=self.payload();args['manifest']['micro']['probability_cutoff']=.97
  second=self.store.install_model(args)
  self.assertNotEqual(first['manifest_path'],second['manifest_path'])
 def test_generated_manifest_satisfies_v2_required_minimum_version(self):
  import json
  result=self.store.install_model(self.payload())
  manifest=json.loads((self.root/'esphome'/result['manifest_path']).read_text())
  self.assertEqual(manifest['micro']['minimum_esphome_version'],'2024.7.0')

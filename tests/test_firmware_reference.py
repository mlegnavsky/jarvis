import hashlib
from pathlib import Path
import tempfile
import unittest
from app.firmware import FirmwareStore
from app.policy import APIError

TARGET='home-assistant-voice-0a8bde.yaml'
SOURCE='''# Original private configuration stays byte-for-byte intact.
packages:
  device: github://esphome/home-assistant-voice-pe/home-assistant-voice.yaml@26.10.1
wifi:
  password: !secret NEVER_EXPOSE_WIFI
api:
  encryption:
    key: !secret NEVER_EXPOSE_KEY
micro_wake_word:
  models:
    - id: jarvis_cz
      model: private.json
'''

class ReferenceConfigTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.path=self.root/'esphome'/TARGET
        self.path.parent.mkdir();self.path.write_text(SOURCE)
        self.store=FirmwareStore(self.root,[TARGET])
    def args(self):
        return dict(target=TARGET,source_sha='a'*40,profile='legacy',
            expected_revision=hashlib.sha256(self.path.read_bytes()).hexdigest())
    def test_fixed_source_stage_preserves_secrets_and_every_original_byte(self):
        result=self.store.stage_reference(self.args())
        self.assertFalse(result['activation_performed'])
        text=self.path.read_text();a=text.index('  jarvis_reference:');b=text.index('wifi:')
        self.assertEqual(text[:a]+text[b:],SOURCE)
        self.assertIn('ref: '+ 'a'*40,text)
        self.assertIn('firmware/reference_bridge/voice-pe-legacy.yaml',text)
        self.assertNotIn('NEVER_EXPOSE',str(result))
    def test_stale_revision_and_unknown_profile_cannot_write(self):
        for overrides in ({'expected_revision':'0'*64},{'profile':'../secrets'},
                          {'source_sha':'main'},{'target':'other.yaml'}):
            args=self.args();args.update(overrides)
            with self.assertRaises(APIError):self.store.stage_reference(args)
            self.assertEqual(self.path.read_text(),SOURCE)
    def test_stock_sendspin_experiment_cannot_be_staged_or_silence_existing_player(self):
        args=self.args();args['profile']='stock_sendspin'
        with self.assertRaises(APIError):self.store.stage_reference(args)
        self.assertEqual(self.path.read_text(),SOURCE)
    def test_existing_overlay_or_ambiguous_yaml_cannot_be_overwritten(self):
        variants=[SOURCE.replace('packages:', 'packages: {a: b}\npackages:'),
            SOURCE.replace('  device:', '  jarvis_reference: already\n  device:'),
            SOURCE.replace('packages:\n  device: github://esphome/home-assistant-voice-pe/home-assistant-voice.yaml@26.10.1', 'packages: {device: original}')]
        for variant in variants:
            self.path.write_text(variant)
            with self.assertRaises(APIError):self.store.stage_reference(self.args())
            self.assertEqual(self.path.read_text(),variant)
    def test_metadata_exposes_only_allowlisted_public_package_reference(self):
        value=self.store.metadata(TARGET)
        self.assertNotIn('NEVER_EXPOSE',str(value))
        self.assertEqual(value['reference_profile']['public_voice_package'],
            {'repository':'esphome/home-assistant-voice-pe','path':'home-assistant-voice.yaml','ref':'26.10.1'})
        self.assertTrue(value['reference_profile']['api_encryption_declared'])
        self.path.write_text(SOURCE.replace('github://esphome/home-assistant-voice-pe/home-assistant-voice.yaml@26.10.1','https://PRIVATE/token'))
        value=self.store.metadata(TARGET)
        self.assertNotIn('PRIVATE',str(value))
        self.assertIsNone(value['reference_profile']['public_voice_package'])

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
        return dict(target=TARGET,source_sha='a'*40,profile='legacy',reference_server_id='P'*43,
            expected_revision=hashlib.sha256(self.path.read_bytes()).hexdigest())
    def test_fixed_source_stage_preserves_secrets_and_every_original_byte(self):
        result=self.store.stage_reference(self.args())
        self.assertFalse(result['activation_performed'])
        text=self.path.read_text();a=text.index('  jarvis_reference:');b=text.index('wifi:')
        self.assertEqual(text[:a]+text[b:],SOURCE)
        self.assertIn('ref: '+ 'a'*40,text)
        self.assertIn('firmware/reference_bridge/voice-pe-legacy.yaml',text)
        self.assertIn('jarvis_reference_server_id: "'+'P'*43+'"',text)
        self.assertNotIn('NEVER_EXPOSE',str(result))
    def test_stale_revision_and_unknown_profile_cannot_write(self):
        for overrides in ({'expected_revision':'0'*64},{'profile':'../secrets'},
                          {'source_sha':'main'},{'target':'other.yaml'}):
            args=self.args();args.update(overrides)
            with self.assertRaises(APIError):self.store.stage_reference(args)
            self.assertEqual(self.path.read_text(),SOURCE)
    def test_stock_profile_requires_public_identity_and_preserves_original_configuration(self):
        args=self.args();args['profile']='stock_sendspin'
        missing=dict(args);missing.pop('reference_server_id')
        with self.assertRaises(APIError):self.store.stage_reference(missing)
        self.assertEqual(self.path.read_text(),SOURCE)
        try:self.store.stage_reference(args)
        except APIError as exc:self.fail(f'identity-pinned stock profile was refused: {exc}')
        text=self.path.read_text();a=text.index('  jarvis_reference:');b=text.index('wifi:')
        self.assertEqual(text[:a]+text[b:],SOURCE)
        self.assertIn('voice-pe-stock-sendspin.yaml',text)
        self.assertIn('jarvis_reference_server_id: "'+'P'*43+'"',text)
    def test_missing_or_malformed_public_identity_cannot_write(self):
        for identity in (None,'','X'*42,'X'*44,'X'*42+'=','X'*40+'\nhi'):
            self.path.write_text(SOURCE)
            args=self.args();args['reference_server_id']=identity
            with self.subTest(identity=identity):
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

    def test_official_package_without_explicit_ref_is_recognized_and_preserved(self):
        source=SOURCE.replace('@26.10.1','')
        self.path.write_text(source)
        meta=self.store.metadata(TARGET)
        self.assertEqual(meta['reference_profile']['public_voice_package'],
            {'repository':'esphome/home-assistant-voice-pe','path':'home-assistant-voice.yaml','ref':None})
        args=self.args();args['expected_revision']=meta['revision']
        self.store.stage_reference(args)
        text=self.path.read_text();a=text.index('  jarvis_reference:');b=text.index('wifi:')
        self.assertEqual(text[:a]+text[b:],source)
        self.assertNotIn('NEVER_EXPOSE',str(meta))

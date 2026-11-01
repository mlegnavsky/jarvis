"""Firmware diagnostics expose a fixed audio schema, never source text."""
import importlib
import os
from pathlib import Path
import tempfile
import unittest


class FirmwareSnapshotTests(unittest.TestCase):
    def snapshot(self, source):
        module = importlib.import_module('firmware_snapshot')
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / 'esphome' / 'home-assistant-voice-0a8bde.yaml'
            path.parent.mkdir()
            path.write_text(source)
            return module.read_snapshot(Path(root))

    def test_private_values_and_lambdas_never_leave_fixed_schema(self):
        source = '''
wifi:
  password: !secret PRIVATE_PASSWORD
api:
  encryption:
    key: PRIVATE_KEY
packages:
  upstream: https://PRIVATE_HOST/PRIVATE_PATH
micro_wake_word:
  microphone:
    microphone: i2s_mics
    channels: 1
    gain_factor: 4
  vad:
  models:
    - id: jarvis_cz
      model: PRIVATE_MODEL_PATH
voice_assistant:
  microphone:
    - microphone: i2s_mics
      channels: 0
    - microphone: i2s_mics
      channels: 1
  noise_suppression_level: 0
  auto_gain: 0 dbfs
  volume_multiplier: 1
  on_end:
    - wait_until:
        not:
          voice_assistant.is_running:
    - lambda: !lambda return PRIVATE_LAMBDA;
  on_tts_end:
    - voice_assistant.stop:
select:
  - id: wake_word_sensitivity
    initial_option: Slightly sensitive
    on_value:
      lambda: !lambda |-
        id(jarvis_cz).set_probability_cutoff(247);
        return PRIVATE_OTHER;
'''
        value = self.snapshot(source)
        self.assertEqual(value['status'], 'observed')
        self.assertEqual(value['wake_microphone'], [{'channels': 1, 'gain_factor': 4}])
        self.assertEqual(value['assistant_microphones'], [{'channels': 0}, {'channels': 1}])
        self.assertTrue(value['wake_vad_configured'])
        self.assertTrue(value['packages_present'])
        self.assertEqual(value['assistant_audio']['auto_gain_dbfs'], 0)
        self.assertEqual(value['sensitivity_cutoff_models'], ['jarvis_cz'])
        self.assertEqual(value['assistant_lifecycle']['on_tts_end']['stops_assistant'], True)
        self.assertEqual(value['assistant_lifecycle']['on_end']['contains_lambda'], True)
        self.assertNotIn('PRIVATE', str(value))
        self.assertNotIn('247', str(value))

    def test_missing_audio_fields_stay_unknown(self):
        value = self.snapshot('packages:\n  remote: PRIVATE_URL\n')
        self.assertIsNone(value['wake_microphone'])
        self.assertIsNone(value['wake_vad_configured'])
        self.assertIsNone(value['assistant_lifecycle']['on_end'])

    def test_bad_or_oversized_yaml_is_not_echoed(self):
        for source in ('micro_wake_word: [SECRET', 'SECRET' * 30000):
            value = self.snapshot(source)
            self.assertEqual(value['status'], 'unavailable')
            self.assertNotIn('SECRET', str(value))

    def test_symlinked_source_is_not_read(self):
        module = importlib.import_module('firmware_snapshot')
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / 'esphome' / 'home-assistant-voice-0a8bde.yaml'
            path.parent.mkdir()
            secret = Path(root) / 'private.yaml'
            secret.write_text('micro_wake_word:\n  vad:\n')
            path.symlink_to(secret)
            self.assertEqual(module.read_snapshot(Path(root))['status'], 'unavailable')

    def test_symlinked_parent_is_not_read(self):
        module = importlib.import_module('firmware_snapshot')
        with tempfile.TemporaryDirectory() as root:
            other = Path(root) / 'other-private'
            other.mkdir()
            (other / module.TARGET).write_text('micro_wake_word:\n  vad:\n')
            (Path(root) / 'esphome').symlink_to(other, target_is_directory=True)
            self.assertEqual(module.read_snapshot(Path(root))['status'], 'unavailable')

    def test_duplicate_keys_are_ambiguous_not_observed(self):
        for source in ('voice_assistant: {}\nvoice_assistant: {}\n',
                       'voice_assistant:\n  microphone: {}\n  microphone: {}\n'):
            self.assertEqual(self.snapshot(source)['status'], 'unavailable')

    def test_fifo_is_not_opened(self):
        module = importlib.import_module('firmware_snapshot')
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / 'esphome' / module.TARGET
            path.parent.mkdir()
            os.mkfifo(path)
            self.assertEqual(module.read_snapshot(Path(root))['status'], 'unavailable')

import unittest
from media import VolumeGuard


class AudioOutputs:
    """In-memory transport; no production device is contacted."""
    def __init__(self):
        self.volumes = {'tv': .7, 'apple_audio': .4}
        self.fail = set()
        self.calls = []

    def get_volume(self, entity):
        return self.volumes[entity]

    def set_volume(self, entity, level):
        self.calls.append((entity, level))
        if entity in self.fail:
            raise OSError('unreachable')
        self.volumes[entity] = level


class VolumeTests(unittest.TestCase):
    def setUp(self):
        self.audio = AudioOutputs()
        self.guard = VolumeGuard(self.audio, ('tv', 'apple_audio'), duck_level=.15)

    def test_duck_until_end_then_restore_exact_original(self):
        self.assertEqual(self.guard.begin(), {})
        self.assertEqual(self.audio.volumes, {'tv': .15, 'apple_audio': .15})
        self.assertEqual(self.guard.end(), {})
        self.assertEqual(self.audio.volumes, {'tv': .7, 'apple_audio': .4})
        self.assertEqual(self.guard.pending, {})

    def test_duplicate_wake_keeps_original_snapshot(self):
        self.guard.begin()
        self.guard.begin()
        self.guard.end()
        self.assertEqual(self.audio.volumes['tv'], .7)

    def test_never_increase_low_volume(self):
        self.audio.volumes['tv'] = .05
        self.guard.begin()
        self.assertEqual(self.audio.volumes['tv'], .05)

    def test_partial_failure_still_ducks_other_outputs(self):
        self.audio.fail.add('tv')
        self.assertIn('tv', self.guard.begin())
        self.assertEqual(self.audio.volumes['apple_audio'], .15)
        self.audio.fail.clear()
        self.guard.end()
        self.assertEqual(self.audio.volumes['tv'], .7)

    def test_restore_error_retains_snapshot_for_retry(self):
        self.guard.begin()
        self.audio.fail.add('tv')
        self.assertIn('tv', self.guard.end())
        self.assertEqual(self.guard.pending, {'tv': .7})
        self.audio.fail.clear()
        self.assertEqual(self.guard.end(), {})
        self.assertEqual(self.audio.volumes['tv'], .7)

    def test_invalid_volume_is_not_written(self):
        self.audio.volumes['tv'] = float('nan')
        self.assertIn('tv', self.guard.begin())
        self.assertFalse(any(entity == 'tv' for entity, _ in self.audio.calls))

    def test_new_session_cannot_overwrite_pending_restore(self):
        self.guard.begin()
        self.audio.fail.add('tv')
        self.guard.end()
        with self.assertRaises(RuntimeError):
            self.guard.begin()
        self.assertEqual(self.guard.pending, {'tv': .7})


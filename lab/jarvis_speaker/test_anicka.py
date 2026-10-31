import unittest
from controller import Mode, SpeakerController


class AnickaTests(unittest.TestCase):
    def test_new_wake_and_timeout_before_speech(self):
        now = [0.0]
        ctrl = SpeakerController(clock=lambda: now[0])
        self.assertFalse(ctrl.wake('Jarvisi'))
        self.assertTrue(ctrl.wake('  ANIČKO  '))
        now[0] = 3.0
        ctrl.speech_started()
        self.assertEqual(ctrl.mode, Mode.IDLE)


if __name__ == '__main__':
    unittest.main()

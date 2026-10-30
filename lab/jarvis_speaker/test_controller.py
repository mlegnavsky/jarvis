import unittest
from controller import Mode, SpeakerConfig, SpeakerController


class SpeakerTests(unittest.TestCase):
    def setUp(self):
        self.now = 100.0
        self.ctrl = SpeakerController(clock=lambda: self.now)

    def test_wake_only_selected_phrase(self):
        self.assertFalse(self.ctrl.wake("zhasni"))
        self.assertTrue(self.ctrl.wake("Jarvisi"))
        self.assertEqual(self.ctrl.mode, Mode.LISTENING)

    def test_barge_in(self):
        self.ctrl.wake("jarvisi")
        self.ctrl.response_started()
        self.assertTrue(self.ctrl.speech_started())
        self.assertTrue(self.ctrl.interrupt_tts)
        self.assertEqual(self.ctrl.mode, Mode.LISTENING)

    def test_followup_timeout(self):
        self.ctrl.wake("jarvisi")
        self.ctrl.response_started()
        self.ctrl.response_finished()
        self.now += 3.1
        self.ctrl.tick()
        self.assertEqual(self.ctrl.mode, Mode.IDLE)

    def test_unknown_speaker(self):
        self.ctrl.voice_identity("Martin", 0.4)
        self.assertIsNone(self.ctrl.speaker_id)
        self.ctrl.voice_identity("Martin", 0.9)
        self.assertEqual(self.ctrl.speaker_id, "Martin")


if __name__ == "__main__":
    unittest.main()

import unittest
from controller import Mode, SpeakerConfig, SpeakerController


class IdentityHelper:
    def identify(self, identity, confidence):
        self.ctrl.voice_identity(identity, confidence, utterance_id=self.ctrl.utterance_id)


class SpeakerTests(IdentityHelper, unittest.TestCase):
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
        self.assertEqual(self.ctrl.mode, Mode.CAPTURING)

    def test_followup_timeout(self):
        self.ctrl.wake("jarvisi")
        self.ctrl.response_started()
        self.ctrl.response_finished(playback_id=self.ctrl.playback_id)
        self.now += 3.1
        self.ctrl.tick()
        self.assertEqual(self.ctrl.mode, Mode.IDLE)

    def test_unknown_speaker(self):
        self.ctrl.wake("jarvisi")
        self.identify("Martin", 0.4)
        self.assertIsNone(self.ctrl.speaker_id)
        self.identify("Martin", 0.9)
        self.assertEqual(self.ctrl.speaker_id, "Martin")

class PolicyTests(IdentityHelper, unittest.TestCase):
    def setUp(self):
        self.now = 10.0
        self.ctrl = SpeakerController(
            SpeakerConfig(approved_speakers=frozenset({'Martin'})),
            clock=lambda: self.now)
        self.ctrl.wake('Jarvisi')

    def test_only_approved_profile_can_consume_one_command(self):
        self.identify('Guest', .99)
        self.assertFalse(self.ctrl.authorize_command(utterance_id=self.ctrl.utterance_id))
        self.identify('Martin', .99)
        self.assertTrue(self.ctrl.authorize_command(utterance_id=self.ctrl.utterance_id))
        self.assertFalse(self.ctrl.authorize_command(utterance_id=self.ctrl.utterance_id))

    def test_next_utterance_clears_identity(self):
        self.identify('Martin', .99)
        self.ctrl.speech_started()
        self.assertFalse(self.ctrl.authorize_command(utterance_id=self.ctrl.utterance_id))

    def test_playback_cannot_wake_or_interrupt(self):
        self.ctrl.end_session()
        self.assertFalse(self.ctrl.wake('Jarvisi', source='playback'))
        self.ctrl.wake('Jarvisi')
        self.ctrl.response_started()
        self.assertFalse(self.ctrl.speech_started(source='echo'))
        self.assertEqual(self.ctrl.mode, Mode.SPEAKING)

    def test_confidence_nonfinite_or_outside_range_is_rejected(self):
        for confidence in (float('nan'), float('inf'), 1.1, -1, .5):
            self.identify('Martin', confidence)
            self.assertFalse(self.ctrl.authorize_command(utterance_id=self.ctrl.utterance_id))

    def test_expired_proof_does_not_authorize(self):
        self.identify('Martin', .99)
        self.now += 4
        self.assertFalse(self.ctrl.authorize_command(utterance_id=self.ctrl.utterance_id))

    def test_followup_needs_new_verification(self):
        self.identify('Martin', .99)
        self.ctrl.response_started()
        self.ctrl.response_finished(playback_id=self.ctrl.playback_id)
        self.assertFalse(self.ctrl.authorize_command(utterance_id=self.ctrl.utterance_id))

    def test_processing_does_not_expire_while_waiting_for_answer(self):
        self.identify('Martin', .99)
        self.assertTrue(self.ctrl.authorize_command(utterance_id=self.ctrl.utterance_id))
        self.now += 10
        self.ctrl.tick()
        self.assertEqual(self.ctrl.mode, Mode.PROCESSING)

    def test_stale_output_callback_cannot_restart_session(self):
        session = self.ctrl.session_id
        self.ctrl.end_session()
        self.ctrl.response_finished(playback_id=0, session_id=session)
        self.assertEqual(self.ctrl.mode, Mode.IDLE)
        self.ctrl.wake('Jarvisi')
        self.ctrl.response_started()
        self.ctrl.response_finished(playback_id=0, session_id=session)
        self.assertEqual(self.ctrl.mode, Mode.SPEAKING)

    def test_unknown_introduction_never_authorizes(self):
        self.identify(None, 0)
        self.assertEqual(self.ctrl.unknown_speaker_prompt, 'Neznám váš hlas, jak se jmenujete?')
        self.assertFalse(self.ctrl.authorize_command(utterance_id=self.ctrl.utterance_id))

    def test_duplicate_wake_does_not_reset_verified_turn(self):
        session = self.ctrl.session_id
        self.identify('Martin', .99)
        self.assertFalse(self.ctrl.wake('Jarvisi'))
        self.assertEqual(self.ctrl.session_id, session)
        self.assertTrue(self.ctrl.authorize_command(utterance_id=self.ctrl.utterance_id))


class CallbackTests(IdentityHelper, unittest.TestCase):
    def setUp(self):
        self.now = 0.0
        self.ctrl = SpeakerController(SpeakerConfig(approved_speakers=frozenset({'Martin'})), clock=lambda: self.now)
        self.ctrl.wake('Jarvisi')

    def test_stale_identity_cannot_authorize_new_utterance(self):
        old = self.ctrl.utterance_id
        self.ctrl.speech_started()
        self.ctrl.voice_identity('Martin', .99, utterance_id=old)
        self.assertFalse(self.ctrl.authorize_command(utterance_id=self.ctrl.utterance_id))

    def test_wrong_utterance_cannot_consume_valid_proof(self):
        self.identify('Martin', .99)
        self.assertFalse(self.ctrl.authorize_command(utterance_id=self.ctrl.utterance_id - 1))

    def test_interrupted_playback_completion_cannot_finish_new_output(self):
        self.ctrl.response_started()
        old = self.ctrl.playback_id
        self.ctrl.speech_started()
        self.ctrl.response_started()
        self.ctrl.response_finished(playback_id=old)
        self.assertEqual(self.ctrl.mode, Mode.SPEAKING)

    def test_long_command_does_not_hit_followup_silence_timeout(self):
        self.ctrl.speech_started()
        self.now = 5.0
        self.identify('Martin', .99)
        self.assertTrue(self.ctrl.authorize_command(utterance_id=self.ctrl.utterance_id))

    def test_capture_is_still_bounded(self):
        self.ctrl.speech_started()
        self.now = 31.0
        self.ctrl.tick()
        self.assertEqual(self.ctrl.mode, Mode.IDLE)


if __name__ == '__main__':
    unittest.main()

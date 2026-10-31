import unittest
from controller import Mode
from simulation import Simulation, demo


class SimulationTests(unittest.TestCase):
    def setUp(self):
        self.sim = Simulation()

    def turn(self, text, speaker='fixture-owner', mic='living-room'):
        token = self.sim.speech(mic=mic)
        self.sim.submit(token, text, speaker=speaker, confidence=.99)
        return self.sim.playback

    def test_wake_duck_and_followup_restore(self):
        self.assertTrue(self.sim.wake('Aničko'))
        self.assertEqual(self.sim.volumes['tv'], .15)
        out = self.turn('rozsviť')
        self.assertTrue(self.sim.lights['obývák'])
        self.sim.advance(5)
        self.assertEqual(self.sim.ctrl.mode, Mode.SPEAKING)
        self.sim.complete(out)
        self.sim.advance(2.9)
        self.assertEqual(self.sim.volumes['tv'], .15)
        self.sim.advance(.1)
        self.assertEqual(self.sim.ctrl.mode, Mode.IDLE)
        self.assertEqual(self.sim.volumes['tv'], .7)

    def test_unknown_introduction_and_followup_cannot_act(self):
        self.sim.wake('Aničko')
        for text in ('rozsviť', 'Jmenuji se Martin', 'rozsviť'):
            out = self.turn(text, speaker='unknown')
            self.assertFalse(self.sim.lights['obývák'])
            self.assertEqual(self.sim.reply, 'Neznám váš hlas, jak se jmenujete?')
            self.sim.complete(out)
        self.assertEqual(self.sim.actions, [])

    def test_each_turn_verifies_voice_and_uses_microphone_room(self):
        self.sim.wake('Aničko')
        self.sim.complete(self.turn('rozsviť', mic='child-room'))
        self.assertTrue(self.sim.lights['dětský pokoj'])
        self.assertFalse(self.sim.lights['obývák'])
        self.turn('zhasni', speaker=None, mic='child-room')
        self.assertTrue(self.sim.lights['dětský pokoj'])

    def test_playback_cannot_wake_or_interrupt(self):
        self.assertFalse(self.sim.wake('Aničko', source='playback'))
        self.sim.wake('Aničko')
        out = self.turn('jak se jmenuješ')
        self.assertIsNone(self.sim.speech(source='echo'))
        self.assertEqual(self.sim.playback, out)

    def test_barge_in_stops_output_and_stale_completion_is_ignored(self):
        self.sim.wake('Aničko')
        old = self.turn('rozsviť')
        token = self.sim.speech()
        self.assertIsNone(self.sim.playback)
        self.sim.complete(old)
        self.assertEqual(self.sim.ctrl.mode, Mode.CAPTURING)
        self.sim.submit(token, 'zhasni', speaker='fixture-owner', confidence=.99)
        new = self.sim.playback
        self.sim.complete(old)
        self.assertEqual(self.sim.playback, new)
        self.assertFalse(self.sim.lights['obývák'])

    def test_stale_transcript_and_unknown_mic_cannot_dispatch(self):
        self.sim.wake('Aničko')
        old = self.sim.speech()
        self.sim.speech()
        self.sim.submit(old, 'rozsviť', speaker='fixture-owner', confidence=.99)
        self.assertEqual(self.sim.actions, [])
        self.assertIsNone(self.sim.speech(mic='unmapped'))

    def test_expired_followup_cannot_restart_without_wake(self):
        self.sim.wake('Aničko')
        self.sim.advance(3)
        self.assertIsNone(self.sim.speech())
        self.assertEqual(self.sim.ctrl.mode, Mode.IDLE)

    def test_output_error_restores_tv_and_closes_session(self):
        self.sim.wake('Aničko')
        self.sim.output_available = False
        with self.assertRaises(OSError):
            self.turn('jak se jmenuješ')
        self.assertEqual(self.sim.ctrl.mode, Mode.IDLE)
        self.assertEqual(self.sim.volumes['tv'], .7)

    def test_hung_output_is_stopped_and_volume_restored(self):
        self.sim.wake('Aničko')
        self.turn('jak se jmenuješ')
        self.sim.advance(30)
        self.assertIsNone(self.sim.playback)
        self.assertEqual(self.sim.ctrl.mode, Mode.IDLE)
        self.assertEqual(self.sim.volumes['tv'], .7)

    def test_stop_failure_blocks_commands_and_next_wake_until_recovered(self):
        self.sim.wake('Aničko')
        self.turn('jak se jmenuješ')
        self.sim.stop_available = False
        self.assertIsNone(self.sim.speech())
        self.assertEqual(self.sim.ctrl.mode, Mode.IDLE)
        self.assertFalse(self.sim.wake('Aničko'))
        self.assertEqual(self.sim.actions, [])
        self.sim.stop_available = True
        self.sim.advance(0)
        self.assertIsNone(self.sim.playback)
        self.assertTrue(self.sim.wake('Aničko'))

    def test_restore_failure_retried_before_next_session(self):
        self.sim.wake('Aničko')
        self.sim.volume_available = False
        self.sim.advance(3)
        self.assertEqual(self.sim.guard.pending, {'tv': .7})
        self.assertFalse(self.sim.wake('Aničko'))
        self.sim.volume_available = True
        self.sim.advance(0)
        self.assertEqual(self.sim.volumes['tv'], .7)
        self.assertTrue(self.sim.wake('Aničko'))

    def test_demo_runs_complete_scenarios_without_production_calls(self):
        report = demo()
        self.assertEqual(len(report), 6)
        self.assertTrue(all(row['passed'] for row in report))
        self.assertTrue(all(row['simulation'] for row in report))


if __name__ == '__main__':
    unittest.main()

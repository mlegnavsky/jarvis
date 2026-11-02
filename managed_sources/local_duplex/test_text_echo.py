"""A generated reply must never return as a fresh user turn."""
import importlib
import unittest


class TextEchoTests(unittest.TestCase):
    def echo(self):return importlib.import_module('text_echo').TextEcho()

    def test_own_question_and_partial_playback_are_rejected(self):
        guard=self.echo()
        guard.remember('Co pro tebe můžu udělat?',started_at=10,duration=3,tail=2)
        for text in ('Co pro tebe můžu udělat?', 'Co pro tebe', 'můžu udělat'):
            self.assertTrue(guard.matches(text,captured_from=11,captured_until=13),text)
        self.assertTrue(guard.matches('Co',captured_from=10.1,captured_until=11))

    def test_captured_timing_not_stt_completion_time_decides(self):
        guard=self.echo();guard.remember('Řekni prosím delší větu.',started_at=10,duration=3,tail=2)
        self.assertTrue(guard.matches('Řekni prosím delší větu',captured_from=13.2,captured_until=14.2))
        self.assertFalse(guard.matches('Řekni prosím delší větu',captured_from=8,captured_until=9))
        self.assertFalse(guard.matches('Řekni prosím delší větu',captured_from=16,captured_until=17))

    def test_human_short_answers_stop_and_new_question_remain_valid(self):
        guard=self.echo();guard.remember('Chceš odpovědět ano, nebo ne?',started_at=10,duration=3,tail=2)
        for text in ('Ano','Ne','Stop','Kolik je v obýváku stupňů?', 'Proč jsi řekla chceš odpovědět ano nebo ne?'):
            self.assertFalse(guard.matches(text,captured_from=11,captured_until=12),text)

    def test_spoken_name_accents_and_punctuation_are_normalized(self):
        guard=self.echo();guard.remember('Tady Jarvis. Jsem připravená.',started_at=10,duration=3,tail=2)
        self.assertTrue(guard.matches('Tady Džárvis, jsem připravená!',captured_from=11,captured_until=12))

    def test_single_word_echo_requires_whole_reply_or_control_word(self):
        guard=self.echo();guard.remember('Ano.',started_at=10,duration=1,tail=2)
        self.assertTrue(guard.matches('Ano',captured_from=10.2,captured_until=11))
        guard.remember('Povel zhasni může ovládat světlo.',started_at=20,duration=3,tail=2)
        self.assertTrue(guard.matches('zhasni',captured_from=21,captured_until=22))
        self.assertFalse(guard.matches('světlo',captured_from=16,captured_until=17))
        self.assertTrue(guard.matches('světlo',captured_from=21,captured_until=22))

    def test_history_is_bounded_and_cancel_tail_can_be_shortened(self):
        guard=self.echo()
        for i in range(10):guard.remember('Zkouška číslo '+str(i),started_at=i*10,duration=8,tail=2)
        self.assertLessEqual(len(guard.records),3)
        guard.stopped(at=91,tail=2)
        self.assertTrue(guard.matches('Zkouška číslo 9',captured_from=91,captured_until=92))
        self.assertFalse(guard.matches('Zkouška číslo 9',captured_from=94,captured_until=95))

    def test_real_reply_after_playback_with_small_preroll_overlap_is_not_echo(self):
        guard=self.echo();guard.remember('Můžeš říct světlo.',started_at=10,duration=3,tail=.4)
        self.assertFalse(guard.matches('světlo',captured_from=12.9,captured_until=14.5))

    def test_small_asr_variants_of_generated_question_are_echo(self):
        guard=self.echo();guard.remember('Chceš abych ti řekla další příběh?',started_at=10,duration=4,tail=2)
        for text in ('Chceš abych ti řekla dlouhý příběh?',
                     'Chceš abych řekla další příběh?',
                     'Chceš abych ti řekla ještě další příběh?'):
            self.assertTrue(guard.matches(text,captured_from=11,captured_until=13),text)

    def test_human_corrections_and_short_response_to_question_are_retained(self):
        guard=self.echo();guard.remember('Chceš abych ti řekla další příběh?',started_at=10,duration=4,tail=2)
        for text in ('Ne, chceš abych ti řekla další příběh?',
                     'Proč chceš abych ti řekla další příběh?',
                     'Chceš abych ti neřekla další příběh?',
                     'Chceš abych ti řekla stop další příběh?',
                     'Chci další příběh','Nechci další příběh','Ano','Ne','Stop',
                     'Zhasni v obýváku'):
            self.assertFalse(guard.matches(text,captured_from=11,captured_until=13),text)

    def test_asr_variant_outside_output_interval_is_human(self):
        guard=self.echo();guard.remember('Co pro tebe můžu udělat?',started_at=10,duration=3,tail=2)
        self.assertTrue(guard.matches('Co pro tebe mohu udělat?',captured_from=11,captured_until=13))
        self.assertFalse(guard.matches('Co pro tebe mohu udělat?',captured_from=16,captured_until=18))

    def test_repeated_delayed_questions_do_not_become_new_turns(self):
        guard=self.echo()
        for i in range(8):
            guard.remember('Chceš slyšet delší příběh číslo '+str(i)+'?',started_at=10*i,duration=3,tail=1.9)
            self.assertTrue(guard.matches('Chceš slyšet dlouhý příběh číslo '+str(i)+'?',
                captured_from=10*i+3.4,captured_until=10*i+4.4))
        self.assertLessEqual(len(guard.records),3)

    def test_guard_exposes_scalar_reason_without_transcript_words(self):
        guard=self.echo();guard.remember('Co pro tebe můžu udělat?',started_at=10,duration=3,tail=2)
        guard.matches('Co pro tebe mohu udělat?',captured_from=11,captured_until=13)
        self.assertEqual(guard.last_facts['decision'],'generated_asr_variant')
        self.assertEqual(guard.last_facts['edit_distance'],1)
        self.assertNotIn('mohu',str(guard.last_facts));self.assertNotIn('muzu',str(guard.last_facts))

    def test_output_diagnostics_are_bounded_and_do_not_save_words(self):
        output=importlib.import_module('ha_io').LocalOutput(lambda:None,None,None,None)
        output.text_echo.remember('Co pro tebe můžu udělat?',started_at=10,duration=3,tail=2)
        for _ in range(40):output.is_own_transcript('Co pro tebe mohu udělat?',bytes(32000),12.)
        facts=output.snapshot()['transcript_guard']
        self.assertEqual(len(facts),32)
        self.assertTrue(all(x['decision']=='generated_asr_variant' for x in facts))
        self.assertNotIn('mohu',str(facts));self.assertNotIn('muzu',str(facts))

    def test_new_negation_position_is_preserved_even_if_word_was_elsewhere(self):
        guard=self.echo();guard.remember('Můžeš říct ano nebo ne a pokračovat dál.',started_at=10,duration=4,tail=2)
        self.assertFalse(guard.matches('Můžeš říct ne ano nebo ne a pokračovat dál.',
            captured_from=11,captured_until=13))

    def test_scalar_reason_uses_overlapping_record_not_newer_unrelated_output(self):
        guard=self.echo()
        guard.remember('Co pro tebe můžu udělat?',started_at=10,duration=3,tail=2)
        guard.remember('Nová odpověď.',started_at=20,duration=2,tail=2)
        self.assertFalse(guard.matches('Kolik je hodin?',captured_from=11,captured_until=13))
        self.assertEqual(guard.last_facts['decision'],'different_words')
        self.assertEqual(guard.last_facts['overlap_ratio'],1.)

    def test_indirect_human_request_changes_action_instead_of_becoming_echo(self):
        for original,candidate in (
            ('Můžeš zapnout světlo v obýváku?','Můžeš vypnout světlo v obýváku?'),
            ('Můžeš zamknout dveře u vchodu?','Můžeš odemknout dveře u vchodu?')):
            guard=self.echo();guard.remember(original,started_at=10,duration=4,tail=2)
            self.assertFalse(guard.matches(candidate,captured_from=11,captured_until=13),candidate)

    def test_dp_prefix_cannot_delete_new_negation_or_repeated_stop(self):
        for original,candidate in (
            ('Stop chci slyšet jiný příběh','Stop stop chci slyšet jiný příběh'),
            ('Já ti mohu povědět další dlouhý příběh teď večer ne',
             'Já ne já ti mohu povědět další dlouhý příběh teď večer ne')):
            guard=self.echo();guard.remember(original,started_at=10,duration=4,tail=2)
            self.assertFalse(guard.matches(candidate,captured_from=11,captured_until=13),candidate)

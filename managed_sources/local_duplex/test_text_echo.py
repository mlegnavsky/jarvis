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

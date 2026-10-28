"""Recognized activation must survive into the command without inventing a verb."""
import unittest
from wake_commands import compose


class CompositionTests(unittest.TestCase):
    def test_empty_suffix_keeps_the_command(self):
        self.assertEqual(compose('zhasni', ''), 'zhasni')

    def test_room_suffix_is_preserved(self):
        self.assertEqual(compose('rozsviť', 'v koupelně'), 'rozsviť v koupelně')

    def test_repeated_verb_is_not_duplicated(self):
        self.assertEqual(compose('ROZSVIŤ', 'Rozsviť v chodbičce.'), 'Rozsviť v chodbičce.')

    def test_conflicting_verb_is_rejected(self):
        with self.assertRaises(ValueError):
            compose('zhasni', 'rozsviť v koupelně')

    def test_locks_are_commands_not_authentication(self):
        self.assertEqual(compose('odemkni', 'vchodové dveře'), 'odemkni vchodové dveře')
        self.assertEqual(compose('zamkni', ''), 'zamkni')

    def test_ordinary_wake_word_does_not_invent_an_action(self):
        self.assertIsNone(compose('Hey Jarvis', 'v koupelně'))

    def test_non_string_suffix_is_not_stringified_into_a_command(self):
        with self.assertRaises(ValueError):
            compose('zhasni', None)

    def test_multiple_actions_are_rejected(self):
        with self.assertRaises(ValueError):
            compose('zhasni', 'a odemkni dveře')

    def test_command_word_in_a_room_name_is_not_treated_as_a_verb(self):
        self.assertEqual(compose('zhasni', 'v zhasnině'), 'zhasni v zhasnině')

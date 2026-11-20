import unittest
from types import SimpleNamespace as NS
from direct_wake import media_active,COMMANDS

class TelevisionInputTests(unittest.TestCase):
 def test_missing_primary_media_state_cannot_enable_bare_commands(self):
  self.assertTrue(media_active(NS(states=NS(get=lambda entity:None))))
  self.assertTrue(media_active(NS(states=NS(get=lambda entity:None if entity=='media_player.obyvaci_pokoj_obyvaci_pokoj' else NS(state='off')))))

 def test_new_light_nouns_are_not_acoustic_activation_words(self):
  self.assertNotIn('světlo',COMMANDS);self.assertNotIn('světýlko',COMMANDS)

import unittest
from dialogue import should_continue, is_stop, recent_session
class DialogueTests(unittest.TestCase):
 def test_statement_keeps_conversation_open(self):
  self.assertTrue(should_continue('Pověz mi něco o zahradě','Na podzim můžeš sázet cibuloviny.',2,10))
 def test_czech_stop_ends_without_question_heuristic(self):
  for text in ['Děkuji, konec.','Konec','Už končíme','To je všechno, děkuji.']:
   self.assertTrue(is_stop(text));self.assertFalse(should_continue(text,'Dobře.',2,10))
 def test_mentions_of_end_are_not_stop_commands(self):
  for text in ['Jaký má ten film konec?','Nechci končit','Řekni mi příběh na dobrou noc']:
   self.assertFalse(is_stop(text))
 def test_no_text_and_echo_stop_loop(self):
  self.assertFalse(should_continue('.','Odpověď',2,10))
  self.assertFalse(should_continue('Něco ti vysvětlím.','Něco ti vysvětlím.',2,10))
 def test_boundaries(self):
  self.assertFalse(should_continue('Pokračuj','Ano',32,10))
  self.assertFalse(should_continue('Pokračuj','Ano',2,1200))
 def test_only_same_device_recent_session_is_reused(self):
  self.assertEqual(recent_session({'dev':('c',100)},'dev',200),'c')
  self.assertIsNone(recent_session({'dev':('c',100)},'other',200))
  self.assertIsNone(recent_session({'dev':('c',100)},None,200))
  self.assertIsNone(recent_session({'dev':('c',100)},'dev',1001))

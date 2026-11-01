import unittest
from authorization import VoiceGate, command

class GateTests(unittest.TestCase):
 def test_bound_target_cannot_be_reused_for_another_room(self):
  gate=VoiceGate();token=gate.issue('mic','Zhasni','id',True)
  self.assertTrue(gate.bind(token,'mic','Zhasni',('light','turn_off'),(('light.living',),'living')))
  self.assertFalse(gate.consume(token,'mic','Zhasni',('light','turn_off'),(('light.bedroom',),'bedroom')))
 def test_lock_binding_cannot_name_another_lock(self):
  gate=VoiceGate();token=gate.issue('mic','Odemkni','id',True)
  self.assertFalse(gate.bind(token,'mic','Odemkni',('lock','unlock'),(('lock.other',),'vstup')))
 def setUp(self):
  self.now=10;self.gate=VoiceGate(clock=lambda:self.now)
 def test_command_targets_are_explicit(self):
  self.assertEqual(command('Odemkni.'),('lock','unlock'))
  self.assertEqual(command('Rozsviť v obýváku'),('light','turn_on'))
  self.assertIsNone(command('odemkni a vypni alarm'))
 def test_unknown_voice_cannot_issue_token(self):
  self.assertIsNone(self.gate.issue('mic','Zhasni',None,False))
 def test_grant_is_one_use_exact_device_text_and_action(self):
  token=self.gate.issue('mic','Zhasni','voice-id',True)
  self.assertFalse(self.gate.consume(token,'other','Zhasni',('light','turn_off')))
  token=self.gate.issue('mic','Zhasni','voice-id',True)
  self.assertFalse(self.gate.consume(token,'mic','Zhasni',('lock','unlock')))
  token=self.gate.issue('mic','Zhasni','voice-id',True)
  self.assertTrue(self.gate.consume(token,'mic','Zhasni',('light','turn_off')))
  self.assertFalse(self.gate.consume(token,'mic','Zhasni',('light','turn_off')))
 def test_expired_grant_is_not_accepted(self):
  token=self.gate.issue('mic','Zhasni','voice-id',True);self.now+=16
  self.assertFalse(self.gate.consume(token,'mic','Zhasni',('light','turn_off')))
 def test_short_pending_action_needs_explicit_matching_confirmation(self):
  self.gate.pending('mic','Odemkni')
  self.assertIsNone(self.gate.confirm('mic','Aničko dnes je hezky',True))
  self.assertIsNone(self.gate.confirm('mic','Potvrzuji zamknutí hlavního vchodu',True))
  self.assertEqual(self.gate.confirm('mic','Aničko potvrzuji odemknutí hlavního vchodu',True),'odemkni')
 def test_confirmation_expires_and_unknown_voice_clears_it(self):
  self.gate.pending('mic','Odemkni');self.now+=61
  self.assertIsNone(self.gate.confirm('mic','Potvrzuji odemknutí hlavního vchodu',True))
  self.gate.pending('mic','Odemkni')
  self.assertIsNone(self.gate.confirm('mic','Potvrzuji odemknutí hlavního vchodu',False))
  self.assertIsNone(self.gate.confirm('mic','Potvrzuji odemknutí hlavního vchodu',True))

 def test_confirmation_window_includes_spoken_prompt_and_model_latency(self):
  self.gate.pending('mic','Zhasni');self.now+=25
  self.assertEqual(self.gate.confirm('mic','Potvrzuji zhasnutí světel v této místnosti',True),'zhasni')

class PoliteCommandTests(unittest.TestCase):
 def test_observed_polite_light_commands_are_local(self):
  from authorization import canonical_command
  for text in ('Aničko, prosím tě, rozsviť mě světla v obýváku, ať tady lépe vidím.', 'Prosím tě, rozsviť mi světlo v obýváku, ať tady lépe vidím.', 'Rozsviť v obýváku, prosím.'):
   self.assertEqual(command(text),('light','turn_on'))
   self.assertEqual(canonical_command(text),'rozsvit svetla v obyvaku' if 'světla' in text else 'rozsvit svetlo v obyvaku' if 'světlo' in text else 'rozsvit v obyvaku')
 def test_negation_multi_action_and_quotes_are_not_canonicalized(self):
  for text in ('Prosím nerozsviť v obýváku','Řekl jsem rozsviť','Prosím rozsviť a odemkni','Rozsviť v obýváku a pak zhasni','Rozsviť v obýváku pokud tam někdo je'):
   self.assertIsNone(command(text),text)

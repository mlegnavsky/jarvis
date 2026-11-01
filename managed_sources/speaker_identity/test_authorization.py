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
  self.gate.pending('mic','Odemkni');self.now+=11
  self.assertIsNone(self.gate.confirm('mic','Potvrzuji odemknutí hlavního vchodu',True))
  self.gate.pending('mic','Odemkni')
  self.assertIsNone(self.gate.confirm('mic','Potvrzuji odemknutí hlavního vchodu',False))
  self.assertIsNone(self.gate.confirm('mic','Potvrzuji odemknutí hlavního vchodu',True))

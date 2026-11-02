import unittest
from managed_sources.voice_common import parse_command, is_noise_transcript

class ContractTests(unittest.TestCase):
 def test_finite_light_nouns_and_ordinary_variants_are_exact_commands(self):
  for text,service,room in [('Světlo','turn_on',None),('Světla prosím','turn_on',None),
      ('Prosím světýlko','turn_on',None),('Rozsveť','turn_on',None),('Rosviť v obýváku','turn_on','obyvaku'),
      ('Udělej světlo','turn_on',None),('Světlo zapnout','turn_on',None),('Světlo vypnout','turn_off',None),
      ('Světlo v dětském pokojíku','turn_on','detskem pokojiku'),('Zhasni světýlko','turn_off',None)]:
   parsed=parse_command(text);self.assertIsNotNone(parsed,text)
   self.assertEqual((parsed.domain,parsed.service,parsed.room),('light',service,room),text)
  self.assertEqual(parse_command('Světla všude').scope,'all')

 def test_incidental_or_negated_light_nouns_are_not_commands(self):
  for text in ('Tady je světlo','Žádné světlo','Světlo ne','Nedělej světlo','Co znamená světlo?',
      'Říkala světlo','Světlo když přijdu','Světlo v obýváku a zhasni v ložnici','„Světlo“',
      'Jarvisi, nerozsveť','Světlo vypnout a televizi zapnout'):
   self.assertIsNone(parse_command(text),text)
 def test_shared_semantics_cover_all_house_and_explicit_light_synonyms(self):
  for text,canonical in [('Zhasni všude.','zhasni vsude'),('Jarvisi, prosím zhasni všechna světla.','zhasni vsude'),('Zapni světlo v obýváku.','rozsvit svetlo v obyvaku'),('Hej Jarvis, vypni světla v dětském pokoji.','zhasni svetla v detskem pokoji')]:
   p=parse_command(text);self.assertIsNotNone(p,text);self.assertEqual(p.canonical,canonical)
  self.assertEqual(parse_command('Zhasni všude').scope,'all')
 def test_noncommands_never_get_actions(self):
  for text in ('Řekl jsem zhasni všude','Nezhasni','Zhasni v obýváku a pak odemkni','Rozsviť v obýváku pokud tam někdo je','Zapni televizi','Co znamená zhasni?','Zhasni, rozsviť'):
   self.assertIsNone(parse_command(text),text)
 def test_prompt_scaffolding_is_not_speech(self):
  for text in ('context: ###','### context: ###','context: ###\nThe following conversation is a smart home user talking to Home Assistant.\n###','[blank_audio]'):
   self.assertTrue(is_noise_transcript(text),text)
  self.assertFalse(is_noise_transcript('Co znamená slovo context?'))
 def test_quoted_examples_never_become_commands(self):
  for text in ('"Zhasni všude"','„Zhasni všude“',"'Zhasni všude'",'Jarvis, „zhasni“ v obýváku',
      '‚světlo‘','‘světlo’','‹světlo›','Jarvisi, ‚světlo‘', '‚zhasni‘'):
   self.assertIsNone(parse_command(text),text)

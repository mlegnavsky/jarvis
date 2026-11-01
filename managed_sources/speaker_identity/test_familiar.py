import tempfile
from pathlib import Path
import unittest
from policy import VoiceProfiles
from familiar import FamiliarVoices

class FamiliarTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.now=1000
  self.profiles=VoiceProfiles(Path(self.tmp.name)/'profiles.sqlite',clock=lambda:self.now)
  self.f=FamiliarVoices(self.profiles)
 def tearDown(self):self.tmp.cleanup()
 def item(self,n,vector=None,playback=False):
  v=vector or [1.,0.]
  return {'text':'Různá věta '+str(n),'voiced':5,'utterance':str(n),'playback':playback,'result':{'status':'ok','model':'campplus-aa3cfc16-v1','vector':v,'windows':[v,v],'quality':{'status':'ok','rms':.1,'clipped_fraction':0}}}
 def collect(self):
  result=None
  for n in range(6):result=self.f.observe(self.item(n),'session'+str(n//2))
  return result
 def test_independent_sessions_required_and_name_survives_restart_without_authorization(self):
  ready=self.collect();self.assertTrue(ready['ready'])
  question=self.f.dialog('mic','Jak se máš?',ready,allow_ask=True)
  self.assertTrue(question['ask_name'])
  saved=self.f.dialog('mic','Jmenuji se Šarlota',ready,allow_ask=True)
  self.assertIn('Šarlota',saved['local_reply'])
  other=FamiliarVoices(self.profiles);match=other.observe(self.item(7),'new')
  self.assertEqual(match['name'],'Šarlota')
  self.assertEqual(self.profiles.count(),0)
  self.assertEqual(self.profiles.authorization_summary()['authorized_profiles'],0)
 def test_duplicate_playback_and_short_samples_never_mature(self):
  for n in range(10):self.f.observe(self.item(1),'session'+str(n))
  self.assertEqual(self.f.summary()['samples'],1)
  self.f.observe(self.item(2,playback=True),'other')
  short=self.item(3);short['voiced']=1
  self.f.observe(short,'other')
  self.assertEqual(self.f.summary()['samples'],1)
 def test_one_conversation_cannot_trigger_name_question(self):
  for n in range(10):r=self.f.observe(self.item(n),'same')
  self.assertFalse(r['ready'])
  self.assertEqual(self.f.dialog('mic','Ahoj',r,allow_ask=True),{})
 def test_other_voice_and_commands_cannot_take_pending_name(self):
  ready=self.collect();self.f.dialog('mic','Ahoj',ready,allow_ask=True)
  foreign=self.f.observe(self.item(9,[0.,1.]),'other')
  self.assertNotIn('local_reply',self.f.dialog('mic','Jmenuji se Petr',foreign,allow_ask=True))
  self.assertEqual(self.f.dialog('mic','Rozsviť',ready,allow_ask=False),{})
 def test_no_windows_and_inconsistent_windows_are_rejected(self):
  a=self.item(1);a['result']['windows']=[]
  self.assertEqual(self.f.observe(a,'c'),{})
  a=self.item(2);a['result']['windows'][1]=[0.,1.]
  self.assertEqual(self.f.observe(a,'c'),{})
 def test_expiry_and_name_deletion(self):
  r=self.collect();self.f.dialog('mic','Ahoj',r,allow_ask=True)
  self.f.dialog('mic','Jmenuji se Šarlota',r,allow_ask=True)
  self.f.forget('Šarlota');self.assertEqual(self.f.summary()['clusters'],0)
  self.collect();self.now+=31*86400
  self.assertEqual(self.f.summary()['clusters'],0)

 def test_repeated_sentence_with_different_recordings_does_not_mature(self):
  for n in range(8):
   item=self.item(n);item['text']='Stejná věta znovu.'
   self.f.observe(item,'session'+str(n))
  self.assertEqual(self.f.summary()['samples'],1)

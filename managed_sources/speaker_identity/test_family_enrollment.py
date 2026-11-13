import math,tempfile,unittest,json
from pathlib import Path
from policy import VoiceProfiles
from family_enrollment import FamilyEnrollment

def sample(n,a=.1,seconds=7):
 return {'utterance':'audio-'+str(n),'voiced':seconds,'playback':False,
  'result':{'status':'ok','model':'campplus-aa3cfc16-v1','vector':[0,math.cos(a),math.sin(a)],
   'windows':[[0,math.cos(a-.02),math.sin(a-.02)],[0,math.cos(a+.02),math.sin(a+.02)]],
   'quality':{'status':'ok','rms':.05,'clipped_fraction':0}}}
class FamilyTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.p=VoiceProfiles(Path(self.tmp.name)/'p.sqlite')
  self.p.begin('mic','Martin')
  for _ in range(3):self.p.sample('mic',[1,0,0],4)
  self.p.bootstrap_authorization('Martin');self.owner=self.p.identify([1,0,0])['memory_id']
  self.f=FamilyEnrollment(self.p)
 def tearDown(self):self.tmp.cleanup()
 def begin(self):
  self.f.start('mic',self.owner)
  self.f.collect('mic','Jmenuji se Šarlota',{})
  self.f.collect('mic','Ano souhlasím',{})
 def test_progress_validates_new_answers_and_commits_unprivileged_profile(self):
  self.begin();progress=[]
  for i in range(8):
   r=self.f.collect('mic','Moje různá celá odpověď '+str(i),sample(i,.05*i))
   self.assertFalse(r['authorized']);self.assertNotIn('control_token',r);progress.append(r['progress_percent'])
  self.assertEqual(r['status'],'family_enrolled');self.assertEqual(progress[-1],100)
  self.assertEqual(progress,sorted(progress));self.assertIn('kontrol',r['local_reply'])
  who=self.p.identify([0,math.cos(.22),math.sin(.22)])
  self.assertEqual(who['profile'],'sarlota');self.assertFalse(self.p.is_authorized(who['memory_id']))
  self.assertEqual(self.p.count(),2);self.assertTrue(self.p.is_authorized(self.owner))
 def test_restart_keeps_progress_and_duplicate_cannot_advance(self):
  self.begin();self.f.collect('mic','První různá odpověď',sample(1))
  self.f=FamilyEnrollment(self.p);self.assertEqual(self.f.summary()['training_samples'],1)
  self.f.collect('mic','První různá odpověď',sample(1));self.assertEqual(self.f.summary()['training_samples'],1)
 def test_no_consent_no_authorized_owner_no_profile_overwrite(self):
  with self.assertRaises(ValueError):self.f.start('mic','missing')
  self.f.start('mic',self.owner);self.f.collect('mic','Jsem Martin',{})
  self.assertEqual(self.p.count(),1);self.assertEqual(self.f.summary()['stage'],'name')
  self.f.collect('mic','Jsem Šarlota',{});self.f.collect('mic','Ne nesouhlasím',{})
  self.assertEqual(self.f.summary()['status'],'idle');self.assertEqual(self.p.count(),1)
 def test_failed_validation_never_reports_complete_or_grants_control(self):
  self.begin()
  for i in range(5):self.f.collect('mic','Tréninková odpověď '+str(i),sample(i,.04*i))
  bad=sample(9);bad['result']['vector']=[1,0,0];bad['result']['windows']=[[1,0,0],[1,0,0]]
  r=self.f.collect('mic','Rozsviť světlo v obýváku prosím',bad)
  self.assertLess(r['progress_percent'],100);self.assertFalse(r['authorized']);self.assertEqual(self.p.count(),1)
 def test_cancel_and_owner_forget_erase_pending_vectors(self):
  self.begin();self.f.collect('mic','První moje odpověď',sample(1));self.f.collect('mic','Zruš zaučení',{})
  self.assertEqual(self.f.summary()['status'],'idle')
  self.begin();self.p.forget('Martin');self.assertEqual(self.f.summary()['status'],'idle')
 def test_admin_approval_is_revision_bound_lights_only_and_revocable(self):
  self.begin()
  for i in range(8):self.f.collect('mic','Odpověď '+str(i),sample(i,.05*i))
  revision=self.f.summary()['validated_profile_revision'];path=Path(self.tmp.name)/'family-control.json'
  target=self.p.identify([0,1,0])['memory_id']
  def request(action,key,expected=revision):
   path.write_text(json.dumps({'request_id':key,'action':action,'profile':'Šarlota','expected_revision':expected,'issued_at':self.p.clock()}))
   return self.f.process_control(path)
  self.assertEqual(request('authorize_lights','a'*32,'f'*64)['status'],'rejected')
  self.assertFalse(self.p.is_authorized(target))
  self.assertEqual(request('authorize_lights','b'*32)['status'],'authorized_lights')
  self.assertTrue(self.p.can_control(target,'light'));self.assertFalse(self.p.can_control(target,'lock'))
  with self.assertRaises(ValueError):self.f.start('other',target)
  self.assertTrue(self.p.can_control(self.owner,'lock'))
  self.assertEqual(request('revoke_lights','c'*32)['status'],'revoked_lights')
  self.assertFalse(self.p.is_authorized(target));self.assertEqual(self.p.count(),2)
 def test_forget_erases_copied_known_speaker_exclusion_references(self):
  self.begin()
  for i in range(8):self.f.collect('mic','Odpověď '+str(i),sample(i,.05*i))
  child=self.p.identify([0,1,0])['memory_id'];self.p.forget('Martin')
  with self.p._db() as db:bank=json.loads(db.execute('SELECT samples FROM voices WHERE voice_id=?',(child,)).fetchone()[0])
  self.assertEqual(bank['negative'],[])
  self.assertEqual(self.p.identify([0,1,0])['status'],'unknown')
 def test_enrollment_requires_actual_inter_profile_separation(self):
  references=[[.8*math.cos(a),.6,.8*math.sin(a)] for a in (0,2*math.pi/3,4*math.pi/3)]
  with self.p._db() as db:db.execute('UPDATE voices SET samples=?',(json.dumps(references),))
  self.begin()
  for i in range(8):r=self.f.collect('mic','Různá odpověď '+str(i),sample(i,.005*i))
  self.assertNotEqual(r['status'],'family_enrolled');self.assertLess(r['progress_percent'],100)
  self.assertEqual(self.p.count(),1)
 def test_admin_approval_rechecks_current_rival_models(self):
  self.begin()
  for i in range(8):self.f.collect('mic','Různá odpověď '+str(i),sample(i,.05*i))
  revision=self.f.summary()['validated_profile_revision']
  with self.p._db() as db:db.execute('UPDATE voices SET samples=? WHERE voice_id=?',(json.dumps([[0,1,0]]*3),self.owner))
  path=Path(self.tmp.name)/'control.json';path.write_text(json.dumps({'request_id':'e'*32,'action':'authorize_lights','profile':'Šarlota','expected_revision':revision,'issued_at':self.p.clock()}))
  self.assertEqual(self.f.process_control(path)['status'],'rejected')
 def test_training_command_does_not_escape_as_device_action(self):
  self.begin();r=self.f.collect('mic','Rozsviť v obýváku',sample(1))
  self.assertTrue(r['calibration']);self.assertFalse(r['authorized']);self.assertNotIn('effective_text',r)

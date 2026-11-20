import math,json,tempfile,unittest
from pathlib import Path
from policy import VoiceProfiles,profile_score

def vec(a):return [math.cos(a),math.sin(a)]
class CohortTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.p=VoiceProfiles(Path(self.tmp.name)/'p.sqlite')
  self.p.begin('mic','Martin')
  for a in (0,.05,.1):self.p.sample('mic',vec(a),4)
  self.p.bootstrap_authorization('Martin')
  self.bank={'positive':[vec(a) for a in (0,.05,.1)],'negative':[vec(a) for a in (2.7,2.72,2.74,2.76,2.78)]}
 def tearDown(self):self.tmp.cleanup()
 def install(self,bank=None):
  with self.p._db() as db:
   identity=db.execute('SELECT voice_id FROM voices').fetchone()[0]
   db.execute('UPDATE voices SET samples=?',(json.dumps(self.bank if bank is None else bank),))
   db.execute('INSERT OR REPLACE INTO voice_matching_policies VALUES (?,?)',(identity,'cohort_margin_v1'))
 def test_noisy_positive_needs_support_and_exclusion_margin(self):
  self.assertEqual(self.p.identify(vec(1.05))['status'],'unknown')
  self.install();known=self.p.identify(vec(1.05))
  self.assertEqual(known['status'],'recognized');self.assertLess(known['score'],.65)
  self.assertEqual(self.p.identify(vec(2.74))['status'],'unknown')
 def test_short_window_support_cannot_independently_authorize_whole_turn(self):
  self.install();self.assertEqual(self.p.identify(vec(1.095))['status'],'unknown')
  self.assertEqual(self.p.identify(vec(1.095),window=True)['status'],'recognized')
 def test_one_close_reference_and_cohort_overlap_reject(self):
  self.install({**self.bank,'positive':[vec(0),vec(2)]})
  self.assertEqual(self.p.identify(vec(0))['status'],'unknown')
  self.install({**self.bank,'negative':[vec(.1),vec(.12),vec(.14)]})
  self.assertEqual(self.p.identify(vec(.05))['status'],'unknown')
 def test_missing_or_malformed_cohort_fails_closed(self):
  for bank in ({'positive':self.bank['positive'],'negative':[]},self.bank['positive'],{'positive':self.bank['positive'],'negative':[[1,0,0]]*3}):
   self.install(bank);self.assertEqual(self.p.identify(vec(0))['status'],'unknown')
 def test_numeric_diagnostics_expose_no_templates_or_identity(self):
  self.install();e=self.p.match_diagnostics(vec(1.05))
  self.assertGreaterEqual(e['exclusion_margin'],.2)
  for private in ('positive','negative','vector','Martin','voice_id'):self.assertNotIn(private,str(e))

class CohortControlTests(unittest.IsolatedAsyncioTestCase):
 async def test_noise_tolerant_identity_never_weakens_lock_or_delete(self):
  import asyncio
  from types import SimpleNamespace as NS
  from coordinator import Coordinator
  async def execute(fn,*args):return fn(*args)
  async def infer(pcm):return {'status':'ok','model':'campplus-aa3cfc16-v1','vector':vec(1.05),'windows':[vec(1.095),vec(1.0)],'quality':{'status':'ok','rms':.1,'clipped_fraction':0}}
  with tempfile.TemporaryDirectory() as folder:
   c=Coordinator(NS(async_add_executor_job=execute),Path(folder)/'p.sqlite',infer,enforce=True)
   c.profiles.begin('mic','Martin')
   for a in (0,.05,.1):c.profiles.sample('mic',vec(a),4)
   c.profiles.bootstrap_authorization('Martin')
   with c.profiles._db() as db:
    identity=db.execute('SELECT voice_id FROM voices').fetchone()[0]
    bank={'positive':[vec(a) for a in (0,.05,.1)],'negative':[vec(a) for a in (2.7,2.72,2.74)]}
    db.execute('UPDATE voices SET samples=?',(json.dumps(bank),))
    db.execute('INSERT INTO voice_matching_policies VALUES (?,?)',(identity,'cohort_margin_v1'))
   for text,allowed in [('Rozsviť v obýváku',True),('Zamkni hlavní vchod',False),('Smaž můj hlasový profil',False)]:
    await c.complete('mic',bytes(256000),8,text)
    result=await c.turn(NS(text=text,device_id='mic'),'conversation')
    self.assertEqual(result.get('authorized',False),allowed)
    if not allowed:self.assertNotIn('control_token',result)
   self.assertEqual(c.profiles.count(),1)

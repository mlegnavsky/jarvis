import unittest
from datetime import datetime
from zoneinfo import ZoneInfo
try:from autonomous_verification import candidate,finish
except ImportError:candidate=finish=None

class AutonomousVerificationTests(unittest.TestCase):
 def setUp(self):
  self.now=datetime(2026,11,6,10,1,tzinfo=ZoneInfo('Europe/Prague')).timestamp()
  self.settings={'automatic':True,'inhibited':False,'bias_enabled':True,'bias_verified':True,'battery_verified':False}
  self.state={'ready':True,'healthy':True,'active_kind':'bias','soc':65,'pv_w':1200,'capacity_kwh':23.552,'net_price':5,'pending_stop':False,'charging':False,'pv_low_seconds':180}
  q=self.now//900*900;self.quotes=[{'start':q+i*900,'end':q+(i+1)*900,'net':5} for i in range(4)]
 def choose(self,**changes):
  self.assertIsNotNone(candidate)
  return candidate(self.settings,{**self.state,**changes},self.quotes,self.now)
 def test_low_pv_fresh_price_reserve_and_preparation_budget_admit_only_bounded_battery_test(self):
  c=self.choose();self.assertEqual(c['kind'],'battery');self.assertTrue(c['due'])
  self.assertEqual((c['power_w'],c['minutes'],c['minimum_soc']),(2000,5,60))
 def test_missing_or_unsafe_conditions_wait_without_changing_settings(self):
  for changes in ({'pv_low_seconds':20},{'pv_w':1800},{'pv_w':None},{'soc':62},{'soc':None},{'healthy':False},{'capacity_kwh':None},{'capacity_kwh':1},{'net_price':-1},{'ready':False},{'active_kind':'pv'},{'charging':True},{'pending_stop':True}):
   with self.subTest(changes=changes):self.assertFalse(self.choose(**changes)['due'])
  self.assertTrue(self.settings['automatic'])
 def test_new_bias_is_verified_first_and_known_negative_price_only_admits_tiny_probe(self):
  self.settings['bias_verified']=False
  c=self.choose(active_kind=None,net_price=-1)
  self.assertTrue(c['due']);self.assertEqual((c['kind'],c['power_w'],c['minutes'],c['minimum_soc']),('bias',2,3,30))
 def test_prepare_margin_unique_positive_coverage_retry_delay_and_attempt_cap(self):
  self.now+=180 #10:04: next safe native start10:05 leaves only60s
  self.assertFalse(self.choose()['due'])
  self.now-=180
  self.quotes.append(dict(self.quotes[0]));self.assertFalse(self.choose()['due']);self.quotes.pop()
  self.settings['auto_verification']={'day':'2026-11-06','attempts':2};self.assertFalse(self.choose()['due'])
  self.settings['auto_verification']={'day':'2026-11-06','attempts':1,'not_before':self.now+60};self.assertFalse(self.choose()['due'])
 def test_accepted_autonomous_proof_restores_request_but_manual_or_failed_proof_does_not(self):
  self.assertIsNotNone(finish)
  s={**self.settings,'automatic':False,'verification_resume_auto':True,'auto_verification':{'kind':'battery'}}
  p={'reason':'deadline','observed':True,'stop_verified':True,'native_expiry_observed':True,'conflicts':{}}
  r=finish(s,p,True,self.now);self.assertTrue(r['automatic']);self.assertFalse(r['inhibited']);self.assertFalse(r['verification_resume_auto'])
  r=finish(s,{**p,'native_expiry_observed':False},False,self.now);self.assertFalse(r['automatic']);self.assertTrue(r['inhibited'])
  r=finish({**s,'verification_resume_auto':False},p,True,self.now);self.assertFalse(r['automatic'])
 def test_inconclusive_pv_only_or_recovered_interruption_resumes_small_mode_with_bounded_cooldown(self):
  self.assertIsNotNone(finish)
  s={**self.settings,'automatic':False,'verification_resume_auto':True,'auto_verification':{'kind':'battery','day':'2026-11-06','attempts':1}}
  for reason in ('deadline','recovery','price','reserve'):
   r=finish(s,{'reason':reason,'observed':False,'stop_verified':True,'conflicts':{}},False,self.now)
   self.assertTrue(r['automatic']);self.assertFalse(r['inhibited']);self.assertGreaterEqual(r['auto_verification']['not_before'],self.now+1800)
  r=finish(s,{'reason':'manual','observed':False,'stop_verified':True,'conflicts':{}},False,self.now)
  self.assertFalse(r['automatic'])

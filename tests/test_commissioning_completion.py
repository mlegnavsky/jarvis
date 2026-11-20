import unittest
from datetime import datetime
from zoneinfo import ZoneInfo
try:from commissioning_completion import finish
except ImportError:finish=None

class AutonomousVerificationTests(unittest.TestCase):
 def setUp(self):
  self.now=datetime(2026,11,6,10,1,tzinfo=ZoneInfo('Europe/Prague')).timestamp()
  self.settings={'automatic':True,'inhibited':False,'bias_enabled':True,'bias_verified':True,'battery_verified':False}
  self.state={'ready':True,'healthy':True,'active_kind':'bias','soc':65,'pv_w':1200,'capacity_kwh':23.552,'net_price':5,'pending_stop':False,'charging':False,'pv_low_seconds':180}
  q=self.now//900*900;self.quotes=[{'start':q+i*900,'end':q+(i+1)*900,'net':5} for i in range(4)]
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

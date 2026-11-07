import unittest
from sales import after_stop
class BiasAcceptanceTests(unittest.TestCase):
 def test_only_bounded_measured_complete_probe_promotes_bias(self):
  proof={'id':'bias','mode':'bias','purpose':'bias_probe','reason':'deadline','power_w':2,'minimum_soc':30,'observed':True,'sustained':True,'stop_verified':True,'conflicts':{}}
  self.assertTrue(after_stop({'automatic':False},proof).get('bias_verified'))
  for key,value in [('power_w',3),('minimum_soc',20),('observed',False),('sustained',False),('stop_verified',False),('conflicts',{'cap':{}}),('reason','manual')]:
   with self.subTest(key=key):self.assertFalse(after_stop({'automatic':False},{**proof,key:value}).get('bias_verified',False))

 def test_unconfirmed_repeat_probe_revokes_old_bias_acceptance(self):
  proof={'id':'bad','mode':'bias','purpose':'bias_probe','reason':'deadline','power_w':2,'minimum_soc':30,'observed':False,'sustained':False,'stop_verified':True,'conflicts':{}}
  result=after_stop({'bias_verified':True,'automatic':True},proof)
  self.assertFalse(result['bias_verified']);self.assertFalse(result['automatic']);self.assertTrue(result['inhibited'])

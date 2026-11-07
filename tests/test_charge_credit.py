import unittest,sys
sys.path.insert(0,'managed_sources/spot_control')
from charge_credit import charge_limit
class ChargeCredit(unittest.TestCase):
 def test_fresh_native_and_bms_limits_bound_credit(self):
  self.assertEqual(charge_limit({108:175,212:100,218:200},100,110,52,25),5.2)
 def test_unknown_stale_zero_or_invalid_blocks_future_charge(self):
  for regs,at,now,v,t in [({},100,110,52,25),({108:175,212:0,218:200},100,110,52,25),({108:175,212:100,218:200},100,200,52,25),({108:175,212:100,218:200},100,110,None,25),({108:175,212:100,218:200},100,110,52,60)]:
   self.assertEqual(charge_limit(regs,at,now,v,t),0)

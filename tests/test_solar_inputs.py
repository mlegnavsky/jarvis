import unittest
from solar_inputs import capacity_basis, house_power, cycle_acceptance


class SolarInputsTests(unittest.TestCase):
 def test_configured_capacity_is_not_a_physical_capacity_claim(self):
  x=capacity_basis(460,63,23.3)
  self.assertEqual(x['capacity_kwh'],23.552)
  self.assertEqual(x['source'],'configured_ah_at_nominal_51_2v')
  self.assertFalse(x['physical_verified'])
  self.assertAlmostEqual(x['above_sale_reserve_kwh'],.70656)
  self.assertEqual(capacity_basis(920,63)['capacity_kwh'],47.104)
 def test_bad_capacity_or_soc_never_creates_available_energy(self):
  for value in (None,'unknown',0,-1,True,float('nan'),2001):
   self.assertIsNone(capacity_basis(value,70)['capacity_kwh'])
  self.assertIsNone(capacity_basis(460,None)['remaining_kwh'])
  self.assertEqual(capacity_basis(460,59)['above_sale_reserve_kwh'],0)
 def test_canonical_house_power_wins_and_export_mode_never_uses_native_zero(self):
  self.assertEqual(house_power(620,0,'Export First'),620)
  self.assertIsNone(house_power(None,0,'Export First'))
  self.assertEqual(house_power(None,450,'Zero Export To CT'),450)
  self.assertIsNone(house_power(-20,0,'Export First'))
 def test_full_cycle_requires_real_export_native_expiry_and_full_restore(self):
  proof={'id':'sale1','reason':'deadline','phase':'complete','observed':True,
         'native_expiry_observed':True,'stop_verified':True,'conflicts':{}}
  self.assertTrue(cycle_acceptance(proof)['verified'])
  for change in ({'observed':False},{'native_expiry_observed':False},{'stop_verified':False},
                 {'reason':'manual'},{'conflicts':{'146':{}}}):
   self.assertFalse(cycle_acceptance({**proof,**change})['verified'])

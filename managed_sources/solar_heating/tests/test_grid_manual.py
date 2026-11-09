import unittest
from engine import Controller

class GridManualTests(unittest.TestCase):
 def evaluate(self,c,**kw):
  v=dict(temp=20,pv=0,soc=30,discharge=0,load=400,child=False,living=False,grid_ready=True)
  v.update(kw);return c.evaluate(1000,**v)
 def test_grid_manual_below_soc_limit_and_above_standard_temperature(self):
  c=Controller();c.configure({'temp_on':21,'temp_off':22});c.request_grid('child',900)
  self.assertTrue(self.evaluate(c,temp=23.9)['child']['on'])
  self.assertEqual(self.evaluate(c)['child']['reason'],'Ručně · Ze sítě · do 24 °C')
 def test_exact24_clears_override_and_returns_standard(self):
  c=Controller();c.request_grid('child',900)
  self.assertFalse(self.evaluate(c,temp=24,child=True)['child']['on'])
  self.assertFalse(c.grid_manual['child']);self.assertEqual(c.manual_off_until['child'],0)
 def test_user_off_clears_exception_and_retains_off_lock(self):
  c=Controller();c.request_grid('child',900);c.external('child',False,950)
  self.assertFalse(c.grid_manual['child']);self.assertFalse(self.evaluate(c)['child']['on'])
 def test_loss_of_grid_or_temperature_clears_exception(self):
  for kw in ({'grid_ready':False},{'temp':None}):
   c=Controller();c.request_grid('child',900)
   self.assertFalse(self.evaluate(c,child=True,**kw)['child']['on']);self.assertFalse(c.grid_manual['child'])
 def test_grid_intent_persists_but_requires_current_proof_after_restart(self):
  c=Controller();c.request_grid('living',900);c=Controller(c.dump())
  self.assertTrue(self.evaluate(c)['living']['on'])
  self.assertFalse(self.evaluate(c,grid_ready=False,living=True)['living']['on'])
 def test_other_room_and_standard_manual_still_protected(self):
  c=Controller();c.request_grid('child',900);c.external('living',True,900)
  a=self.evaluate(c);self.assertTrue(a['child']['on']);self.assertFalse(a['living']['on'])
 def test_short_transfer_peak_does_not_cancel_manual_override(self):
  c=Controller();c.request_grid('child',900)
  self.assertTrue(self.evaluate(c,discharge=1500)['child']['on'])
  self.assertTrue(c.grid_manual['child'])
 def test_sustained_discharge_at_reserve_stops_and_keeps_reason(self):
  c=Controller();c.request_grid('child',900)
  v=dict(temp=20,pv=0,soc=30,discharge=1500,load=1500,child=True,living=False,grid_ready=True)
  self.assertTrue(c.evaluate(1000,**v)['child']['on'])
  self.assertTrue(c.evaluate(1029,**v)['child']['on'])
  self.assertFalse(c.evaluate(1030,**v)['child']['on'])
  self.assertFalse(c.grid_manual['child'])
  self.assertIn('30 %',c.grid_stop['child'])
  self.assertEqual(Controller(c.dump()).grid_stop['child'],c.grid_stop['child'])

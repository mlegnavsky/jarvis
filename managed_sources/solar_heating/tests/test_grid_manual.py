import unittest
from engine import Controller

class GridManualTests(unittest.TestCase):
 def evaluate(self,c,**kw):
  v=dict(temp=20,pv=0,soc=30,discharge=0,load=400,child=False,living=False,grid_ready=True)
  v.update(kw);return c.evaluate(1000,**v)
 def test_grid_manual_below_soc_limit_and_above_standard_temperature(self):
  c=Controller();c.configure({'temp_on':21,'temp_off':22});c.request_grid('child',900)
  self.assertTrue(self.evaluate(c,temp=23.9)['child']['on'])
  self.assertEqual(self.evaluate(c)['child']['reason'],'Ručně · síť · do 24 °C')
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

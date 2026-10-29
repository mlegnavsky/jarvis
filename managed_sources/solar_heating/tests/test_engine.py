import unittest
from engine import Controller, mean_power

class HeatingTests(unittest.TestCase):
 def make(self):
  c=Controller();c.samples=[[700,4000],[1000,4000]];return c
 def run_at(self,c,t=1000,**kw):
  values=dict(temp=20,pv=4000,soc=70,discharge=0,load=400,child=False,living=False)
  values.update(kw);return c.evaluate(t,**values)
 def test_mean_is_time_weighted_and_cloud_spike_not_enough(self):
  self.assertAlmostEqual(mean_power([[0,0],[290,6000]],300),200)
 def test_child_first_living_after_two_minutes(self):
  c=self.make();a=self.run_at(c);self.assertTrue(a['child']['on']);self.assertFalse(a['living']['on'])
  c.on_since['child']=1000
  a=self.run_at(c,1120,child=True,load=1300);self.assertTrue(a['living']['on'])
 def test_thermal_hysteresis(self):
  c=self.make();self.run_at(c);self.assertTrue(self.run_at(c,temp=23,child=True)['child']['on'])
  self.assertFalse(self.run_at(c,temp=23.5,child=True)['child']['on'])
 def test_manual_ends_on_either_limit_and_returns_auto(self):
  for kw in [dict(temp=23.5),dict(soc=50)]:
   c=self.make();c.manual['child']=True
   a=self.run_at(c,child=True,**kw);self.assertFalse(a['child']['on']);self.assertFalse(c.manual['child'])
 def test_manual_ignores_clouds_but_not_missing_temperature(self):
  c=self.make();c.manual['child']=True
  self.assertTrue(self.run_at(c,pv=0,child=True)['child']['on'])
  self.assertFalse(self.run_at(c,temp=None,child=True)['child']['on'])
 def test_off_cooldown(self):
  c=self.make();c.external('child',False,1000)
  self.assertFalse(self.run_at(c,1299)['child']['on'])
  self.assertTrue(self.run_at(c,1300)['child']['on'])
 def test_battery_exception_hysteresis(self):
  c=Controller();self.assertTrue(self.run_at(c,soc=90,pv=0)['child']['on'])
  self.assertTrue(self.run_at(c,soc=86,pv=0,child=True)['child']['on'])
  self.assertFalse(self.run_at(c,soc=84,pv=0,child=True)['child']['on'])
 def test_discharge_sheds_living_then_child(self):
  c=self.make();c.on_since['child']=500
  self.run_at(c,1000,child=True,living=True,discharge=500,load=3400)
  a=self.run_at(c,1120,child=True,living=True,discharge=500,load=3400)
  self.assertFalse(a['living']['on']);self.assertTrue(a['child']['on'])
  self.assertFalse(self.run_at(c,1240,child=True,discharge=500,load=1300)['child']['on'])
 def test_missing_energy_does_not_become_zero_or_allow_auto(self):
  c=self.make();self.assertFalse(self.run_at(c,soc=None,child=True)['child']['on'])
 def test_headroom_prevents_repeated_discharge_restart(self):
  c=self.make();self.assertFalse(self.run_at(c,load=3900)['child']['on'])
 def test_restore_has_no_restart_delay_and_preserves_manual_and_cooldown(self):
  c=self.make();c.manual['living']=True;c.off_until['child']=1100
  restored=Controller(c.dump());a=self.run_at(restored,1050,living=True)
  self.assertFalse(a['child']['on']);self.assertTrue(a['living']['on'])
 def test_pv_hysteresis_keeps_on_between_bounds(self):
  c=Controller();c.samples=[[700,1100],[1000,1100]]
  self.assertTrue(self.run_at(c,pv=1100,child=True,load=1000)['child']['on'])
  self.assertFalse(self.run_at(c,pv=1100)['child']['on'])
 def test_settings_change_without_restarting_controller(self):
  c=self.make();c.configure({'temp_on':21,'temp_off':23})
  self.assertFalse(self.run_at(c,temp=21.5)['child']['on'])
  self.assertTrue(self.run_at(c,temp=20.5)['child']['on'])
  self.assertFalse(self.run_at(c,temp=23,child=True)['child']['on'])
  self.assertEqual(Controller(c.dump()).settings['temp_off'],23)
 def test_invalid_settings_leave_previous_rules_intact(self):
  c=self.make()
  with self.assertRaises(ValueError):c.configure({'temp_on':24,'temp_off':23})
  self.assertEqual(c.settings['temp_on'],22)

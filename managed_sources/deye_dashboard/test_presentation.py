import unittest
from catalogue import card,catalogue
class Presentation(unittest.TestCase):
 def test_write_green_read_red_and_unavailable_red(self):
  c=card(catalogue([{'entity_id':'number.inverter_battery_max_charging_current'},{'entity_id':'sensor.inverter_pv_power'}]),'Test')
  self.assertIn('#16803c',c['content'])
  self.assertIn('nelze měnit',c['content'])
  self.assertIn('K čemu',c['content'])
 def test_battery_limit_explained(self):
  import catalogue as c
  self.assertTrue(hasattr(c,'explain'),'missing plain language explanations')
  self.assertIn('nabíj',c.explain('number.inverter_battery_max_charging_current'))
if __name__=='__main__':unittest.main()

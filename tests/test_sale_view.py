import sys
import unittest
sys.path.insert(0,'managed_sources/spot_control')
try:from sale_view import view,summary_cards
except ImportError:view=summary_cards=None

def walk(x):
 if isinstance(x,dict):
  yield x
  for value in x.values():yield from walk(value)
 elif isinstance(x,list):
  for value in x:yield from walk(value)

class ViewTests(unittest.TestCase):
 def setUp(self):self.assertIsNotNone(view,'native sales form is not implemented')
 def test_navigation_does_not_start_export(self):
  cards=summary_cards();nav=next(x for x in walk(cards) if x.get('name')=='Vlastní prodej')
  self.assertEqual(nav['tap_action'],{'action':'navigate','navigation_path':'/hlavni-prehled/vlastni-prodej'})
 def test_form_values_live_in_persistent_entities(self):
  result=view();entities=[x.get('entity') for x in walk(result)]
  self.assertIn('number.jarvis_sale_power_w',entities)
  self.assertIn('number.jarvis_sale_minutes',entities)
  self.assertIn('select.jarvis_sale_source',entities)
 def test_start_and_stop_are_distinct_and_stale_state_cannot_start(self):
  nodes=list(walk(view()))
  actions=[x['perform_action'] for x in nodes if x.get('action')=='perform-action']
  self.assertIn('jarvis_spot_control.start_sale',actions)
  self.assertIn('jarvis_spot_control.stop_sale',actions)
  start=next(x for x in nodes if x.get('perform_action')=='jarvis_spot_control.start_sale')
  conditional=next(x for x in nodes if x.get('type')=='conditional' and start in list(walk(x)))
  self.assertIn({'condition':'state','entity':'sensor.jarvis_energy_sales','state':'idle'},conditional['conditions'])

if __name__=='__main__':unittest.main()

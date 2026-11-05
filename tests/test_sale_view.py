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
 def test_armed_native_test_is_waiting_instead_of_claiming_measured_export(self):
  import jinja2
  cards=[x for x in walk(summary_cards()) if x.get('type')=='markdown' and 'Stav ověřování' in x.get('content','')]
  self.assertEqual(len(cards),1)
  attrs={'settings':{'battery_verified':False},'native_test':{'phase':'armed','start':1000,'end':1300,'observed':False}}
  env=jinja2.Environment();env.filters['timestamp_custom']=lambda value,fmt,local:str(value)
  text=env.from_string(cards[0]['content']).render(state_attr=lambda entity,key:attrs.get(key))
  self.assertIn('čekám na začátek',text);self.assertIn('95 %',text);self.assertNotIn('Prodej běží',text)
 def test_native_commissioning_has_a_direct_stop_on_spot_overview(self):
  cards=[x for x in walk(summary_cards()) if x.get('type')=='conditional' and {'condition':'state','entity':'sensor.jarvis_energy_sales','state':'native_test'} in x.get('conditions',[])]
  self.assertEqual(len(cards),1)
  self.assertEqual(cards[0]['card']['tap_action']['perform_action'],'jarvis_spot_control.stop_sale')

if __name__=='__main__':unittest.main()

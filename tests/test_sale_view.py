import sys
import unittest
from datetime import datetime
from zoneinfo import ZoneInfo
sys.path.insert(0,'managed_sources/spot_control')
try:from sale_view import view,summary_cards,augment_spot
except ImportError:view=summary_cards=None

def walk(x):
 if isinstance(x,dict):
  yield x
  for value in x.values():yield from walk(value)
 elif isinstance(x,list):
  for value in x:yield from walk(value)

class ViewTests(unittest.TestCase):
 def setUp(self):self.assertIsNotNone(view,'native sales form is not implemented')
 def render(self,content,attrs):
  import jinja2
  env=jinja2.Environment()
  env.filters['timestamp_custom']=lambda value,fmt,local:datetime.fromtimestamp(value,ZoneInfo('Europe/Prague')).strftime(fmt)
  return env.from_string(content).render(state_attr=lambda entity,key:attrs.get(key),states=lambda entity:'ready',is_number=lambda value:isinstance(value,(int,float)))
 def markdown(self,cards,attrs):
  return '\n'.join(self.render(x['content'],attrs) for x in walk(cards) if x.get('type')=='markdown')
 def test_normal_ui_reports_current_ha_control_and_dynamic_bias(self):
  text=self.markdown(view(),{'bias_policy':{'target_export_w':20,'minimum_soc':30,'resume_soc':31}})
  self.assertIn('Cíl:20 W',text);self.assertIn('od31 %',text)
  self.assertNotIn('nejméně 5 minut',text)
  self.assertIn('Běžný prodej řídí HA',text)
 def test_daily_block_shows_local_times_price_and_fixed_sale_reserve(self):
  attrs={'settings':{'battery_verified':True},'selected_block':{
   'start':datetime.fromisoformat('2026-11-06T17:00:00+00:00').timestamp(),
   'end':datetime.fromisoformat('2026-11-06T19:00:00+00:00').timestamp(),
   'average_net':2.5,'day':'2026-11-06','block_minutes':120}}
  text=self.markdown(summary_cards(),attrs)
  self.assertIn('18:00',text);self.assertIn('20:00',text);self.assertIn('2.5',text)
  self.assertIn('2 hodiny',text);self.assertIn('60 %',text)
 def test_history_forecast_is_informational_and_does_not_replace_fixed_reserve(self):
  text=self.markdown(summary_cards(),{'planning':{'quality':'conservative','required_soc':94,'estimated_house_kwh':7.2}})
  self.assertIn('Informační',text);self.assertIn('94 %',text)
  self.assertIn('prodejní rezervu 60 %',text)
  self.assertNotIn('Doporučená rezerva:',text)
 def test_missing_daily_block_is_visible_even_if_forecast_is_available(self):
  text=self.markdown(summary_cards(),{'planning':{'quality':'calibrated','required_soc':60,'estimated_house_kwh':5}})
  self.assertIn('Úplný dvouhodinový blok zatím není dostupný',text)
 def test_armed_battery_sale_does_not_claim_measured_export(self):
  attrs={'battery_sale':{'phase':'armed','observed':False,'start':1800000000,'end':1800007200,'power_w':500}}
  text=self.markdown(summary_cards(),attrs)
  self.assertIn('Čekám na začátek bateriového prodeje',text)
  self.assertNotIn('Prodej běží · dodávka potvrzena',text)
  attrs['battery_sale'].update(phase='measuring',observed=True)
  text=self.markdown(summary_cards(),attrs)
  self.assertIn('Prodej běží · dodávka potvrzena',text)
 def test_native_battery_phases_offer_stop_on_overview(self):
  for phase in ('armed','measuring','expiry_observed','stopping'):
   cards=[x for x in walk(summary_cards()) if x.get('type')=='conditional' and {'condition':'state','entity':'sensor.jarvis_energy_sales','state':phase} in x.get('conditions',[])]
   self.assertTrue(any(x['card'].get('tap_action',{}).get('perform_action')=='jarvis_spot_control.stop_sale' for x in cards),phase)
 def test_existing_sales_overview_is_upgraded_without_losing_original_cards(self):
  retained=[{'type':'picture','image':'/local/house.png'},{'type':'entities','entities':['sensor.home']},{'type':'markdown','content':'Domácí historie'}]
  old=[{'type':'markdown','content':'## Prodej elektřiny\nStaré řízení'},
   {'type':'tile','name':'Vlastní prodej','entity':'sensor.jarvis_energy_sales'},
   *[{'type':'markdown','content':'Starý stav'} for _ in range(5)],*retained]
  original={'sections':[{'cards':old},{'cards':[{'type':'markdown','content':'Původní'} for _ in range(5)]}]}
  upgraded=augment_spot(original)
  self.assertIn('Denní plán baterie',self.markdown(upgraded,{}))
  self.assertEqual([c.get('image') for c in upgraded['sections'][0]['cards'] if c.get('type')=='picture'],['/local/house.png'])
  self.assertEqual(original['sections'][0]['cards'][0]['content'],'## Prodej elektřiny\nStaré řízení')
  self.assertEqual(augment_spot(upgraded),upgraded)
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

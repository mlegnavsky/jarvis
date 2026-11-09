import unittest
from heating_history import patch,patch_entrypoints

FIXTURE='''title: Home
views:
- title: Domov
  cards:
  - type: custom:jarvis-device-status
    entity: switch.aqara_smart_plug_eu
    heating_entity: sensor.jarvis_topeni_child
    kind: icon
    tap_action:
      action: toggle
    hold_action:
      action: navigate
      navigation_path: /hlavni-prehled/historie-switch-aqara_smart_plug_eu
  - type: custom:jarvis-device-status
    entity: light.other
    kind: icon
- title: History child
  path: historie-switch-aqara_smart_plug_eu
  subview: true
  cards:
  - type: history-graph
    entities: [switch.aqara_smart_plug_eu]
- title: History living
  path: historie-switch-aqara_smart_plug_eu_2
  subview: true
  cards:
  - type: logbook
    entities: [switch.aqara_smart_plug_eu_2]
- !include 'unrelated.yaml'
'''

class HistoryTests(unittest.TestCase):
 def test_native_hold_only_navigates_and_unrelated_content_preserved(self):
  result=patch(FIXTURE)
  self.assertIn('- type: state-icon\n    entity: switch.aqara_smart_plug_eu',result)
  self.assertNotIn('heating_entity:',result)
  self.assertIn('navigation_path: /hlavni-prehled/historie-switch-aqara_smart_plug_eu',result)
  self.assertIn('- type: custom:jarvis-device-status\n    entity: light.other\n    kind: icon',result)
  self.assertIn("- !include 'unrelated.yaml'",result)
  self.assertEqual(result.count('type: history-graph'),1)
 def test_both_histories_have_explicit_grid_start_off_and_shared24_sensor(self):
  result=patch(FIXTURE)
  self.assertEqual(result.count('perform_action: jarvis_solar_heating.set_mode'),4)
  self.assertEqual(result.count('mode: grid_manual'),2)
  self.assertEqual(result.count('mode: \'off\''),2)
  self.assertIn('room: child',result);self.assertIn('room: living',result)
  self.assertEqual(result.count('entity: sensor.aqara_temp_humidity_sensor_t1_teplota'),2)
  self.assertIn('Zapnout topení ze sítě',result)
  self.assertIn('24 °C',result);self.assertIn('30 %',result)
 def test_idempotent_patch_and_missing_target_rejected(self):
  result=patch(FIXTURE);self.assertEqual(patch(result),result)
  with self.assertRaises(ValueError):patch('views: []\n')
 def test_room_status_labels_route_to_controls_and_buttons_are_visible_in_rooms(self):
  import yaml
  fixture='views:\n'
  for room,path in [('child','pokoj-detsky'),('living','pokoj-obyvak')]:
   fixture+='- title: Room\n  path: '+path+'\n  cards:\n  - type: picture-elements\n    elements:\n    - type: state-label\n      entity: sensor.jarvis_topeni_'+room+'\n      tap_action:\n        action: more-info\n'
  result=patch_entrypoints(fixture);d=yaml.safe_load(result)
  for view,entity in zip(d['views'],['switch.aqara_smart_plug_eu','switch.aqara_smart_plug_eu_2']):
   self.assertEqual(view['cards'][0]['type'],'grid')
   self.assertEqual(view['cards'][0]['cards'][0]['tap_action']['data']['mode'],'grid_manual')
   label=view['cards'][1]['elements'][0]
   for action in ('tap_action','hold_action'):
    self.assertEqual(label[action],{'action':'navigate','navigation_path':'/hlavni-prehled/historie-'+entity.replace('.','-')})
  self.assertEqual(patch_entrypoints(result),result)

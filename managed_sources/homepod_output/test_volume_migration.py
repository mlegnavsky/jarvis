import unittest
import yaml
from jinja2 import Template
from migrate_volume import guard_automations

class VolumeMigrationTests(unittest.TestCase):
 def source(self):
  return yaml.safe_dump([{'id':'duck','conditions':[],'actions':[{'action':'media_player.volume_set','target':{'entity_id':'media_player.homepod_obyvak_homepod_obyvak'},'data':{'volume_level':.1}}]},
    {'id':'restore','conditions':[],'actions':[{'delay':{'seconds':10}},{'action':'media_player.volume_set','target':{'entity_id':'media_player.homepod_obyvak_homepod_obyvak'},'data':{'volume_level':.45}}]},
    {'id':'unrelated','actions':[{'action':'light.turn_on'}]}],sort_keys=False)
 def allowed(self,condition,adapter):
  return Template(condition['value_template']).render(state_attr=lambda *args:adapter).strip()=='True'
 def test_active_homepod_route_blocks_both_old_volume_automations(self):
  result=yaml.safe_load(guard_automations(self.source(),{'duck','restore'}))
  for automation in result[:2]:
   self.assertFalse(self.allowed(automation['conditions'][0],'active'))
   self.assertTrue(self.allowed(automation['conditions'][0],'unsupported_core'))
  self.assertEqual(result[2],yaml.safe_load(self.source())[2])
 def test_restore_rechecks_after_delay_and_migration_is_idempotent(self):
  result=guard_automations(self.source(),{'duck','restore'})
  actions=yaml.safe_load(result)[1]['actions']
  self.assertIn('delay',actions[0])
  self.assertFalse(self.allowed(actions[-2],'active'))
  self.assertEqual(actions[-1]['action'],'media_player.volume_set')
  self.assertEqual(guard_automations(result,{'duck','restore'}),result)
 def test_unexpected_target_is_not_silently_rewritten(self):
  with self.assertRaises(ValueError):guard_automations(self.source().replace('media_player.homepod_obyvak_homepod_obyvak','media_player.other'),{'duck','restore'})

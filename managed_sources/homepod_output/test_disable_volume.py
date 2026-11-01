import importlib
import unittest
import yaml


class DisableVolumeRulesTests(unittest.TestCase):
    def test_only_selected_legacy_volume_rules_are_disabled_without_reformatting(self):
        module=importlib.import_module('migrate_volume')
        source="- id: 'duck'\n  alias: Old duck\n  actions:\n  - action: media_player.volume_set\n    target:\n      entity_id: "+module.TARGET+"\n    data:\n      volume_level: 0.1\n- id: 'heat'\n  alias: Heating # preserve this comment\n  initial_state: true\n  actions: []\n"
        result=module.disable_legacy_volume_automations(source,{'duck'})
        self.assertEqual(result,source.replace("- id: 'duck'\n","- id: 'duck'\n  initial_state: false\n"))
        self.assertFalse(yaml.safe_load(result)[0]['initial_state'])
        self.assertEqual(module.disable_legacy_volume_automations(result,{'duck'}),result)

    def test_missing_or_unrelated_action_is_rejected(self):
        module=importlib.import_module('migrate_volume')
        with self.assertRaises(ValueError):module.disable_legacy_volume_automations('[]',{'missing'})
        with self.assertRaises(ValueError):module.disable_legacy_volume_automations("- id: duck\n  actions:\n  - action: light.turn_on\n",{'duck'})

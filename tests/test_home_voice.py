"""Render the actual shipped blueprint predicates/action data; no copied decision logic."""
import unittest
from pathlib import Path
from types import SimpleNamespace
import yaml
from jinja2.nativetypes import NativeEnvironment

PATH = Path('blueprints/automation/jarvis/tv_duck.yaml')

class BlueprintLoader(yaml.SafeLoader):
    pass
BlueprintLoader.add_constructor('!input', lambda loader, node: {'input': loader.construct_scalar(node)})

class HomeVoiceTests(unittest.TestCase):
    def setUp(self):
        self.blueprint = yaml.load(PATH.read_text(), Loader=BlueprintLoader)
        self.tv_state, self.satellite_state = 'playing', 'idle'
        self.attrs = {'volume_level': 0.6, 'is_volume_muted': False, 'supported_features': 4}
        self.env = NativeEnvironment()
        self.env.globals.update(is_state=lambda entity, state: (self.tv_state if entity=='media_player.tv' else self.satellite_state)==state,
            state_attr=lambda entity, key: self.attrs.get(key), is_number=lambda value: type(value) in (float, int),
            now=lambda: 100, as_timestamp=lambda value: float(value))
        self.env.filters['bitwise_and'] = lambda left, right: int(left) & int(right)
        self.context = {'tv': 'media_player.tv', 'satellite': 'assist_satellite.jarvis', 'quiet_volume': 0.15,
            'original_volume': 0.6, 'finish_by': 220, 'wait': SimpleNamespace(completed=True)}

    def render(self, template):
        return self.env.from_string(template).render(**self.context)

    def can_duck(self):
        return self.render(self.blueprint['conditions'][0]['value_template'])

    def can_restore(self):
        return self.render(self.blueprint['actions'][-1]['if'][0]['value_template'])

    def test_playing_tv_ducks_to_lower_volume_and_records_original(self):
        self.assertTrue(self.can_duck())
        actions = self.blueprint['actions']
        self.assertEqual(self.render(actions[0]['variables']['original_volume']), 0.6)
        self.assertEqual(self.render(actions[1]['data']['volume_level']), 0.15)
        self.assertEqual(actions[1]['action'], 'media_player.volume_set')
        self.assertEqual(self.render(actions[1]['target']['entity_id']), 'media_player.tv')

    def test_off_unavailable_muted_missing_and_low_volume_are_untouched(self):
        for state in ('off', 'unknown', 'unavailable', 'paused'):
            self.tv_state = state
            self.assertFalse(self.can_duck())
        self.tv_state = 'playing'
        for attrs in ({}, {'volume_level': None, 'supported_features': 4}, {'volume_level': True, 'supported_features': 4}, {'volume_level': 0.1, 'supported_features': 4},
                      {'volume_level': 0.6, 'is_volume_muted': True, 'supported_features': 4},
                      {'volume_level': 0.6, 'supported_features': 0}):
            self.attrs = attrs
            self.assertFalse(self.can_duck())

    def test_only_idle_after_successful_wait_restores_current_owned_volume(self):
        self.attrs['volume_level'] = 0.15
        self.assertTrue(self.can_restore())
        for state in ('listening', 'processing', 'responding', 'unavailable'):
            self.satellite_state = state
            self.assertFalse(self.can_restore())
        self.satellite_state = 'idle'
        self.context['wait'].completed = False
        self.assertFalse(self.can_restore())

    def test_manual_volume_mute_and_stopped_tv_prevent_restore(self):
        self.attrs['volume_level'] = 0.4
        self.assertFalse(self.can_restore())
        self.attrs.update(volume_level=0.15, is_volume_muted=True)
        self.assertFalse(self.can_restore())
        self.attrs['is_volume_muted'] = False
        self.tv_state = 'off'
        self.assertFalse(self.can_restore())

    def test_reentry_does_not_replace_original_and_startup_is_not_a_wake(self):
        self.assertEqual(self.blueprint['mode'], 'single')
        trigger = self.blueprint['triggers'][0]
        self.assertEqual(trigger['from'], 'idle')
        self.assertEqual(trigger['to'], 'listening')
        self.assertEqual(self.render(self.blueprint['actions'][2]['variables']['finish_by']), 220)
        self.assertEqual(self.blueprint['actions'][3]['repeat']['sequence'][1]['delay'], '00:00:02')
        restore = self.blueprint['actions'][-1]['then'][0]
        self.assertEqual(self.render(restore['data']['volume_level']), 0.6)

    def test_followup_listening_keeps_waiting_until_idle_or_deadline(self):
        until = self.blueprint['actions'][3]['repeat']['until'][0]['value_template']
        self.satellite_state = 'listening'
        self.assertFalse(self.render(until))
        self.satellite_state = 'idle'
        self.assertTrue(self.render(until))
        self.satellite_state = 'processing'
        self.context['finish_by'] = 90
        self.assertTrue(self.render(until))

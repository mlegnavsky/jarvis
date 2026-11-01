import importlib
import json
from pathlib import Path
import tempfile
import unittest


class ControlTests(unittest.TestCase):
    def read(self,data,last=None):
        module=importlib.import_module('control')
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'control.json';path.write_text(json.dumps(data))
            return module.read_control(Path(root),last,100)

    def test_fresh_bounded_probe_is_the_only_operation(self):
        data={'action':'probe','nonce':'a'*32,'expires_at':180}
        self.assertEqual(self.read(data),data)
        self.assertIsNone(self.read(data,'a'*32))

    def test_fixed_output_test_is_allowed_without_arbitrary_text(self):
        data={'action':'output_test','nonce':'b'*32,'expires_at':180}
        self.assertEqual(self.read(data),data)
        self.assertIsNone(self.read({**data,'message':'arbitrary'}))

    def test_old_future_and_extra_actions_are_rejected(self):
        base={'action':'probe','nonce':'a'*32,'expires_at':180}
        for change in ({'expires_at':99},{'expires_at':10000},{'action':'play'},{'message':'PRIVATE'}):
            self.assertIsNone(self.read({**base,**change}))

    def test_software_recovery_and_fixed_voice_probe_cannot_take_targets_or_text(self):
        for action in ('audio_recover','voice_agent_probe'):
            data={'action':action,'nonce':'c'*32,'expires_at':180}
            self.assertEqual(self.read(data),data)
            self.assertIsNone(self.read({**data,'target':'other-device'}))
            self.assertIsNone(self.read({**data,'message':'arbitrary'}))

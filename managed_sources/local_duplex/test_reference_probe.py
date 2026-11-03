import importlib
from pathlib import Path
import tempfile
from types import SimpleNamespace as NS
import unittest
try: module=importlib.import_module('reference_probe')
except ModuleNotFoundError: module=None

class ProbeTests(unittest.TestCase):
    def setUp(self):self.assertIsNotNone(module,'generated-only reference probe missing')
    def test_identity_is_stable_private_and_not_replaced(self):
        with tempfile.TemporaryDirectory() as root:
            key=module.private_key(Path(root))
            self.assertEqual(len(key),32);self.assertEqual(module.private_key(Path(root)),key)
            path=Path(root)/'reference-private'/'identity.key'
            self.assertEqual(path.stat().st_mode&0o777,0o600)
            path.write_bytes(b'bad')
            with self.assertRaises(ValueError):module.private_key(Path(root))
            self.assertEqual(path.read_bytes(),b'bad')
    def test_public_identity_is_derived_from_private_key_without_a_device_connection(self):
        from aiosendspin.noise.keys import Identity
        from unittest.mock import patch
        self.assertTrue(hasattr(module,'public_identity'),'public-only preparation missing')
        with tempfile.TemporaryDirectory() as root, patch('socket.socket',side_effect=AssertionError('network forbidden')):
            public=module.public_identity(root)
            private=(Path(root)/'reference-private'/'identity.key').read_bytes()
            self.assertEqual(public,Identity.from_private_bytes(private).peer_id)
            self.assertRegex(public,r'^[A-Za-z0-9_-]{43}$')
            self.assertEqual(module.public_identity(root),public)
            self.assertEqual(len(private),32)
    def test_symlinks_never_read_as_private_identity(self):
        with tempfile.TemporaryDirectory() as root:
            p=Path(root);(p/'outside').write_bytes(b'x'*32)
            (p/'reference-private').mkdir();(p/'reference-private'/'identity.key').symlink_to(p/'outside')
            with self.assertRaises(ValueError):module.private_key(p)
    def test_ws_connection_alone_is_not_authenticated_ready(self):
        client=NS(client_id='exact',is_connected=True,is_paired=False,available=True,role=lambda _:object())
        self.assertFalse(module.client_ready(client,'exact'))
        client.is_paired=True;self.assertTrue(module.client_ready(client,'exact'))
        self.assertFalse(module.client_ready(client,'foreign'))
        client.available=False;self.assertFalse(module.client_ready(client,'exact'))
    def test_generated_packets_are_fixed_stereo_and_not_silent(self):
        data=module.generated_pcm(352)
        self.assertEqual(len(data),1408);self.assertNotEqual(data,bytes(1408))
        self.assertEqual(data[:700],module.generated_pcm(352)[:700])
    def test_health_requires_same_generation_mute_and_zero_fault(self):
        row=dict(schema=1,boot_id=9,generation=3,state=2,fault=0,muted=True)
        module.check_health(row,9,3)
        for key,value in [('boot_id',10),('generation',4),('state',0),('fault',1),('muted',False)]:
            with self.assertRaises(ValueError):module.check_health({**row,key:value},9,3)

    def test_same_generated_request_cannot_run_twice_and_is_not_a_mic_grant(self):
        import json
        with tempfile.TemporaryDirectory() as root:
            self.assertTrue(module.claim_probe(root,'b'*32,100))
            self.assertFalse(module.claim_probe(root,'b'*32,101))
            state=json.loads((Path(root)/'reference-probe-state.json').read_text())
            self.assertIs(state['microphone_authorized'],False)

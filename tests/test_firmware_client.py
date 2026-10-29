import unittest
from app.firmware_client import FirmwareClient
from app.ha import UpstreamError

class Socket:
 def __init__(self,messages):self.messages=list(messages);self.sent=[];self.closed=False
 async def send_json(self,value):self.sent.append(value)
 async def receive_json(self):return self.messages.pop(0)
 async def close(self):self.closed=True
class Supervisor:
 def __init__(self,reply=None):self.socket=Socket([reply or {'id':1,'success':True,'result':{'configured':[]}}])
 async def _websocket(self):return self.socket

class TransportTests(unittest.IsolatedAsyncioTestCase):
 async def test_uses_explicit_native_ha_capability_not_supervisor_proxy(self):
  sup=Supervisor();value=await FirmwareClient(sup).call('devices/list')
  self.assertEqual(value,{'configured':[]})
  self.assertEqual(sup.socket.sent,[{'id':1,'type':'jarvis_firmware_bridge/request','command':'devices/list','args':{}}])
  self.assertTrue(sup.socket.closed)
 async def test_native_errors_never_expose_messages_or_credentials(self):
  sup=Supervisor({'id':1,'success':False,'error':{'code':'native_unavailable','message':'private-session-secret'}})
  with self.assertRaisesRegex(UpstreamError,'firmware_unavailable') as caught:await FirmwareClient(sup).call('devices/list')
  self.assertNotIn('private',str(caught.exception));self.assertTrue(sup.socket.closed)
 async def test_unknown_commands_rejected_before_connection(self):
  sup=Supervisor()
  with self.assertRaises(UpstreamError):await FirmwareClient(sup).call('arbitrary/shell')
  self.assertEqual(sup.socket.sent,[])
 async def test_uncorrelated_frames_are_bounded(self):
  sup=Supervisor();sup.socket.messages=[{'id':99}]*70
  with self.assertRaises(UpstreamError):await FirmwareClient(sup).call('devices/list')
  self.assertTrue(sup.socket.closed)

class NativeResponseTests(unittest.TestCase):
    def test_native_list_and_reachability_fields(self):
        from app.firmware import unwrap, public_device
        native = {'configured': [{'configuration': 'voice.yaml', 'expected_config_hash': 'abcd1234',
                                  'runtime_state': {'state': 'online', 'deployed_config_hash': 'abcd1234'}}],
                  'importable': []}
        devices = unwrap(native, 'devices')
        self.assertIsInstance(devices, list)
        self.assertEqual(public_device(devices[0])['status'], 'online')

class InstallChainTests(unittest.IsolatedAsyncioTestCase):
    async def run_install(self, upload_status='completed', online=True):
        import tempfile
        from pathlib import Path
        from types import SimpleNamespace
        from unittest.mock import Mock, AsyncMock, patch
        from app.firmware import FirmwareBridge
        class Client:
            def __init__(self): self.polled = []
            async def call(self, command, args=None):
                if command == 'devices/list':
                    return {'configured': [{'configuration': 'voice.yaml', 'expected_config_hash': 'abcd1234', 'runtime_state': {'state': 'online' if online else 'offline', 'deployed_config_hash': 'abcd1234'}}], 'importable': []}
                if command == 'firmware/install':
                    return {'job_id': 'compile1', 'configuration': 'voice.yaml', 'job_type': 'compile', 'status': 'completed', 'exit_code': 0}
                if command == 'firmware/get_jobs':
                    return [{'job_id': 'upload1', 'configuration': 'voice.yaml', 'job_type': 'upload', 'status': 'running', 'depends_on': 'compile1'}]
                if command == 'firmware/get_job':
                    self.polled.append(args['job_id'])
                    return {'job_id': 'upload1', 'configuration': 'voice.yaml', 'job_type': 'upload', 'status': upload_status, 'exit_code': 0 if upload_status=='completed' else 1, 'depends_on': 'compile1'}
                raise AssertionError(command)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); (root/'esphome').mkdir()
            (root/'esphome/voice.yaml').write_text('micro_wake_word:\n  models:\n    - id: jarvis\n      model: old.json\n')
            database = Mock(); database.__enter__ = Mock(return_value=Mock()); database.__exit__ = Mock(return_value=False)
            admin = SimpleNamespace(files=SimpleNamespace(root=root), options={'firmware_targets': ['voice.yaml']}, backup=AsyncMock(), remember=Mock(), db=Mock(return_value=database))
            client = Client(); bridge = FirmwareBridge(admin, client)
            args = {'target': 'voice.yaml', 'expected_revision': bridge.store().metadata('voice.yaml')['revision']}
            with patch('app.firmware.asyncio.sleep', new=AsyncMock()):
                result = await bridge.perform('key', 'firmware_install', args)
            return result, client

    async def test_install_waits_for_native_dependent_upload(self):
        result, client = await self.run_install()
        self.assertEqual(client.polled, ['upload1'])
        self.assertEqual(result['firmware_job']['job_id'], 'upload1')
        self.assertTrue(result['verified'])

    async def test_failed_upload_is_unverified_even_with_matching_device_hash(self):
        result, client = await self.run_install(upload_status='failed')
        self.assertEqual(client.polled, ['upload1'])
        self.assertFalse(result['verified'])

    async def test_offline_precheck_never_submits_install(self):
        from app.policy import APIError
        with self.assertRaisesRegex(APIError, 'firmware_device_not_online'):
            await self.run_install(online=False)

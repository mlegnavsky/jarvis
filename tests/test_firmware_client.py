import unittest
from app.firmware_client import FirmwareClient
from app.ha import UpstreamError


class Socket:
    def __init__(self, messages):
        self.messages, self.sent, self.closed = list(messages), [], False
    async def send_json(self, value):
        self.sent.append(value)
    async def receive_json(self):
        value = self.messages.pop(0)
        if callable(value):
            return value(self.sent[-1])
        return value
    async def close(self):
        self.closed = True


class Supervisor:
    base = 'http://supervisor'
    def __init__(self):
        self.core = Socket([{'id': 1, 'success': True, 'result': {'session': 'private-session'}}])
        self.builder = Socket([{'server_version': '1.25.0', 'requires_auth': False},
                               {'message_id': 'unrelated', 'result': 'ignore'},
                               lambda sent: {'message_id': sent['message_id'], 'result': {'job_id': 'job1', 'status': 'queued'}}])
        self.connections = []
        self.requests = []
    async def _websocket(self):
        return self.core
    async def request(self, method, path):
        self.requests.append((method, path))
        return {'state': 'started', 'ingress_url': '/api/hassio_ingress/opaque-token'}
    async def _session(self):
        return self
    async def ws_connect(self, url, **kwargs):
        self.connections.append((url, kwargs))
        return self.builder


class FirmwareClientTests(unittest.IsolatedAsyncioTestCase):
    async def test_core_authenticated_ingress_correlates_and_closes(self):
        sup = Supervisor()
        result = await FirmwareClient(sup).call('firmware/compile', {'configuration': 'voice.yaml'})
        self.assertEqual(result, {'job_id': 'job1', 'status': 'queued'})
        self.assertEqual(sup.core.sent, [{'id': 1, 'type': 'supervisor/api', 'endpoint': '/ingress/session', 'method': 'post', 'data': {}}])
        self.assertEqual(sup.connections[0][0], 'http://supervisor/ingress/opaque-token/ws')
        self.assertEqual(sup.connections[0][1]['headers'], {'Cookie': 'ingress_session=private-session'})
        self.assertTrue(sup.core.closed and sup.builder.closed)
        self.assertEqual(sup.builder.sent[0]['args'], {'configuration': 'voice.yaml'})

    async def test_unknown_command_never_opens_transport(self):
        sup = Supervisor()
        with self.assertRaises(UpstreamError):
            await FirmwareClient(sup).call('devices/update_config', {})
        self.assertEqual(sup.core.sent, [])

    async def test_raw_remote_error_and_tokens_never_escape(self):
        sup = Supervisor()
        sup.builder.messages = [{'requires_auth': False}, lambda sent: {'message_id': sent['message_id'], 'error_code': 'internal_error', 'details': 'private-session password secret'}]
        with self.assertRaisesRegex(UpstreamError, '^firmware_unavailable$'):
            await FirmwareClient(sup).call('devices/list', {})
        self.assertTrue(sup.builder.closed and sup.core.closed)

    async def test_invalid_ingress_path_and_rejected_core_fail_closed(self):
        for result in ({'id': 1, 'success': False, 'error': {'message': 'secret'}}, {'id': 1, 'success': True, 'result': {'session': 'bad\r\n'}}):
            sup = Supervisor()
            sup.core.messages = [result]
            with self.assertRaises(UpstreamError):
                await FirmwareClient(sup).call('devices/list', {})
            self.assertEqual(sup.connections, [])
            self.assertTrue(sup.core.closed)

    async def test_frame_flood_is_bounded_and_closes(self):
        sup = Supervisor()
        sup.builder.messages = [{'requires_auth': False}] + [{'message_id': 'other'}] * 100
        with self.assertRaises(UpstreamError):
            await FirmwareClient(sup).call('devices/list', {})
        self.assertTrue(sup.builder.closed)

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

import unittest
from app.maintenance import MaintenanceBridge
from app.policy import APIError

class BridgeTests(unittest.IsolatedAsyncioTestCase):
    async def test_disabled_by_default(self):
        with self.assertRaises(APIError) as caught:
            await MaintenanceBridge(None, {}).request('GET', '/v1/check')
        self.assertEqual(caught.exception.code, 'maintenance_disabled')

    async def test_arbitrary_path_rejected_before_network(self):
        options = {'maintenance_enabled': True, 'maintenance_token': 'x'*32}
        with self.assertRaises(APIError):
            await MaintenanceBridge(None, options).request('POST', '/core/update')

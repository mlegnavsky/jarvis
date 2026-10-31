import unittest
import asyncio
from tests.ha_fixture import HomeFixture
from app.ha import HAClient


class InventoryTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.fixture = HomeFixture()
        url = await self.fixture.start()
        self.client = HAClient('supervisor-test', url, timeout=0.2)

    async def asyncTearDown(self):
        await self.client.close()
        await self.fixture.close()

    async def test_full_inventory_is_fresh_and_contains_registries(self):
        result = await self.client.snapshot()
        self.assertTrue(result['connected'])
        self.assertFalse(result['partial'])
        self.assertEqual(result['states'][0]['state'], 'off')
        self.assertEqual(result['registries']['areas'][0]['name'], 'Test room')
        self.assertEqual(result['system']['core']['version'], '2026.6.4')
        self.assertIn('captured_at', result)

    async def test_disconnection_does_not_serve_cached_states(self):
        await self.client.snapshot()
        self.fixture.unavailable = True
        result = await self.client.snapshot()
        self.assertFalse(result['connected'])
        self.assertIsNone(result['states'])
        self.assertTrue(result['errors'])

    async def test_unsupported_registry_reports_partial_inventory(self):
        self.fixture.unsupported.add('config/device_registry/list')
        result = await self.client.snapshot()
        self.assertTrue(result['connected'])
        self.assertTrue(result['partial'])
        self.assertIsNone(result['registries']['devices'])
        self.assertEqual(result['states'][0]['entity_id'], 'light.test')

    async def test_timeout_is_bounded_and_reported(self):
        self.fixture.delay = 1
        result = await asyncio.wait_for(self.client.snapshot(), 0.8)
        self.assertFalse(result['connected'])
        self.assertIsNone(result['states'])

    async def test_event_stream_tracks_state_and_reconnects(self):
        task = asyncio.create_task(self.client.watch(retry_delay=0.01))
        try:
            for _ in range(100):
                if self.client.stream_connected:
                    break
                await asyncio.sleep(0.01)
            self.assertTrue(self.client.stream_connected)
            ws = self.fixture.sockets[-1]
            await ws.send_json({'type': 'event', 'id': 1, 'event': {'event_type': 'state_changed', 'data': {'entity_id': 'light.test', 'new_state': {'entity_id': 'light.test', 'state': 'on'}}}})
            await asyncio.sleep(0.02)
            self.assertEqual(self.client.last_event['entity_id'], 'light.test')
            await ws.close()
            for _ in range(100):
                if len(self.fixture.sockets) > 1 and self.client.stream_connected:
                    break
                await asyncio.sleep(0.01)
            self.assertGreater(len(self.fixture.sockets), 1)
        finally:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)

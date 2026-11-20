"""RTC synchronization must timestamp after the queue and prove hardware ticks."""
import asyncio
from datetime import datetime
import unittest
from zoneinfo import ZoneInfo

try:
    import native_clock
except ImportError:
    native_clock = None

LOCAL = ZoneInfo('Europe/Prague')


def encode(t):
    dt = datetime.fromtimestamp(t, LOCAL)
    return [(dt.year - 2000) << 8 | dt.month, dt.day << 8 | dt.hour, dt.minute << 8 | dt.second]


class FakeClock:
    def __init__(self):
        self.t = datetime(2026, 11, 5, 18, 0, tzinfo=LOCAL).timestamp()

    def now(self):
        return self.t

    async def sleep(self, seconds):
        self.t += seconds


class FakeSemaphore:
    def __init__(self, clock, wait=0):
        self.clock, self.wait, self.locked = clock, wait, False

    async def __aenter__(self):
        self.clock.t += self.wait
        self.locked = True

    async def __aexit__(self, *args):
        self.locked = False


class FakeDevice:
    def __init__(self, clock, wait=0, ignore=False, frozen=False, malformed=False):
        self.clock, self.calls, self.offset = clock, [], -11
        self.ignore, self.frozen, self.malformed = ignore, frozen, malformed
        self.cached = None
        self.modbus = self
        self._semaphore = FakeSemaphore(clock, wait)

    def read(self):
        if self.malformed:
            return [0, 65535]
        raw = encode(self.clock.t + self.offset)
        if self.frozen:
            if self.cached is None:
                self.cached = raw
            return self.cached
        return raw

    async def get_response(self, code, address, **kwargs):
        assert self._semaphore.locked
        self.calls.append(('direct', code, address, kwargs))
        if code == 16:
            raw = kwargs['data']
            dt = datetime(2000 + (raw[0] >> 8), raw[0] & 255, raw[1] >> 8,
                          raw[1] & 255, raw[2] >> 8, raw[2] & 255, tzinfo=LOCAL)
            if not self.ignore:
                self.offset = dt.timestamp() - self.clock.t
            return raw
        return self.read()

    async def execute(self, code, address, **kwargs):
        assert not self._semaphore.locked
        self.calls.append(('independent', code, address, kwargs))
        return self.read()


class NativeClockTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.assertIsNotNone(native_clock, 'native RTC helper is not implemented')
        self.clock = FakeClock()

    async def sync(self, **kwargs):
        device = FakeDevice(self.clock, **kwargs)
        result = await native_clock.sync_native_clock(device, self.clock.now, self.clock.sleep)
        return device, result

    async def test_admission_runs_under_transport_lock_before_timestamp_and_write(self):
        device = FakeDevice(self.clock, wait=7)
        before = self.clock.t
        async def admit(get_response):
            self.assertTrue(device._semaphore.locked)
            self.assertEqual(device.calls, [])
            self.clock.t += 3
            return True
        result = await native_clock.sync_native_clock(device, self.clock.now, self.clock.sleep, admit=admit)
        self.assertTrue(result['verified'])
        self.assertEqual(device.calls[0][3]['data'], encode(before + 10))

    async def test_rejected_admission_never_changes_clock_and_releases_transport(self):
        for verdict in (False, None):
            device = FakeDevice(self.clock)
            async def admit(get_response):return verdict
            result = await native_clock.sync_native_clock(device, self.clock.now, self.clock.sleep, admit=admit)
            self.assertFalse(result['verified'])
            self.assertEqual(device.calls, [])
            self.assertFalse(device._semaphore.locked)

    async def test_admission_exception_never_writes_clock(self):
        device = FakeDevice(self.clock)
        async def admit(get_response):raise ValueError('Owner enabled export')
        result = await native_clock.sync_native_clock(device, self.clock.now, self.clock.sleep, admit=admit)
        self.assertFalse(result['verified']);self.assertEqual(device.calls, [])
        self.assertFalse(device._semaphore.locked)

    async def test_lock_wait_does_not_age_the_encoded_write_timestamp(self):
        before = self.clock.t
        device, result = await self.sync(wait=10)
        self.assertTrue(result['verified'])
        self.assertEqual(device.calls[0][3]['data'], encode(before + 10))
        self.assertEqual(result['before_timestamp'], before + 10)

    async def test_actual_clock_must_tick_after_independent_read(self):
        device, result = await self.sync()
        self.assertTrue(result['supported'])
        self.assertTrue(result['verified'])
        self.assertGreaterEqual(result['progress_seconds'], 2)
        self.assertLessEqual(abs(result['error_seconds']), 5)
        self.assertEqual([call[:3] for call in device.calls],
                         [('direct', 16, 62), ('direct', 3, 62), ('independent', 3, 62)])
        self.assertEqual(device.calls[1][3], {'count': 3})
        self.assertEqual(device.calls[2][3], {'count': 3})

    async def test_ignored_stale_write_is_not_verified(self):
        _, result = await self.sync(ignore=True)
        self.assertFalse(result['verified'])
        self.assertGreater(abs(result['error_seconds']), 5)

    async def test_same_cached_acknowledgement_is_not_clock_progress(self):
        _, result = await self.sync(frozen=True)
        self.assertFalse(result['verified'])
        self.assertEqual(result['progress_seconds'], 0)

    async def test_unsupported_transport_never_writes(self):
        class Unsupported:
            async def execute(self, *args, **kwargs):
                raise AssertionError('Unsupported transport must never execute')
        result = await native_clock.sync_native_clock(Unsupported(), self.clock.now, self.clock.sleep)
        self.assertFalse(result['supported'])
        self.assertFalse(result['verified'])

    async def test_malformed_hardware_read_is_not_verified(self):
        _, result = await self.sync(malformed=True)
        self.assertFalse(result['verified'])
        self.assertTrue(result['error'])

    async def test_independent_read_failure_stays_unverified_and_releases_lock(self):
        device = FakeDevice(self.clock)
        async def timeout(*args, **kwargs):
            raise TimeoutError('Read expired')
        device.execute = timeout
        result = await native_clock.sync_native_clock(device, self.clock.now, self.clock.sleep)
        self.assertFalse(result['verified'])
        self.assertFalse(device._semaphore.locked)
        self.assertIn('timed out', result['error'])

    async def test_invalid_final_calendar_bytes_cannot_be_verified(self):
        device = FakeDevice(self.clock)
        async def malformed(*args, **kwargs):
            return [0x1AFF, 0x0501, 0]
        device.execute = malformed
        result = await native_clock.sync_native_clock(device, self.clock.now, self.clock.sleep)
        self.assertFalse(result['verified'])
        self.assertTrue(result['error'])

    async def test_invalid_now_or_unencodable_year_never_writes(self):
        for timestamp in (float('nan'), datetime(1999, 1, 1, tzinfo=LOCAL).timestamp(),
                          datetime(2256, 1, 1, tzinfo=LOCAL).timestamp()):
            self.clock.t = timestamp
            device, result = await self.sync()
            self.assertFalse(result['verified'])
            self.assertEqual(device.calls, [])


if __name__ == '__main__':
    unittest.main()

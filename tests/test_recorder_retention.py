import ast
import asyncio
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest


class RetentionAdapterTests(unittest.IsolatedAsyncioTestCase):
    async def setup_adapter(self, archive_error=False, save_error=False):
        path = Path('managed_sources/recorder_retention/__init__.py')
        self.assertTrue(path.exists(), 'retention adapter missing')
        tree = ast.parse(path.read_text())
        setup = next(n for n in tree.body if isinstance(n, ast.AsyncFunctionDef) and n.name == 'async_setup')
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.saved = {}; self.calls = []; self.reports = []; self.listeners = {}
        parent = self
        class Store:
            def __init__(self, *args): pass
            async def async_load(self): return parent.saved
            async def async_save(self, body):
                if save_error: raise OSError('disk full')
                parent.saved = dict(body)
        def capture(*args):
            if archive_error: raise ValueError('checksum mismatch')
            return {'source_bytes': 6000000000, 'archive_bytes': 4000000}
        async def call(*args, **kwargs): self.calls.append((args, kwargs))
        async def executor(fn, *args): return fn(*args)
        self.hass = SimpleNamespace(config=SimpleNamespace(path=lambda *p: str(Path(tmp.name).joinpath(*p))),
            async_add_executor_job=executor, services=SimpleNamespace(async_call=call),
            states=SimpleNamespace(async_set=lambda *args:self.reports.append(args)), is_running=False,
            bus=SimpleNamespace(async_listen_once=lambda event, callback:self.listeners.update({event:callback})))
        scope = {'DOMAIN':'jarvis_recorder_retention','Path':Path,'Store':Store,'capture':capture,'asyncio':asyncio,
            'shutil':SimpleNamespace(disk_usage=lambda path:SimpleNamespace(free=2000000000)),
            'time':SimpleNamespace(time=lambda:100000), 'timedelta':__import__('datetime').timedelta,
            'async_track_time_interval':lambda *args:None}
        exec(compile(ast.Module(body=[setup],type_ignores=[]),str(path),'exec'),scope)
        await scope['async_setup'](self.hass,{})
        self.maintain=self.listeners['homeassistant_started']

    async def test_archive_failure_never_requests_irreversible_purge(self):
        await self.setup_adapter(archive_error=True)
        await self.maintain()
        self.assertEqual(self.calls, [])
        self.assertEqual(self.reports[-1][1], 'error')

    async def test_success_queues_bounded_purge_once_per_day_without_repack(self):
        await self.setup_adapter()
        await self.maintain(); await self.maintain()
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.calls[0][0], ('recorder','purge',{'keep_days':7,'repack':False,'apply_filter':False}))
        self.assertFalse(self.reports[-1][2]['purge_completion_verified'])

    async def test_failed_durable_marker_prevents_purge(self):
        await self.setup_adapter(save_error=True)
        await self.maintain()
        self.assertEqual(self.calls, [])

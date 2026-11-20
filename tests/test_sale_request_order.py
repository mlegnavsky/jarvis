"""Exercise the actual nested HA control handlers without a Home Assistant host."""
import ast
import asyncio
from pathlib import Path
from types import SimpleNamespace
import unittest


def handlers(namespace):
    source = ast.parse(Path('managed_sources/spot_control/sale_setup.py').read_text())
    setup = next(n for n in source.body if isinstance(n, ast.AsyncFunctionDef) and n.name == 'async_setup_sales')
    names = {'configure', '_configure_locked', 'stop_sale'}
    body = [n for n in setup.body if isinstance(n, ast.AsyncFunctionDef) and n.name in names]
    exec(compile(ast.Module(body=body, type_ignores=[]), '<production-handlers>', 'exec'), namespace)
    return namespace


class RequestOrderTests(unittest.IsolatedAsyncioTestCase):
    async def test_enable_rejects_incomplete_cleanup(self):
        prefs = {'automatic': False}
        saved = []
        async def persist():
            saved.append(dict(prefs))
        async def event(*args):
            pass
        ns = handlers(dict(lock=asyncio.Lock(), prefs=prefs, persist_settings=persist,
                           event=event, time=SimpleNamespace(time=lambda: 100),
                           window=SimpleNamespace(active=False),
                           battery=SimpleNamespace(active=True, record={'phase': 'stopping'}),
                           c=SimpleNamespace(active=False)))
        with self.assertRaisesRegex(ValueError, 'ukončení'):
            await ns['configure']({'automatic': True})
        self.assertFalse(prefs['automatic'])
        self.assertEqual(saved, [])

    async def test_persistence_failure_does_not_skip_physical_stop(self):
        prefs = {'automatic': True}
        stopped = []
        async def fail():
            raise OSError('storage unavailable')
        async def event(*args):
            pass
        async def stop(reason):
            stopped.append((reason, prefs['automatic']))
        async def handled():
            pass
        ns = handlers(dict(lock=asyncio.Lock(), prefs=prefs, persist_settings=fail,
                           event=event, time=SimpleNamespace(time=lambda: 100),
                           window=SimpleNamespace(active=False), battery=SimpleNamespace(active=False),
                           c=SimpleNamespace(stop=stop, error=''), handle_stop=handled,
                           handle_native_stops=handled, active=lambda: False))
        await ns['stop_sale']()
        self.assertEqual(stopped, [('manual', False)])

    async def test_enable_waits_until_previous_stop_finishes(self):
        lock = asyncio.Lock()
        prefs = {'automatic': True}
        physical_stop = asyncio.Event()
        release_stop = asyncio.Event()
        observations = []

        async def persist():
            pass

        async def event(*args):
            pass

        async def stop(reason):
            observations.append(prefs['automatic'])
            physical_stop.set()
            await release_stop.wait()

        async def handled():
            pass

        ns = handlers(dict(lock=lock, prefs=prefs, persist_settings=persist, event=event,
                           time=SimpleNamespace(time=lambda: 100),
                           window=SimpleNamespace(active=False), battery=SimpleNamespace(active=False),
                           c=SimpleNamespace(stop=stop, error=''), handle_stop=handled,
                           handle_native_stops=handled, active=lambda: False))
        await lock.acquire()
        stopping = asyncio.create_task(ns['stop_sale']())
        await asyncio.sleep(0)
        enabling = asyncio.create_task(ns['configure']({'automatic': True}))
        await asyncio.sleep(0)
        lock.release()
        try:
            await asyncio.wait_for(physical_stop.wait(), 1)
            self.assertFalse(prefs['automatic'], 'new enable ran before old physical stop')
            self.assertFalse(enabling.done(), 'enable must wait for complete cleanup')
        finally:
            release_stop.set()
            await asyncio.gather(stopping, enabling)
        self.assertEqual(observations, [False])
        self.assertTrue(prefs['automatic'])


if __name__ == '__main__':
    unittest.main()

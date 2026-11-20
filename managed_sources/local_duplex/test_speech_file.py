import asyncio
from concurrent.futures import ThreadPoolExecutor, TimeoutError
import importlib
import os
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch
import wave


class SpeechFileTests(unittest.IsolatedAsyncioTestCase):
    def module(self):return importlib.import_module('speech_file')

    def test_canonical_wave_local_uri_and_private_permissions(self):
        with tempfile.TemporaryDirectory() as root:
            store=self.module().SpeechFiles(root)
            item=store.create(b'\x00\x20'*1600)
            self.assertTrue(item.media_id.startswith('media-source://media_source/local/jarvis_speech/'))
            with wave.open(str(item.path),'rb') as audio:
                self.assertEqual((audio.getframerate(),audio.getnchannels(),audio.getsampwidth(),audio.getnframes()),(16000,1,2,1600))
                self.assertEqual(audio.readframes(1600),b'\x00\x20'*1600)
            self.assertEqual(item.path.stat().st_mode&0o777,0o600)
            self.assertEqual(item.path.parent.stat().st_mode&0o777,0o700)
            store.release(item.name)
            self.assertFalse(item.path.exists())

    def test_bound_retention_preserves_foreign_files_and_rejects_links(self):
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as external:
            store=self.module().SpeechFiles(root,clock=lambda:1000)
            items=[store.create(bytes(320)) for _ in range(4)]
            foreign=items[0].path.parent/'user.wav';foreign.write_bytes(b'KEEP')
            with self.assertRaises(ValueError):store.create(bytes(320))
            os.utime(items[0].path,(0,0))
            replacement=store.create(bytes(320))
            self.assertFalse(items[0].path.exists())
            self.assertEqual(foreign.read_bytes(),b'KEEP')
            with self.assertRaises(ValueError):store.release('../user.wav')
            replacement.path.unlink();replacement.path.symlink_to(foreign)
            with self.assertRaises(ValueError):store.release(replacement.name)
            self.assertEqual(foreign.read_bytes(),b'KEEP')
            blocked=Path(external)/'jarvis_speech';blocked.symlink_to(items[0].path.parent,target_is_directory=True)
            with self.assertRaises(ValueError):self.module().SpeechFiles(external).create(bytes(320))

    def race_after_listing(self,store,second):
        module=self.module();original=module.os.listdir;listed=threading.Event();resume=threading.Event()
        def listing(directory):
            names=original(directory)
            if not listed.is_set():listed.set();resume.wait(3)
            return names
        results=[]
        with patch.object(module.os,'listdir',side_effect=listing),ThreadPoolExecutor(max_workers=2) as workers:
            first=workers.submit(store.create,bytes(320))
            try:
                self.assertTrue(listed.wait(2))
                other=workers.submit(second)
                try:other.result(timeout=.2)
                except (TimeoutError,ValueError):pass
            finally:resume.set()
            for future in (first,other):
                try:results.append(future.result(timeout=2))
                except ValueError:results.append('limit')
        return results

    def test_concurrent_creates_cannot_exceed_four_resources(self):
        with tempfile.TemporaryDirectory() as root:
            store=self.module().SpeechFiles(root)
            for _ in range(3):store.create(bytes(320))
            results=self.race_after_listing(store,lambda:store.create(bytes(320)))
            self.assertEqual(len(list(store.root.glob('*.wav'))),4)
            self.assertEqual(results.count('limit'),1)

    def test_release_cannot_remove_entry_between_creation_listing_and_stat(self):
        with tempfile.TemporaryDirectory() as root:
            store=self.module().SpeechFiles(root);old=store.create(bytes(320))
            self.race_after_listing(store,lambda:store.release(old.name))
            self.assertEqual(len(list(store.root.glob('*.wav'))),1)

    async def test_cancel_during_creation_drains_and_removes_file(self):
        with tempfile.TemporaryDirectory() as root:
            store=self.module().SpeechFiles(root);entered=asyncio.Event();finish=asyncio.Event()
            async def run(fn,*args):
                if fn.__name__=='create':entered.set();await finish.wait()
                return fn(*args)
            execute=lambda fn,*args:asyncio.create_task(run(fn,*args))
            task=asyncio.create_task(self.module().create_owned_file(execute,store,bytes(320)))
            await entered.wait();task.cancel();finish.set()
            with self.assertRaises(asyncio.CancelledError):await task
            self.assertEqual(list(store.root.glob('*.wav')),[])

    async def test_owned_file_release_is_idempotent(self):
        with tempfile.TemporaryDirectory() as root:
            store=self.module().SpeechFiles(root)
            async def run(fn,*args):return fn(*args)
            execute=lambda fn,*args:asyncio.create_task(run(fn,*args))
            prepared=await self.module().create_owned_file(execute,store,bytes(320))
            await self.module().release_prepared(prepared)
            await self.module().release_prepared(prepared)
            self.assertEqual(list(store.root.glob('*.wav')),[])

    async def test_output_releases_file_on_completion_cancellation_and_stale_owner(self):
        io=importlib.import_module('ha_io')
        for mode in ('complete','cancel','stale'):
            released=[];started=asyncio.Event()
            player=NS(state='idle',available=True,is_volume_muted=False,volume_level=.4)
            async def release():released.append(True)
            async def prepare(_text):
                if mode=='stale':output.disown()
                return NS(media_id='owned-file',pcm=bytes(3200),release=release)
            async def start(_player,_media):player.state='playing';started.set()
            async def stop(_player):player.state='idle'
            async def wait(_seconds):
                if mode=='cancel':await asyncio.Event().wait()
                player.state='idle';await asyncio.sleep(0)
            output=io.LocalOutput(lambda:player,prepare,start,stop,sleep=wait)
            task=asyncio.create_task(output.play('fixed'))
            if mode=='cancel':await started.wait();task.cancel()
            if mode in ('cancel','stale'):
                with self.assertRaises(asyncio.CancelledError):await task
            else:await task
            self.assertEqual(released,[True],mode)

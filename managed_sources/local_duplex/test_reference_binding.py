"""Run the HA-facing orchestration with no Home Assistant or hardware process."""
import ast
import asyncio
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace as NS
import unittest
from reference_probe import claim_probe


class ReferenceBindingTests(unittest.IsolatedAsyncioTestCase):
    def app(self, root, probe_class, endpoint):
        tree=ast.parse(Path(__file__).with_name('__init__.py').read_text())
        cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='LocalDialogue')
        methods=[n for n in cls.body if isinstance(n,ast.AsyncFunctionDef) and n.name in ('reference_probe','reference_identity','handle')]
        async def native_session(value,handler):return await handler(value)
        scope=dict(asyncio=asyncio,time=time,claim_probe=claim_probe,
                   NativeReferenceEndpoint=endpoint,GeneratedReferenceProbe=probe_class,
                   native_session=native_session,pipeline_signature=lambda _: 'valid')
        exec(compile(ast.Module(body=methods,type_ignores=[]),'production-reference-binding','exec'),scope)
        app=NS(probing=False,active=None,room_isolated=False,reference_probe_task=None,root=root,report={},lock=asyncio.Lock())
        entry=NS(domain='esphome',data={'noise_psk':'synthetic-test-marker'})
        app.hass=NS(async_add_executor_job=asyncio.to_thread,
                    config_entries=NS(async_get_entry=lambda _:entry))
        app.player=lambda:NS(state='idle',_entry_data=NS(entry_id='test-native'))
        app.saved=[]
        async def save():app.saved.append(app.probing)
        app.save=save
        app.run=lambda nonce:scope['reference_probe'](app,nonce)
        app.handle=lambda value:scope['handle'](app,value)
        app.identity_scope=scope
        app.prepare_identity=(lambda:scope['reference_identity'](app)) if 'reference_identity' in scope else None
        return app

    async def test_identity_preparation_reports_only_public_id_without_endpoint_access(self):
        def forbidden(*args,**kwargs):raise AssertionError('native endpoint must remain untouched')
        with tempfile.TemporaryDirectory() as root:
            app=self.app(root,forbidden,forbidden)
            self.assertIsNotNone(app.prepare_identity,'local-only identity binding missing')
            app.identity_scope['public_identity']=lambda path:'P'*43
            app.player=forbidden
            await app.prepare_identity()
            self.assertEqual(app.report['reference_identity'],
                {'status':'passed','server_id':'P'*43,'microphone_opened':False,'network_opened':False})
            self.assertFalse(app.probing)
            app.report={};await app.lock.acquire()
            try:await app.prepare_identity()
            finally:app.lock.release()
            self.assertEqual(app.report,{})

    async def test_identity_failure_never_exposes_private_material_and_releases_guard(self):
        def failed(path):raise ValueError('sensitive private-key details')
        with tempfile.TemporaryDirectory() as root:
            app=self.app(root,object,object)
            self.assertIsNotNone(app.prepare_identity,'local-only identity binding missing')
            app.identity_scope['public_identity']=failed
            await app.prepare_identity()
            self.assertEqual(app.report['reference_identity']['status'],'failed')
            self.assertEqual(app.report['reference_identity']['error'],'ValueError')
            self.assertNotIn('sensitive',str(app.report))
            self.assertFalse(app.probing)

    async def test_normal_input_waiting_for_initialization_or_lock_cannot_overlap_probe(self):
        for boundary in ('initialization','dialogue_lock'):
            with self.subTest(boundary=boundary), tempfile.TemporaryDirectory() as root:
                waiting=asyncio.Event();resume=asyncio.Event();probing=asyncio.Event();finish=asyncio.Event()
                class Probe:
                    def __init__(self,*args):self.report={'status':'running'}
                    async def run(self):probing.set();await finish.wait()
                app=self.app(root,Probe,lambda *args,**kwargs:object())
                app.report['self_test']={'status':'passed','pipeline_signature':'valid'}
                app.lock=asyncio.Lock();app.ready=lambda:True;started=[]
                async def ensure():
                    waiting.set()
                    if boundary=='initialization':await resume.wait()
                async def dialogue(value):started.append(True)
                app.ensure_homepod_initialized=ensure;app.dialogue=dialogue
                if boundary=='dialogue_lock':await app.lock.acquire()
                normal=asyncio.create_task(app.handle(NS(run=NS(pipeline=object()))))
                await asyncio.wait_for(waiting.wait(),1)
                # The lock case represents maintenance acquired by another path;
                # reference_probe itself must refuse a held dialogue lock below.
                probe=None
                if boundary=='dialogue_lock':app.probing=True;probing.set()
                else:probe=asyncio.create_task(app.run('a'*32))
                try:
                    await asyncio.wait_for(probing.wait(),1)
                    resume.set()
                    if boundary=='dialogue_lock':app.lock.release()
                    await asyncio.wait_for(normal,1)
                    self.assertEqual(started,[],'normal dialogue overlapped reference ownership')
                finally:
                    finish.set()
                    if probe:await probe
                    if not normal.done():normal.cancel();await asyncio.gather(normal,return_exceptions=True)

    async def test_occupied_dialogue_cannot_consume_request_or_start_endpoint(self):
        def forbidden(*args,**kwargs):raise AssertionError('endpoint must remain unused')
        with tempfile.TemporaryDirectory() as root:
            app=self.app(root,forbidden,forbidden);app.active=object()
            await app.run('a'*32)
            self.assertFalse((Path(root)/'reference-probe-state.json').exists())
            self.assertEqual(app.report,{})

    async def test_native_session_preparing_under_lock_blocks_probe_before_active_assignment(self):
        def forbidden(*args,**kwargs):raise AssertionError('endpoint must remain unused')
        with tempfile.TemporaryDirectory() as root:
            app=self.app(root,forbidden,forbidden)
            await app.lock.acquire()
            try:await app.run('a'*32)
            finally:app.lock.release()
            self.assertFalse((Path(root)/'reference-probe-state.json').exists())
            self.assertEqual(app.report,{})

    async def test_completed_probe_is_one_shot_and_cannot_enable_production_reference(self):
        calls=[]
        class Probe:
            def __init__(self,*args):self.report={'status':'running'}
            async def run(self):calls.append('ran');self.report['status']='passed'
        def endpoint(player,*,encrypted):
            if not encrypted:raise AssertionError('lost native encryption check')
            return object()
        with tempfile.TemporaryDirectory() as root:
            app=self.app(root,Probe,endpoint)
            await app.run('a'*32)
            self.assertEqual(app.report['reference_probe']['status'],'passed')
            self.assertFalse(app.report['reference_probe']['production_reference_enabled'])
            await app.run('a'*32)
            self.assertEqual(calls,['ran'])
            self.assertEqual(app.report['reference_probe']['status'],'already_consumed')
            self.assertFalse(app.probing);self.assertIsNone(app.reference_probe_task)

    async def test_cancellation_waits_for_probe_cleanup_before_releasing_maintenance(self):
        started=asyncio.Event();cleaning=asyncio.Event();released=asyncio.Event()
        class Probe:
            def __init__(self,*args):self.report={'status':'running'}
            async def run(self):
                try:started.set();await asyncio.Event().wait()
                finally:cleaning.set();await released.wait()
        with tempfile.TemporaryDirectory() as root:
            app=self.app(root,Probe,lambda *args,**kwargs:object())
            task=asyncio.create_task(app.run('a'*32))
            await asyncio.wait_for(started.wait(),1);task.cancel()
            await asyncio.wait_for(cleaning.wait(),1)
            self.assertTrue(app.probing);self.assertIs(app.reference_probe_task,task)
            released.set()
            with self.assertRaises(asyncio.CancelledError):await task
            self.assertFalse(app.probing);self.assertIsNone(app.reference_probe_task)
            self.assertEqual(app.saved,[False])

    async def test_native_failure_is_sanitized_and_releases_maintenance(self):
        def endpoint(*args,**kwargs):raise ValueError('sensitive native connection details')
        with tempfile.TemporaryDirectory() as root:
            app=self.app(root,object,endpoint)
            await app.run('a'*32)
            self.assertEqual(app.report['reference_probe']['status'],'failed')
            self.assertEqual(app.report['reference_probe']['error'],'ValueError')
            self.assertNotIn('sensitive',str(app.report))
            self.assertFalse(app.probing);self.assertIsNone(app.reference_probe_task)

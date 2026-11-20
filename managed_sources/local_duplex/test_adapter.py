"""Exercise the actual routing wrapper with native boundary doubles."""
import asyncio
import importlib
from types import SimpleNamespace as NS
import unittest


class AdapterTests(unittest.IsolatedAsyncioTestCase):
    async def test_changed_pipeline_still_reaches_operator_before_original_core(self):
        adapter=importlib.import_module('adapter');hass=object();events=[]
        class Input:
            async def execute(value,validate=False):events.append('cloud_fallback')
        async def handle(value):events.append('dialogue')
        async def operator(value):events.append('local_close')
        adapter.install(hass,Input,'2026.6.4','expected','satellite',handle,operator_handle=operator)
        value=Input();value.run=NS(hass=hass,pipeline=NS(id='changed'),start_stage='stt',end_stage='tts',id='late')
        value.satellite_id='satellite';value.wake_word_phrase=None;value.stt_stream=object();value.stt_metadata=NS(sample_rate=16000)
        await value.execute(validate=True)
        self.assertEqual(events,['local_close'])

    async def test_operator_installation_proof_rejects_replaced_wrapper_and_other_owner(self):
        adapter=importlib.import_module('adapter');self.assertTrue(hasattr(adapter,'operator_installed'))
        hass=object()
        class Input:
            async def execute(value,validate=False):pass
        async def handle(value):pass
        async def operator(value):return adapter.DELEGATE
        adapter.install(hass,Input,'2026.6.4','p','s',handle,operator_handle=operator)
        self.assertTrue(adapter.operator_installed(hass,Input,operator))
        self.assertFalse(adapter.operator_installed(object(),Input,operator))
        async def replacement(value,validate=False):pass
        Input.execute=replacement
        self.assertFalse(adapter.operator_installed(hass,Input,operator))

    async def test_fixed_operator_route_runs_before_cloud_preparation_and_metadata_begin_skips_debug_start(self):
        adapter=importlib.import_module('adapter');hass=object();events=[]
        class Input:
            async def execute(value,validate=False):events.append('normal_native')
            async def validate(value):raise AssertionError('operator must not prepare cloud providers')
        async def handle(value):events.append('dialogue')
        async def body(value):events.append('bounded_memory_only')
        async def operator(value):
            return await adapter.native_session(value,body,begin=lambda:events.append('metadata_start'))
        adapter.install(hass,Input,'2026.6.4','p','s',handle,operator_handle=operator)
        async def end():events.append('native_end')
        def start(**kwargs):raise AssertionError('Core debug recording must not start')
        value=Input();value.run=NS(hass=hass,pipeline=NS(id='p'),start_stage='stt',
            end_stage='tts',id='native-room',tts_stream=None,start=start,end=end)
        value.session=NS(conversation_id='c');value.device_id='d';value.satellite_id='s'
        value.wake_word_phrase=None;value.stt_stream=object();value.stt_metadata=NS(sample_rate=16000)
        await value.execute(validate=True)
        self.assertEqual(events,['metadata_start','bounded_memory_only','native_end'])

    async def test_operator_decline_keeps_normal_validation_and_target_guards(self):
        adapter=importlib.import_module('adapter');hass=object();events=[]
        class Input:
            async def execute(value,validate=False):events.append('native')
            async def validate(value):events.append('validate')
        async def handle(value):events.append('dialogue')
        async def operator(value):events.append('operator_check');return adapter.DELEGATE
        adapter.install(hass,Input,'2026.6.4','p','s',handle,operator_handle=operator)
        value=Input();value.run=NS(hass=hass,pipeline=NS(id='p'),start_stage='stt',end_stage='tts',id='real')
        value.satellite_id='other';value.wake_word_phrase=None;value.stt_stream=object();value.stt_metadata=NS(sample_rate=16000)
        await value.execute(validate=True)
        self.assertEqual(events,['native']);events.clear()
        value.satellite_id='s';await value.execute(validate=True)
        self.assertEqual(events,['operator_check','validate','dialogue'])

    def setup_adapter(self, *, core='2026.6.4'):
        adapter=importlib.import_module('adapter')
        self.native=[];self.sessions=[];self.hass=object()
        class Input:
            async def execute(value,validate=False):self.native.append((value,validate))
            async def validate(value):pass
        async def handle(value):self.sessions.append(value)
        self.result=adapter.install(self.hass,Input,core,'pipeline','satellite',handle)
        def create(**changes):
            value=Input();value.run=NS(hass=self.hass,pipeline=NS(id='pipeline'),start_stage='stt',end_stage='tts',id='real')
            value.satellite_id='satellite';value.wake_word_phrase='Jarvis'
            value.stt_stream=object();value.stt_metadata=NS(sample_rate=16000)
            for key,val in changes.items():setattr(value,key,val)
            return value
        return Input,create

    async def test_target_uses_continuous_session(self):
        _,create=self.setup_adapter();value=create()
        await value.execute(validate=True)
        self.assertEqual(self.sessions,[value]);self.assertEqual(self.native,[])

    async def test_other_pipeline_satellite_and_bare_hint_delegate(self):
        _,create=self.setup_adapter()
        for kind in ('pipeline','satellite','hint','synthetic'):
            value=create()
            if kind=='pipeline':value.run.pipeline.id='other'
            if kind=='satellite':value.satellite_id='other'
            if kind=='hint':value.wake_word_phrase='zhasni'
            if kind=='synthetic':value.run.id='synthetic-probe'
            await value.execute(validate=True)
        self.assertEqual(len(self.native),4);self.assertEqual(self.sessions,[])

    async def test_unsupported_core_never_installs(self):
        _,create=self.setup_adapter(core='2026.7.0');await create().execute()
        self.assertEqual(self.result,'unsupported_core');self.assertEqual(len(self.native),1)

    async def test_physical_button_activation_can_start_session(self):
        _,create=self.setup_adapter();value=create(wake_word_phrase=None)
        await value.execute();self.assertEqual(self.sessions,[value])

    async def test_transcription_only_client_never_enters_control_dialogue(self):
        _,create=self.setup_adapter();value=create();value.run.end_stage='stt'
        await value.execute();self.assertEqual(self.sessions,[]);self.assertEqual(len(self.native),1)

    async def test_unverified_provider_keeps_prepared_native_fallback(self):
        adapter=importlib.import_module('adapter');hass=object();seen=[]
        class Input:
            async def execute(self,validate=False):seen.append(validate)
            async def validate(self):seen.append('prepared')
        async def handle(value):return adapter.DELEGATE
        adapter.install(hass,Input,'2026.6.4','p','s',handle)
        value=Input();value.run=NS(hass=hass,pipeline=NS(id='p'),start_stage='stt',end_stage='tts',id='r')
        value.satellite_id='s';value.wake_word_phrase='Jarvis';value.stt_stream=object();value.stt_metadata=NS(sample_rate=16000)
        await value.execute(validate=True)
        self.assertEqual(seen,['prepared',False])

    async def test_prepared_native_stream_is_deleted_before_run_start(self):
        adapter=importlib.import_module('adapter')
        events=[]
        class Run:
            tts_stream=NS(delete=lambda:events.append('stream_deleted'))
            def start(self,**kwargs):
                self.assert_no_stream=self.tts_stream is None;events.append('start')
            async def end(self):events.append('end')
        value=NS(run=Run(),session=NS(conversation_id='c'),device_id='d',satellite_id='s')
        async def body(value):events.append('mic_and_independent_playback')
        await adapter.native_session(value,body)
        self.assertTrue(value.run.assert_no_stream)
        self.assertEqual(events,['stream_deleted','start','mic_and_independent_playback','end'])
        self.assertFalse(hasattr(value.run,'_jarvis_suppressed_activation'))

    async def test_native_run_always_ends_on_cancellation(self):
        adapter=importlib.import_module('adapter');ended=[]
        value=NS(run=NS(tts_stream=None,start=lambda **kw:None,end=None),session=NS(conversation_id='c'),device_id='d',satellite_id='s')
        async def end():ended.append(True)
        value.run.end=end
        async def body(value):raise asyncio.CancelledError()
        with self.assertRaises(asyncio.CancelledError):await adapter.native_session(value,body)
        self.assertEqual(ended,[True])

    async def test_validation_failure_and_cancellation_emit_terminal_cleanup(self):
        adapter=importlib.import_module('adapter')
        for error in (ValueError('provider unavailable'),asyncio.CancelledError()):
            with self.subTest(error=type(error).__name__):
                events=[];hass=object()
                class Input:
                    async def execute(self,validate=False):events.append('legacy')
                    async def validate(self):raise error
                async def end():events.append('end')
                async def handle(value):events.append('dialogue')
                adapter.install(hass,Input,'2026.6.4','p','s',handle,error_event=lambda error:'error')
                value=Input();value.run=NS(hass=hass,pipeline=NS(id='p'),start_stage='stt',end_stage='tts',id='r',
                    tts_stream=None,start=lambda **kw:events.append('start'),end=end,process_event=events.append)
                value.session=NS(conversation_id='c');value.device_id='d';value.satellite_id='s'
                value.wake_word_phrase='Jarvis';value.stt_stream=object();value.stt_metadata=NS(sample_rate=16000)
                with self.assertRaises(type(error)):await value.execute(validate=True)
                self.assertEqual(events,['start','end'] if isinstance(error,asyncio.CancelledError) else ['start','error','end'])

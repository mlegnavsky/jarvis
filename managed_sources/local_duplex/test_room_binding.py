"""Exercise the production HA binding without a cloud or device connection."""
import asyncio
import ast
from dataclasses import asdict,dataclass,replace
from pathlib import Path
from types import SimpleNamespace as NS
import unittest
import time
import tempfile
from calibration import CalibrationManager

from adapter import DELEGATE,native_session
from room_measurement import reserved_marker
from room_measurement import RoomMeasurement
from room_native import NativeRoomLink


@dataclass
class AudioSettings:
    is_vad_enabled:bool=False
    auto_gain_dbfs:int=0
    noise_suppression_level:int=0


@dataclass
class Metadata:
    sample_rate:int=16000


class RoomBindingTests(unittest.IsolatedAsyncioTestCase):
    def app(self,**extra):
        tree=ast.parse(Path(__file__).with_name('__init__.py').read_text())
        cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='LocalDialogue')
        scope=dict(asyncio=asyncio,DELEGATE=DELEGATE,native_session=native_session,
            reserved_marker=reserved_marker,asdict=asdict,replace=replace,
            PipelineEvent=lambda kind,data=None:NS(type=kind,data=data),
            PipelineEventType=NS(RUN_START='run-start',RUN_END='run-end',STT_START='stt-start',INTENT_END='intent-end'),
            MicroVadSpeexEnhancer=lambda *args:NS(),prime_native_vad=lambda enhancer:(77,.01),
            PASSAGE='fixed story',release_prepared=None,SATELLITE_COMPONENT='satellites',
            AssistSatelliteEntityFeature=NS(START_CONVERSATION=1),
            SATELLITE='assist_satellite.home_assistant_voice_0a8bde_assist_satellite',
            MUTE='microphone_mute',PIPELINE='fixed_pipeline',AGENT='fixed_agent')
        scope.update(CORE_VERSION='2026.6.4',PipelineInput=object,
            operator_installed=lambda *args:True)
        scope.update(extra)
        exec(compile(ast.Module(body=[cls],type_ignores=[]),'production-dialogue','exec'),scope)
        app=object.__new__(scope['LocalDialogue']);app.room_measurement=None
        app.adapter='active';app.room_isolated=False
        return app

    def value(self):
        events=[]
        async def end():events.append(NS(type='run-end',data=None))
        def forbidden(**kwargs):raise AssertionError('Core recording/provider startup was called')
        async def source():yield bytes(320)
        run=NS(id='native',pipeline=NS(id='fixed_pipeline',stt_engine='fixed_stt'),language='cs',
            start_stage='stt',end_stage='tts',
            tts_stream=None,start=forbidden,end=end,process_event=events.append,
            audio_settings=AudioSettings(),process_enhance_audio=forbidden)
        return NS(run=run,conversation_extra_system_prompt='jarvis-room-test:'+'a'*32,
            session=NS(conversation_id='unique'),satellite_id='satellite',device_id='device',
            stt_stream=source(),stt_metadata=Metadata()),events

    async def test_late_reserved_pipeline_closes_without_core_recording_or_providers(self):
        app=self.app();self.assertTrue(hasattr(app,'operator_handle'),'fixed room operator binding missing')
        value,events=self.value()
        await app.operator_handle(value)
        self.assertEqual([e.type for e in events],['run-start','intent-end','run-end'])
        self.assertFalse(events[1].data['intent_output']['continue_conversation'])

    async def test_accepted_operator_taps_only_existing_native_source(self):
        app=self.app();self.assertTrue(hasattr(app,'operator_handle'),'fixed room operator binding missing')
        value,events=self.value();seen=[]
        async def capture(source,enhance):seen.append(await anext(source))
        app.room_measurement=NS(accepts=lambda marker:marker==value.conversation_extra_system_prompt,capture=capture)
        await app.operator_handle(value)
        self.assertEqual(seen,[bytes(320)])
        self.assertEqual([e.type for e in events],['run-start','stt-start','intent-end','run-end'])
        self.assertEqual(events[1].data['audio_processing'],
            {'prefers_auto_gain_enabled':False,'prefers_noise_reduction_enabled':False})

    async def test_ordinary_pipeline_is_not_treated_as_operator(self):
        app=self.app();self.assertTrue(hasattr(app,'operator_handle'),'fixed room operator binding missing')
        value,events=self.value();value.conversation_extra_system_prompt=None
        self.assertIs(await app.operator_handle(value),DELEGATE)
        self.assertEqual(events,[])

    async def test_isolation_blocks_missing_consumed_and_duplicate_markers(self):
        for phase in ('late_before_first_input','core_exception_cleared_marker','duplicate_after_first_input'):
            app=self.app();app.room_isolated=True
            value,events=self.value();value.conversation_extra_system_prompt=None
            self.assertIsNone(await app.operator_handle(value),phase)
            self.assertEqual([e.type for e in events],['run-start','intent-end','run-end'])

    async def test_changed_pipeline_with_valid_marker_is_closed_without_capture(self):
        app=self.app();app.room_isolated=True;value,events=self.value();value.run.pipeline.id='changed'
        async def forbidden(*args):raise AssertionError('changed pipeline must not capture')
        app.room_measurement=NS(accepts=lambda marker:True,capture=forbidden)
        await app.operator_handle(value)
        self.assertEqual([e.type for e in events],['run-start','intent-end','run-end'])

    async def test_partial_generated_resource_failure_releases_story_without_microphone(self):
        released=[]
        async def release(item):released.append(item)
        async def silent(*args):raise OSError('generated silent file failed')
        app=self.app(release_prepared=release,create_owned_file=silent,
            async_get_pipeline=lambda *args:NS(),SimpleNamespace=NS)
        self.assertTrue(hasattr(app,'prepare_room_test'),'bounded preparation missing')
        prepared=NS(pcm=bytes(32000))
        async def synthesize(*args):return prepared
        app.synthesize=synthesize;app.speech_files=object()
        app.hass=NS(async_add_executor_job=asyncio.to_thread)
        with self.assertRaises(OSError):await app.prepare_room_test()
        self.assertEqual(released,[prepared])

    async def test_muted_busy_or_other_selected_pipeline_blocks_remote_start(self):
        selected=NS(id='fixed_pipeline',conversation_engine='fixed_agent')
        app=self.app(async_get_pipeline=lambda *args:selected)
        self.assertTrue(hasattr(app,'room_test_ready'),'remote microphone preflight missing')
        entity=NS(available=True,supported_features=1,_pipeline_task=None,state='idle',_resolve_pipeline=lambda:None)
        mute=NS(state='off')
        app.hass=NS(data={'satellites':NS(get_entity=lambda _:entity)},states=NS(get=lambda _:mute))
        app.active=None;app.calibration=NS(state='off')
        app.ready=lambda:True;app.speech_ready=lambda:True;app.calibration_ready=lambda:True
        self.assertTrue(app.room_test_ready())
        for status in ('unsupported_core','already_installed','unknown'):
            app.adapter=status;self.assertFalse(app.room_test_ready())
        app.adapter='active'
        mute.state='on';self.assertFalse(app.room_test_ready());mute.state='off'
        entity._pipeline_task=object();self.assertFalse(app.room_test_ready());entity._pipeline_task=None
        selected.id='other';self.assertFalse(app.room_test_ready())

    async def test_foreign_activation_during_tv_acquire_aborts_test_before_cloud_validation(self):
        app=self.app(RoomMeasurement=RoomMeasurement,NativeRoomLink=NativeRoomLink,
            EVENT_CALL_SERVICE='call_service',TELEVISION='television',PLAYER='local_player',
            async_track_state_change_event=lambda *args:lambda:None)
        self.assertTrue(hasattr(app,'room_test'),'room test orchestration missing')
        acquired=asyncio.Event();released=[]
        async def acquire():acquired.set();await asyncio.Event().wait()
        async def release():released.append(True)
        television=NS(acquire=acquire,release=release,input_safe=lambda:True)
        app.probing=False;app.active=None;app.output=None;app.calibration=NS()
        app.lock=asyncio.Lock();app.report={}
        app.hass=NS(data={'satellites':NS(get_entity=lambda _:NS())},
            bus=NS(async_listen=lambda *args:lambda:None))
        app.player=lambda:None;app.television=lambda:television;app.room_test_ready=lambda:True
        async def save():pass
        app.save=save
        task=asyncio.create_task(app.room_test('a'*32,time.time()+60))
        try:
            await asyncio.wait_for(acquired.wait(),1)
            value,_events=self.value();value.conversation_extra_system_prompt=None
            self.assertIs(await app.operator_handle(value),DELEGATE)
            self.assertFalse(app.probing,'foreign input would enter maintenance and be dropped')
            self.assertEqual(released,[True])
        finally:
            task.cancel();await asyncio.gather(task,return_exceptions=True)

    async def test_persistent_isolation_releases_only_after_old_native_connection_is_gone(self):
        with tempfile.TemporaryDirectory() as root:
            async def execute(fn,*args):return await asyncio.to_thread(fn,*args)
            calibration=CalibrationManager(Path(root),execute)
            app=self.app();app.calibration=calibration
            self.assertTrue(hasattr(app,'isolate_room_test'),'durable isolation missing')
            await app.isolate_room_test()
            restored=self.app();restored.calibration=calibration
            await restored.restore_room_isolation()
            self.assertTrue(restored.room_isolated)
            old=NS(cli=NS(is_connected=True),available=True,state='idle')
            current=old
            restored.room_native_link=NS(entity=old,original_client=old.cli)
            restored.hass=NS(data={'satellites':NS(get_entity=lambda _:current)})
            restored.probing=False;restored.active=None
            self.assertFalse(await restored.release_room_isolation())
            current=NS(available=True,state='idle')
            self.assertFalse(await restored.release_room_isolation())
            old.cli.is_connected=False
            self.assertTrue(await restored.release_room_isolation())
            self.assertFalse(restored.room_isolated)
            self.assertFalse(calibration.store.read('room-test-isolation.json')['active'])
            await calibration.close()

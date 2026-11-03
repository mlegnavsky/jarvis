import asyncio
import ast
import importlib
from functools import partial
from pathlib import Path
from types import SimpleNamespace as NS
import unittest

HOME='media_player.homepod_obyvak_homepod_obyvak'
MEDIA='media-source://media_source/local/jarvis_speech/jarvis-'+'a'*32+'.wav'


class HomePodTests(unittest.IsolatedAsyncioTestCase):
    def module(self):return importlib.import_module('homepod_io')

    async def test_stream_uses_one_owned_native_connection_and_aborts_before_cancel(self):
        output=await self.output();events=[]
        reference=importlib.import_module('speech_stream').GrowingReference()
        reference.append(b'\x00\x10'*16000)
        class Prepared:
            def __init__(self):self.reference=reference;self.native=object()
            def abort(self):events.append('abort')
            async def release(self):events.append('release')
            async def wait_finished(self):pass
            def snapshot(self):return {'producer_done':False,'raw_microphone_saved':False}
            def raise_if_failed(self):pass
        prepared=Prepared()
        async def tts(text):return prepared
        async def stream_start(player,value,volume):
            self.assertIs(value,prepared);self.assertEqual(volume,.45)
            events.append('stream');self.started.set()
            try:await self.finish.wait()
            except asyncio.CancelledError:events.append('native_cancel');raise
        output.tts=tts;output.stream_start=stream_start
        task=asyncio.create_task(output.play('fixed'))
        await asyncio.wait_for(self.started.wait(),.2)
        self.assertIs(output.reference,reference)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):await task
        self.assertEqual(events.count('stream'),1)
        self.assertLess(events.index('abort'),events.index('native_cancel'))
        self.assertIn('release',events)

    async def test_stream_provider_uses_existing_entity_client_and_exact_voice_options(self):
        tree=ast.parse(Path(__file__).with_name('__init__.py').read_text())
        cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='LocalDialogue')
        captured=[]
        entity=NS(available=True,default_options={'voice':'marin'},subentry=NS(data={
            'chat_model':'existing-tts-model','prompt':'existing voice instructions','tts_speed':1.1}))
        def create(**kwargs):captured.append(kwargs);return 'same-client-context'
        entity.entry=NS(runtime_data=NS(audio=NS(speech=NS(with_streaming_response=NS(create=create)))))
        async def open_stream(factory,execute):return factory()
        scope={'tts':NS(DATA_COMPONENT='tts.component',ATTR_VOICE='voice'),
            'OpenAITTSEntity':type(entity),'open_speech_stream':open_stream,
            'CONF_CHAT_MODEL':'chat_model','CONF_TTS_SPEED':'tts_speed','RECOMMENDED_TTS_SPEED':1.,
            'CONF_PROMPT':'prompt','spoken_name':lambda x:x}
        exec(compile(ast.Module(body=[cls],type_ignores=[]),'production-dialogue','exec'),scope)
        app=object.__new__(scope['LocalDialogue'])
        app.hass=NS(data={'tts.component':NS(get_entity=lambda _id:entity)},async_add_executor_job=asyncio.to_thread)
        self.assertTrue(hasattr(app,'stream_speech'),'production streaming TTS factory missing')
        result=await app.stream_speech('test',NS(tts_engine='tts.openai_tts',tts_voice='marin'))
        self.assertEqual(result,'same-client-context')
        self.assertEqual(captured,[{'model':'existing-tts-model','voice':'marin','input':'test',
            'instructions':'existing voice instructions','speed':1.1,'response_format':'mp3'}])

    async def test_production_probe_measures_reference_without_opening_microphone(self):
        tree=ast.parse(Path(__file__).with_name('__init__.py').read_text())
        cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='LocalDialogue')
        released=[]
        async def release(prepared):released.append(prepared)
        scope={'asyncio':asyncio,'MicroVadSpeexEnhancer':lambda *args:object(),
            'prime_native_vad':lambda enhancer:(77,.01),'async_get_pipeline':lambda *args:NS(),
            'PIPELINE':'fixed','pipeline_signature':lambda pipeline:'signature',
            'release_prepared':release,'partial':partial,
            'measure_waveform':importlib.import_module('waveform_observer').measure_waveform}
        exec(compile(ast.Module(body=[cls],type_ignores=[]),'production-dialogue','exec'),scope)
        app=object.__new__(scope['LocalDialogue']);app.probing=False;app.report={};app.source_revision='native-source'
        async def execute(func,*args):return func(*args)
        app.hass=NS(async_add_executor_job=execute)
        prepared=NS(pcm=importlib.import_module('test_waveform_observer').shaped(13,3),signal={'silent':False})
        async def synthesize(text,pipeline):return prepared
        async def save():pass
        app.synthesize=synthesize;app.save=save
        await app.probe()
        proof=app.report['self_test']
        self.assertEqual(proof['status'],'passed')
        self.assertIn('waveform_probe',proof)
        self.assertEqual(proof['waveform_probe']['status'],'measured')
        self.assertEqual(proof['waveform_probe']['offset_ms'],1250)
        self.assertFalse(proof['microphone_opened'])
        self.assertFalse(proof['audible_playback'])
        self.assertEqual(released,[prepared])
        async def unavailable(func,*args):raise TimeoutError('executor unavailable')
        app.hass.async_add_executor_job=unavailable
        await app.probe()
        self.assertEqual(app.report['self_test']['status'],'passed')
        self.assertEqual(app.report['self_test']['waveform_probe']['status'],'unavailable')
        self.assertEqual(len(released),2)

    async def test_output_reports_synthesis_and_first_audio_wait_separately(self):
        output=await self.output();original=output.tts
        async def tts(text):self.time+=.3;return await original(text)
        output.tts=tts
        task=asyncio.create_task(output.play('fixed'));await self.started.wait()
        for _ in range(3):await asyncio.sleep(0)
        facts=output.snapshot()
        self.assertEqual(facts['tts_generation_ms'],300.)
        self.assertGreater(facts['first_audio_wait_ms'],0.)
        self.assertAlmostEqual(facts['first_audio_wait_ms'],(output.started_at-.3)*1000,places=1)
        task.cancel();await asyncio.gather(task,return_exceptions=True)

    async def test_production_output_factory_routes_only_to_homepod(self):
        tree=ast.parse(Path(__file__).with_name('__init__.py').read_text())
        cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='LocalDialogue')
        targets=[];player=NS(entity_id=HOME,available=True,state='off')
        async def start(player,media,volume):targets.append(player.entity_id);await asyncio.sleep(.04)
        state=lambda _player:{'volume':.45,'muted':False,'source':'raop','busy':False}
        timing=lambda _player:{'position_s':.1,'latency_s':0.}
        scope={'HomePodOutput':self.module().HomePodOutput,'homepod_state':state,
            'play_homepod_file':start,'homepod_timing':timing}
        exec(compile(ast.Module(body=[cls],type_ignores=[]),'production-dialogue','exec'),scope)
        app=object.__new__(scope['LocalDialogue']);app.homepod=lambda:player
        app.player=lambda:self.fail('Voice PE is microphone only, never the speech destination')
        app.report={'homepod_startup':{'status':'applied'}}
        async def synthesize(text,pipeline):return NS(media_id=MEDIA,pcm=b'\x00\x20'*16000)
        app.synthesize=synthesize
        output=app.make_output(NS(),streaming=False)
        await output.play('fixed')
        self.assertEqual(targets,[HOME])

    async def test_eager_startup_busy_cannot_schedule_duplicate_initialization(self):
        tree=ast.parse(Path(__file__).with_name('__init__.py').read_text())
        cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='LocalDialogue')
        retry_error=getattr(self.module(),'HomePodNotReady',ValueError)
        async def busy(_player):raise retry_error('homepod_already_playing')
        scope={'asyncio':asyncio,'prime_homepod':busy,'HomePodNotReady':retry_error}
        exec(compile(ast.Module(body=[cls],type_ignores=[]),'production-dialogue','exec'),scope)
        app=object.__new__(scope['LocalDialogue']);app.homepod=lambda:NS(available=True)
        app.homepod_init_task=None;app.homepod_initializing=False
        app.report={'homepod_startup':{'status':'pending'}};calls=[]
        loop=asyncio.get_running_loop();previous=loop.get_task_factory()
        def create(coro):
            calls.append(True)
            if len(calls)>1:
                coro.close();done=loop.create_future();done.set_result(None);return done
            return asyncio.create_task(coro)
        app.hass=NS(async_create_task=create)
        async def save():app.schedule_homepod_initialization()
        app.save=save
        try:
            loop.set_task_factory(asyncio.eager_task_factory)
            self.assertFalse(await app.ensure_homepod_initialized())
            self.assertEqual(len(calls),1)
        finally:loop.set_task_factory(previous)

    async def test_startup_disconnected_retries_after_connect_and_only_primes_once(self):
        module=self.module();tree=ast.parse(Path(__file__).with_name('__init__.py').read_text())
        cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='LocalDialogue')
        async def prime(player):return await module.prime_homepod(player,protocol='raop')
        scope={'asyncio':asyncio,'prime_homepod':prime,'HomePodNotReady':getattr(module,'HomePodNotReady',ValueError)}
        exec(compile(ast.Module(body=[cls],type_ignores=[]),'production-dialogue','exec'),scope)
        app=object.__new__(scope['LocalDialogue']);connected,audio,calls=self.native();audio.volume=33.
        player=NS(entity_id=HOME,available=True,atv=None)
        app.homepod=lambda:player;app.homepod_init_task=None;app.homepod_initializing=False
        app.report={'homepod_startup':{'status':'pending'}};app.hass=NS(async_create_task=asyncio.create_task)
        async def save():return None
        app.save=save
        self.assertFalse(await app.ensure_homepod_initialized())
        player.atv=connected.atv
        self.assertTrue(await app.ensure_homepod_initialized())
        self.assertTrue(await app.ensure_homepod_initialized())
        self.assertEqual(calls,[('volume',45.)])

    async def test_disowned_task_finishes_cleanup_before_parent_releases_speech_file(self):
        output=await self.output();cleanup=asyncio.Event();finish_cleanup=asyncio.Event();released=[]
        async def start(player,media,volume):
            self.started.set()
            try:await asyncio.Event().wait()
            finally:cleanup.set();await finish_cleanup.wait()
        async def release():released.append(True)
        async def tts(text):return NS(media_id=MEDIA,pcm=b'\x00\x20'*16000,release=release)
        output.start=start;output.tts=tts
        task=asyncio.create_task(output.play('fixed'));await self.started.wait();output.disown();await cleanup.wait()
        output.disown()  # A second foreign HA command must not cancel RTSP cleanup again.
        try:
            for _ in range(10):await asyncio.sleep(0)
            self.assertFalse(task.done())
            self.assertEqual(released,[])
        finally:
            finish_cleanup.set();await asyncio.gather(task,return_exceptions=True)
        self.assertTrue(output.native_task.done());self.assertEqual(released,[True])

    async def test_stop_timeout_retains_file_until_native_cleanup_finishes(self):
        output=await self.output();output.stop_timeout=.02
        cleanup=asyncio.Event();finish_cleanup=asyncio.Event();released=[]
        async def start(player,media,volume):
            self.started.set()
            try:await asyncio.Event().wait()
            finally:cleanup.set();await finish_cleanup.wait()
        async def release():released.append(True)
        async def tts(text):return NS(media_id=MEDIA,pcm=b'\x00\x20'*16000,release=release)
        output.start=start;output.tts=tts
        task=asyncio.create_task(output.play('fixed'));await self.started.wait()
        try:
            with self.assertRaises(TimeoutError):await output.stop()
            await asyncio.gather(task,return_exceptions=True)
            self.assertFalse(output.native_task.done())
            self.assertEqual(released,[])
        finally:
            finish_cleanup.set();await asyncio.gather(output.native_task,return_exceptions=True)
            for _ in range(10):await asyncio.sleep(0)
        self.assertEqual(released,[True])

    def native(self):
        calls=[]
        async def set_volume(level):calls.append(('volume',level));audio.volume=level
        audio=NS(volume=0.,set_volume=set_volume,playback_manager=NS(_is_acquired=False,stream_client=None))
        async def play(kind,media):calls.append(('play',kind,media))
        player=NS(entity_id=HOME,available=True,state='off',is_volume_muted=False,volume_level=0.,
            atv=NS(audio=NS(_interfaces={'raop':audio})),async_play_media=play)
        return player,audio,calls

    async def test_exact_homepod_native_volume_and_complete_file_only(self):
        io=self.module();player,audio,calls=self.native()
        await io.prime_homepod(player,protocol='raop')
        self.assertEqual(calls,[('volume',45.)])
        self.assertAlmostEqual(io.homepod_state(player,protocol='raop')['volume'],.45)
        await io.play_homepod_file(player,MEDIA,.45,protocol='raop')
        self.assertEqual(calls[-2:],[('volume',45.),('play','music',MEDIA)])
        before=list(calls)
        with self.assertRaises(ValueError):await io.play_homepod_file(player,'https://private/tts.mp3',.45,protocol='raop')
        player.entity_id='media_player.other'
        with self.assertRaises(ValueError):await io.prime_homepod(player,protocol='raop')
        self.assertEqual(calls,before)

    def test_tv_zero_and_mute_cannot_silence_homepod_speech(self):
        io=self.module();player,audio,_=self.native();audio.volume=45.
        decision=io.homepod_state(player,{'volume':0.,'muted':True},protocol='raop')
        self.assertEqual((decision['volume'],decision['muted'],decision['source']),(.45,False,'raop'))
        manager=audio.playback_manager
        self.assertIsNone(io.homepod_timing(player,protocol='raop'))
        manager.stream_client=NS(playback_info=NS(position=.2))
        manager.context=NS(sample_rate=44100,latency=88200)
        self.assertEqual(io.homepod_timing(player,protocol='raop'),{'position_s':.2,'latency_s':2.})

    async def output(self,*,zero=False):
        module=self.module();self.commands=[];self.time=0.;self.finish=asyncio.Event();self.started=asyncio.Event()
        self.player=NS(entity_id=HOME,available=True,state='off')
        async def tts(text):return NS(media_id=MEDIA,pcm=b'\x00\x20'*16000)
        async def start(player,media,level):
            self.commands.append((player.entity_id,media,level));self.started.set();await self.finish.wait()
        def timing(player):return {'position_s':.1,'latency_s':2.} if self.started.is_set() else None
        def state(player):return {'volume':0. if zero else .45,'muted':False,'source':'raop','busy':False}
        async def wait(seconds):self.time+=seconds;await asyncio.sleep(0)
        return module.HomePodOutput(lambda:self.player,tts,start,state,timing,clock=lambda:self.time,sleep=wait)

    async def test_awaits_native_file_end_and_uses_negotiated_latency(self):
        output=await self.output();task=asyncio.create_task(output.play('fixed'))
        await self.started.wait()
        for _ in range(3):await asyncio.sleep(0)
        self.assertFalse(task.done());self.assertEqual(output.completed,0)
        self.assertFalse(output.playing())
        self.assertGreater(output.started_at,self.time)
        self.finish.set();await task
        self.assertEqual(output.completed,1)
        self.assertEqual(self.commands,[(HOME,MEDIA,.45)])

    async def test_zero_skips_and_cancel_drains_only_own_native_task(self):
        output=await self.output(zero=True);await output.play('fixed');self.assertEqual(self.commands,[])
        output=await self.output();task=asyncio.create_task(output.play('fixed'))
        await self.started.wait();task.cancel()
        with self.assertRaises(asyncio.CancelledError):await task
        self.assertTrue(output.native_task.done())
        self.assertEqual(output.stopped,1)

    async def test_airplay_buffering_does_not_mark_microphone_as_playback_overlap(self):
        output=await self.output();output.owned=True;output.started_at=2.
        segmenter=importlib.import_module('segmenter')
        output.reference=segmenter.EchoReference(b'\x00\x20'*16000)
        frame=NS(audio=bytes(320),speech_probability=.99)
        qualified=output.gate(frame,NS(segmenter=segmenter.Segmenter()))
        self.assertEqual(qualified,[(frame.audio,.99)])
        self.assertEqual(output.overlap_frames,0)

    async def test_external_disown_cancels_old_task_without_any_generic_stop(self):
        output=await self.output();task=asyncio.create_task(output.play('fixed'))
        await self.started.wait();output.disown();await output.stop()
        with self.assertRaises(asyncio.CancelledError):await task
        self.assertEqual(output.stopped,0)
        self.assertEqual(len(self.commands),1)

    async def test_homepod_echo_uses_full_reference_window_before_classification(self):
        output=await self.output();output.owned=True;output.started_at=0.
        segmenter=importlib.import_module('segmenter');output.reference=segmenter.EchoReference(b'\x00\x20'*16000)
        session=NS(segmenter=segmenter.Segmenter())
        frame=NS(audio=bytes(320),speech_probability=.99)
        for _ in range(39):self.assertEqual(output.gate(frame,session),[])
        self.assertEqual(len(output.gate(frame,session)),40)

    async def test_cancel_tail_covers_native_queued_audio_latency(self):
        output=await self.output();task=asyncio.create_task(output.play('fixed'))
        await self.started.wait()
        for _ in range(3):await asyncio.sleep(0)
        await output.stop();await asyncio.gather(task,return_exceptions=True)
        self.assertGreaterEqual(output.tail_until-output.clock(),output.latency_s+.4-1e-8)

    async def test_normal_completion_keeps_same_delayed_echo_tail(self):
        output=await self.output();task=asyncio.create_task(output.play('Co pro tebe můžu udělat?'))
        await self.started.wait()
        for _ in range(3):await asyncio.sleep(0)
        self.time=5.;self.finish.set();await task
        self.assertGreaterEqual(output.tail_until-output.clock(),output.latency_s+.4-1e-8)

    async def test_remembered_own_question_covers_delayed_capture_after_end(self):
        output=await self.output();output.started_at=10.;output.latency_s=1.5
        output.last_reference_duration_s=3.;output.pending_text='Co pro tebe můžu udělat?'
        output.remember_speech()
        self.assertTrue(output.is_own_transcript('Co pro tebe můžu udělat?',bytes(32000),14.4))
        self.assertFalse(output.is_own_transcript('Ano',bytes(32000),14.4))

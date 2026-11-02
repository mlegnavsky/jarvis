import asyncio
import ast
import importlib
from pathlib import Path
from types import SimpleNamespace as NS
import unittest

HOME='media_player.homepod_obyvak_homepod_obyvak'
MEDIA='media-source://media_source/local/jarvis_speech/jarvis-'+'a'*32+'.wav'


class HomePodTests(unittest.IsolatedAsyncioTestCase):
    def module(self):return importlib.import_module('homepod_io')

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
        output=app.make_output(NS())
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

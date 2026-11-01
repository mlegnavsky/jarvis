"""Concurrent capture, response ownership and bounded turn behavior."""
import asyncio
import importlib
from types import SimpleNamespace as NS
import unittest


class SessionTests(unittest.IsolatedAsyncioTestCase):
    def session(self, **overrides):
        module=importlib.import_module('session')
        self.calls=[];self.playing=asyncio.Event();self.finish=asyncio.Event()
        async def transcribe(audio,voiced,truncated):
            self.calls.append(('stt',audio));return 'nová věta'
        async def respond(text):return NS(speech=text,continuing=True)
        async def play(text):
            self.calls.append(('play',text));self.playing.set();await self.finish.wait()
        async def stop():self.calls.append(('stop',))
        return module.Session(transcribe=overrides.get('transcribe',transcribe),respond=overrides.get('respond',respond),
            play=overrides.get('play',play),stop=overrides.get('stop',stop),idle_seconds=5,
            on_interrupt=overrides.get('on_interrupt'),
            input_timeout_seconds=overrides.get('input_timeout_seconds',5))

    async def test_failed_stop_still_drains_cancelled_response(self):
        drained=asyncio.Event()
        async def play(text):
            self.playing.set()
            try:await asyncio.Event().wait()
            finally:
                await asyncio.sleep(0)
                drained.set()
        async def stop():raise ValueError('stop_unconfirmed')
        session=self.session(play=play,stop=stop)
        await session.submit(b'a',1,False);await self.playing.wait()
        with self.assertRaises(ValueError):await session.interrupt()
        self.assertTrue(drained.is_set())
        with self.assertRaises(ValueError):await session.close()

    async def test_playback_timeout_cannot_leave_owned_audio_running(self):
        module=importlib.import_module('ha_io');stops=[]
        player=NS(state='idle',available=True,is_volume_muted=False,volume_level=.4)
        async def tts(text):return NS(media_id='own',pcm=bytes(32000))
        async def start(player,media):player.state='playing'
        async def stop(player):stops.append(True);player.state='idle'
        async def sleep(seconds):await asyncio.Event().wait()
        output=module.LocalOutput(lambda:player,tts,start,stop,sleep=sleep)
        async def timed_play(text):
            async with asyncio.timeout(.02):await output.play(text)
        session=self.session(play=timed_play,stop=output.stop)
        await session.submit(b'a',1,False);await session.task
        self.assertEqual(session.stage,'idle')
        self.assertEqual(session.last_error,'TimeoutError')
        self.assertFalse(output.owned)
        self.assertEqual(stops,[True])
        await session.close()

    async def test_stalled_native_input_closes_without_session_limit_wait(self):
        session=self.session(input_timeout_seconds=.02)
        async def frames():
            yield NS(audio=bytes(320),speech_probability=0)
            await asyncio.Event().wait()
        async with asyncio.timeout(.5):await session.run(frames())
        self.assertEqual(session.reason,'audio_source_stalled')
        self.assertEqual(session.stage,'closed')

    async def test_interrupt_notifies_context_before_new_turn(self):
        notified=[];session=self.session(on_interrupt=lambda:notified.append(True))
        await session.submit(b'a',1,False);await self.playing.wait();await session.interrupt()
        self.assertEqual(notified,[True]);await session.close()

    async def test_uncancelled_tts_cannot_dispatch_stale_audio(self):
        output_module=importlib.import_module('ha_io');entered=asyncio.Event();sent=[]
        player=NS(state='idle',available=True,is_volume_muted=False,volume_level=.4)
        async def tts(text):
            entered.set()
            try:await asyncio.Event().wait()
            except asyncio.CancelledError:asyncio.current_task().uncancel()
            return NS(media_id='stale',pcm=bytes(32000))
        async def start(player,media):sent.append(media);player.state='playing'
        async def stop(player):player.state='idle'
        async def sleep(seconds):player.state='idle';await asyncio.sleep(0)
        output=output_module.LocalOutput(lambda:player,tts,start,stop,sleep=sleep)
        session=self.session(play=output.play,stop=output.stop)
        await session.submit(b'a',1,False);await entered.wait();await session.interrupt()
        self.assertEqual(sent,[]);await session.close()

    async def test_new_speech_stops_owned_playback_before_new_turn(self):
        session=self.session()
        await session.submit(b'first',1,False)
        await self.playing.wait()
        await session.interrupt()
        self.assertIn(('stop',),self.calls)
        self.assertTrue(session.task is None or session.task.done())
        self.assertEqual(session.snapshot()['interruptions'],1)
        await session.close()

    async def test_interrupt_during_model_work_never_plays_stale_result(self):
        model=asyncio.Event()
        async def respond(text):model.set();await asyncio.Event().wait()
        session=self.session(respond=respond)
        await session.submit(b'first',1,False);await model.wait()
        await session.interrupt()
        self.assertFalse(any(c[0]=='play' for c in self.calls))
        await session.close()

    async def test_response_which_ignores_cancel_cannot_play_later(self):
        entered=asyncio.Event()
        async def respond(text):
            entered.set()
            try:await asyncio.Event().wait()
            except asyncio.CancelledError:return NS(speech='old',continuing=True)
        session=self.session(respond=respond)
        await session.submit(b'old',1,False);await entered.wait();await session.interrupt()
        self.assertNotIn(('play','old'),self.calls)
        await session.close()

    async def test_silent_light_action_finishes_without_playback(self):
        async def respond(text):return NS(speech='',continuing=False)
        session=self.session(respond=respond)
        await session.submit(b'light',.2,False);await session.task
        self.assertTrue(session.done)
        self.assertFalse(any(c[0]=='play' for c in self.calls))
        await session.close()

    async def test_truncated_utterance_never_reaches_agent(self):
        session=self.session()
        await session.submit(b'partial',30,True)
        if session.task:await session.task
        self.assertFalse(any(c[0]=='stt' for c in self.calls))
        await session.close()

    async def test_close_drains_response_and_stops_owned_output(self):
        session=self.session();await session.submit(b'a',1,False);await self.playing.wait()
        await session.close()
        self.assertEqual(session.snapshot()['stage'],'closed')
        self.assertIn(('stop',),self.calls)

    async def test_provider_failure_is_reported_and_no_success_is_invented(self):
        async def transcribe(*args):raise RuntimeError('PRIVATE provider details')
        session=self.session(transcribe=transcribe)
        await session.submit(b'a',1,False);await session.task
        self.assertEqual(session.snapshot()['last_error'],'RuntimeError')
        self.assertNotIn('PRIVATE',str(session.snapshot()))
        self.assertFalse(any(c[0]=='play' for c in self.calls))
        await session.close()

    async def test_missing_transcript_does_not_end_or_respond(self):
        async def transcribe(*args):return ''
        session=self.session(transcribe=transcribe)
        await session.submit(b'noise',.1,False);await session.task
        self.assertFalse(session.done)
        self.assertEqual(session.snapshot()['completed_turns'],0)
        await session.close()

    async def test_capture_keeps_running_while_playback_is_waiting(self):
        session=self.session();queue=asyncio.Queue();source_closed=asyncio.Event()
        async def frames():
            try:
                while True:
                    frame=await queue.get()
                    if frame is None:return
                    yield frame
            finally:source_closed.set()
        running=asyncio.create_task(session.run(frames()))
        for _ in range(20):await queue.put(NS(audio=bytes(320),speech_probability=.99))
        for _ in range(75):await queue.put(NS(audio=bytes(320),speech_probability=0))
        async with asyncio.timeout(2):await self.playing.wait()
        before=session.frames
        for _ in range(25):await queue.put(NS(audio=bytes(320),speech_probability=0))
        for _ in range(10):await asyncio.sleep(0)
        self.assertGreater(session.frames,before)
        self.assertGreater(session.frames_during_output,0)
        session.request_close('muted')
        async with asyncio.timeout(2):await running
        self.assertTrue(source_closed.is_set())
        self.assertIn(('stop',),self.calls)

    async def test_audio_source_end_cleans_independent_playback(self):
        session=self.session();queue=asyncio.Queue()
        async def frames():
            while (frame:=await queue.get()) is not None:yield frame
        running=asyncio.create_task(session.run(frames()))
        for _ in range(20):await queue.put(NS(audio=bytes(320),speech_probability=.99))
        for _ in range(75):await queue.put(NS(audio=bytes(320),speech_probability=0))
        async with asyncio.timeout(2):await self.playing.wait()
        await queue.put(None)
        async with asyncio.timeout(2):await running
        self.assertEqual(session.stage,'closed')
        self.assertIn(('stop',),self.calls)

    async def test_second_utterance_cancels_first_playback_without_stopping_capture(self):
        turns=[]
        async def respond(text):
            turns.append(text);return NS(speech='answer',continuing=True)
        session=self.session(respond=respond);queue=asyncio.Queue()
        async def frames():
            while (frame:=await queue.get()) is not None:yield frame
        running=asyncio.create_task(session.run(frames()))
        for _ in range(20):await queue.put(NS(audio=bytes(320),speech_probability=.99))
        for _ in range(75):await queue.put(NS(audio=bytes(320),speech_probability=0))
        async with asyncio.timeout(2):await self.playing.wait()
        for _ in range(25):await queue.put(NS(audio=bytes(320),speech_probability=.99))
        for _ in range(75):await queue.put(NS(audio=bytes(320),speech_probability=0))
        async with asyncio.timeout(2):
            while len(turns)<2:await asyncio.sleep(0)
        self.assertIn(('stop',),self.calls)
        self.assertGreaterEqual(session.interruptions,1)
        session.request_close('test_end');await running

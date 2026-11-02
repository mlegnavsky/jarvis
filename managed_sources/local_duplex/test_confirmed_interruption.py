"""Rejected microphone input must never cancel an already speaking answer."""
import asyncio
import importlib
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch


class ConfirmedInterruptionTests(unittest.IsolatedAsyncioTestCase):
    async def start(self, candidate):
        self.calls=[];self.playing=asyncio.Event();self.release=asyncio.Event()
        self.checked=asyncio.Event();self.allow_check=asyncio.Event()
        async def transcribe(audio,voiced,truncated):
            self.calls.append(('stt',audio))
            if audio==b'first':return 'příběh'
            self.checked.set();await self.allow_check.wait()
            if isinstance(candidate,Exception):raise candidate
            return candidate[audio] if isinstance(candidate,dict) else candidate
        async def respond(text):
            self.calls.append(('agent',text));return NS(speech='odpověď '+text,continuing=True)
        async def play(text):
            self.calls.append(('play',text));self.playing.set();await self.release.wait()
        async def stop():self.calls.append(('stop',))
        self.session=importlib.import_module('session').Session(
            transcribe=transcribe,respond=respond,play=play,stop=stop)
        self.addAsyncCleanup(self.session.close)
        await self.session.submit(b'first',1,False);await self.playing.wait()
        self.original=self.session.task

    async def wait_confirmation(self):
        async with asyncio.timeout(1):await self.checked.wait()
        for _ in range(3):await asyncio.sleep(0)

    async def settle(self):
        for _ in range(30):await asyncio.sleep(0)

    async def test_rejected_echo_never_stops_original_output(self):
        await self.start('')
        await self.session.submit(b'echo',1,False);await self.wait_confirmation()
        self.assertFalse(self.original.done())
        self.assertNotIn(('stop',),self.calls)
        self.allow_check.set();await self.settle()
        self.assertFalse(self.original.done())
        self.assertEqual(self.session.interruptions,0)
        self.assertEqual([x for x in self.calls if x[0]=='agent'],[('agent','příběh')])
        self.release.set();await self.original
        self.assertEqual(self.session.completed_turns,1)

    async def test_human_confirmation_stops_after_stt_once_and_keeps_session_open(self):
        await self.start('kolik je hodin')
        await self.session.submit(b'human',1,False);await self.wait_confirmation()
        self.assertNotIn(('stop',),self.calls)
        self.allow_check.set();await self.settle()
        self.assertEqual(self.session.interruptions,1)
        self.assertEqual(self.calls.count(('stt',b'human')),1)
        self.assertIn(('agent','kolik je hodin'),self.calls)
        self.assertFalse(self.session.closed)

    async def test_onset_and_candidate_stt_do_not_block_native_capture(self):
        await self.start('');queue=asyncio.Queue()
        async def frames():
            while (item:=await queue.get()) is not None:yield item
        running=asyncio.create_task(self.session.run(frames()))
        self.addAsyncCleanup(self.finish_reader,running)
        for _ in range(20):await queue.put(NS(audio=bytes(320),speech_probability=.99))
        for _ in range(75):await queue.put(NS(audio=bytes(320),speech_probability=0))
        await self.wait_confirmation()
        for _ in range(100):await queue.put(NS(audio=bytes(320),speech_probability=0))
        async with asyncio.timeout(1):
            while self.session.frames<195:await asyncio.sleep(0)
        self.assertEqual(self.session.interruptions,0)
        self.assertNotIn(('stop',),self.calls)
        self.assertFalse(self.original.done())

    async def finish_reader(self,running):
        self.session.request_close('test');await running

    async def test_explicit_interrupt_cancels_confirmation_without_late_new_turn(self):
        await self.start('late action')
        await self.session.submit(b'human',1,False);await self.wait_confirmation()
        await self.session.interrupt()
        self.allow_check.set();await self.settle()
        self.assertNotIn(('agent','late action'),self.calls)

    async def test_confirmation_failure_does_not_stop_answer(self):
        await self.start(ValueError('private provider detail'))
        await self.session.submit(b'noise',1,False);await self.wait_confirmation()
        self.allow_check.set();await self.settle()
        self.assertFalse(self.original.done())
        self.assertNotIn(('stop',),self.calls)
        self.assertNotIn('private',str(self.session.snapshot()))

    async def test_natural_output_end_during_confirmation_keeps_human_turn(self):
        await self.start('nová otázka')
        await self.session.submit(b'human',1,False);await self.wait_confirmation()
        self.assertFalse(self.original.done())
        self.release.set();await self.original
        self.allow_check.set();await self.settle()
        self.assertIn(('agent','nová otázka'),self.calls)
        self.assertEqual(self.calls.count(('stt',b'human')),1)

    async def test_newer_completed_utterance_supersedes_pending_confirmation(self):
        await self.start('old action')
        await self.session.submit(b'old',1,False);await self.wait_confirmation()
        await self.session.submit(b'correction',1,False)
        self.allow_check.set();await self.settle()
        self.assertNotIn(('agent','old action'),self.calls)
        self.assertFalse(self.original.done())

    async def test_stale_candidate_after_slow_stop_cannot_invoke_agent(self):
        await self.start('late action');clock=[10.]
        self.session.clock=lambda:clock[0]
        async def stop():self.calls.append(('stop',));clock[0]=16.
        self.session.stop=stop
        await self.session.submit(b'human',1,False,captured_until=10.)
        await self.wait_confirmation();self.allow_check.set();await self.settle()
        self.assertNotIn(('agent','late action'),self.calls)

    async def test_newer_candidate_is_checked_while_original_answer_still_plays(self):
        await self.start({b'old':'old action',b'correction':'nová otázka'})
        await self.session.submit(b'old',1,False);await self.wait_confirmation()
        await self.session.submit(b'correction',1,False)
        self.allow_check.set();await self.settle()
        queue=asyncio.Queue()
        async def frames():
            while (item:=await queue.get()) is not None:yield item
        running=asyncio.create_task(self.session.run(frames()))
        self.addAsyncCleanup(self.finish_reader,running)
        await queue.put(NS(audio=bytes(320),speech_probability=0));await self.settle()
        self.assertNotIn(('agent','old action'),self.calls)
        self.assertIn(('agent','nová otázka'),self.calls)
        self.assertEqual(self.calls.count(('stt',b'correction')),1)

    async def test_correction_during_slow_stop_prevents_older_action(self):
        await self.start({b'old':'old action',b'correction':'nová otázka'})
        stopping=asyncio.Event();release_stop=asyncio.Event()
        async def stop():stopping.set();await release_stop.wait()
        self.session.stop=stop
        self.addCleanup(release_stop.set)
        await self.session.submit(b'old',1,False);await self.wait_confirmation()
        self.allow_check.set()
        async with asyncio.timeout(1):await stopping.wait()
        await self.session.submit(b'correction',1,False)
        release_stop.set();await self.settle()
        self.assertNotIn(('agent','old action'),self.calls)

    async def test_source_eof_cancels_candidate_before_late_provider_result(self):
        await self.start('late action')
        await self.session.submit(b'human',1,False);await self.wait_confirmation()
        async def frames():
            if False:yield None
        await self.session.run(frames())
        self.allow_check.set();await self.settle()
        self.assertEqual(self.session.reason,'audio_source_ended')
        self.assertTrue(self.session.closed)
        self.assertNotIn(('agent','late action'),self.calls)

    async def test_explicit_stop_reaches_output_before_slow_stt_cleanup(self):
        await self.start('late action');cleanup=asyncio.Event();entered=asyncio.Event()
        async def transcribe(*args):
            entered.set()
            try:await asyncio.Event().wait()
            except asyncio.CancelledError:await cleanup.wait();return 'late action'
        self.session.transcribe=transcribe
        await self.session.submit(b'human',1,False)
        async with asyncio.timeout(1):await entered.wait()
        native_timeout=asyncio.timeout
        with patch('session.asyncio.timeout',lambda seconds:native_timeout(.01 if seconds==3 else seconds)):
            try:await self.session.interrupt()
            except TimeoutError:pass
        cleanup.set()
        self.assertTrue(self.original.done())
        self.assertIn(('stop',),self.calls)
        self.assertNotIn(('agent','late action'),self.calls)

    async def test_real_text_echo_guard_rejects_own_question_before_stop(self):
        echo=importlib.import_module('text_echo').TextEcho()
        echo.remember('Co pro tebe můžu udělat?',started_at=10.,duration=4.,tail=.4)
        clock=[11.5];agents=[];stops=[];playing=asyncio.Event();release=asyncio.Event()
        async def transcriber(audio):return 'příběh' if audio==b'first' else 'Co pro tebe mohu udělat?'
        async def complete(*args,**kwargs):pass
        async def converse(**kwargs):
            agents.append(kwargs['text'])
            return NS(conversation_id='conversation',continue_conversation=True,
                response=NS(as_dict=lambda:{'speech':{'plain':{'speech':'Co pro tebe můžu udělat?'}},'response_type':'query_answer'}))
        bridge=importlib.import_module('bridge').TurnBridge(transcriber,complete,converse,
            context_factory=lambda:NS(id='context'),device_id='device',satellite_id='satellite',
            conversation_id='conversation',agent_id='agent',language='cs',clock=lambda:clock[0],
            transcript_filter=lambda text,audio,at:'' if echo.matches(text,
                captured_from=at-len(audio)/32000,captured_until=at) else text)
        async def play(text):playing.set();await release.wait()
        async def stop():stops.append(True)
        session=importlib.import_module('session').Session(transcribe=bridge.transcribe,
            respond=bridge.respond,play=play,stop=stop,on_capture=bridge.set_capture_time,
            clock=lambda:clock[0],on_interrupt=bridge.interrupted)
        self.addAsyncCleanup(session.close)
        await session.submit(b'first',1,False);await playing.wait()
        original=session.task
        await session.submit(bytes(32000),.7,False,captured_until=11.5)
        await self.settle()
        self.assertEqual(stops,[])
        self.assertFalse(original.done())
        self.assertEqual(agents,['příběh'])
        self.assertFalse(bridge.interruption_pending)
        release.set();await original

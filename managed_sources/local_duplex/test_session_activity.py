"""Valid dialogue activity renews its watchdog; rejected input cannot."""
import asyncio
import time
from types import SimpleNamespace as NS
import unittest
from session import Session


class SessionActivityTests(unittest.IsolatedAsyncioTestCase):
    async def test_interrupted_valid_turns_cannot_bypass_existing_turn_budget(self):
        accepted=[]
        session=self.make_session();session.max_turns=2
        original_respond=session.respond
        async def respond(text):
            accepted.append(text)
            return await original_respond(text)
        session.respond=respond
        await session.submit(b'first',1,False);await self.started.wait()
        for index in range(2):
            self.now+=1
            await session.submit(b'next',1,False)
            await session.confirmation_task
            for _ in range(5):await asyncio.sleep(0)
        try:
            self.assertEqual(len(accepted),2)
            self.assertTrue(session.done)
            self.assertEqual(session.reason,'turn_limit')
        finally:await session.close()

    def make_session(self, transcribe=None, clock=None):
        self.now=0.;self.started=asyncio.Event();self.ends=asyncio.Event()
        async def stt(*_args):return 'human request'
        async def respond(text):return NS(speech=text,continuing=True)
        async def play(text):self.started.set();await self.ends.wait()
        async def stop():pass
        return Session(transcribe=transcribe or stt,respond=respond,play=play,
            stop=stop,clock=clock or (lambda:self.now),idle_seconds=1000)

    async def test_valid_turn_renews_budget_beyond_original_wall_age(self):
        session=self.make_session()
        observed=[]
        async def frames():
            self.now=1.;yield NS(audio=bytes(320),speech_probability=0.)
            self.now=180.
            await session.submit(b'voice',1,False);await self.started.wait()
            for at in (239.,241.,300.):
                self.now=at;yield NS(audio=bytes(320),speech_probability=0.)
                observed.append((at,session.done))
        await session.run(frames())
        self.assertIn((300.,False),observed)
        self.assertEqual(session.reason,'audio_source_ended')

    async def test_confirmed_human_turn_renews_activity_budget(self):
        session=self.make_session()
        observed=[]
        async def frames():
            self.now=1.
            await session.submit(b'first',1,False);await self.started.wait()
            yield NS(audio=bytes(320),speech_probability=0.)
            self.now=220.
            await session.submit(b'second',1,False)
            await session.confirmation_task
            for _ in range(5):await asyncio.sleep(0)
            for at in (241.,350.):
                self.now=at;yield NS(audio=bytes(320),speech_probability=0.)
                observed.append((at,session.done))
        await session.run(frames())
        self.assertIn((350.,False),observed)
        self.assertEqual(session.interruptions,1)

    async def test_rejected_and_truncated_input_never_refresh_budget(self):
        async def rejected(*_args):return ''
        session=self.make_session(rejected)
        async def frames():
            self.now=1.;yield NS(audio=bytes(320),speech_probability=0.)
            self.now=180.;await session.submit(b'rejected',1,False);await session.task
            self.now=230.;await session.submit(b'truncated',30,True)
            self.now=241.;yield NS(audio=bytes(320),speech_probability=0.)
            await asyncio.sleep(0)
        await session.run(frames())
        self.assertEqual(session.reason,'session_limit')

    async def test_accepted_activity_survives_former_real_wall_timeout(self):
        session=self.make_session(clock=time.monotonic);session.max_seconds=.04
        session.max_turns=1000
        self.ends.set();closed=[]
        async def frames():
            for index in range(120):
                await session.submit(b'voice',1,False);await session.task
                yield NS(audio=bytes(320),speech_probability=0.)
                closed.append(session.done)
                await asyncio.sleep(.012)
        try:await session.run(frames())
        except TimeoutError:self.fail('valid ongoing dialogue hit the old absolute wall timer')
        self.assertEqual(len(closed),120)
        self.assertFalse(any(closed))

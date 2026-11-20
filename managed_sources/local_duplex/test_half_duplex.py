import asyncio
from types import SimpleNamespace as NS
import unittest
from session import Session

class HalfDuplexTests(unittest.IsolatedAsyncioTestCase):
    def make(self):
        from half_duplex import HalfDuplexSession
        self.calls=[];self.started=asyncio.Event();self.finish=asyncio.Event();self.now=[10.]
        async def transcribe(audio,*args):self.calls.append(audio);return 'hello'
        async def respond(text):return NS(speech=text,continuing=True)
        async def play(text):self.started.set();await self.finish.wait()
        async def stop():pass
        return HalfDuplexSession(transcribe=transcribe,respond=respond,play=play,stop=stop,clock=lambda:self.now[0])

    async def test_echo_discarded_followup_after_tail_accepted(self):
        s=self.make()
        await s.submit(b'human',1,False);await self.started.wait()
        await s.submit(b'echo',1,False)
        self.assertEqual(self.calls,[b'human']);self.assertIsNone(s._pending)
        self.finish.set();await s.task
        await s.submit(b'tail',1,False)
        self.assertEqual(self.calls,[b'human'])
        self.now[0]+=1
        await s.submit(b'followup',1,False);await s.task
        self.assertEqual(self.calls,[b'human',b'followup'])
        self.assertEqual(s.interruptions,0)
        await s.close()

    async def test_raw_output_audio_is_zeroed_before_enhancer_and_recovers(self):
        s=self.make();await s.submit(b'human',1,False);await self.started.wait()
        seen=[]
        async def raw():
            yield b'\x11\x22'*160
            self.finish.set();await s.task;self.now[0]+=1
            yield b'\x33\x44'*160
        async def enhance(source):
            async for chunk in source:seen.append(chunk);yield NS(audio=chunk,speech_probability=0)
        async for _ in s.enhanced_source(enhance,raw()):pass
        self.assertEqual(seen,[bytes(320),b'\x33\x44'*160])
        self.assertEqual(s.discarded_input_bytes,320)
        await s.close()

    async def test_output_failure_resumes_after_bounded_tail(self):
        s=self.make()
        async def fail(text):raise ValueError('output failed')
        s._output_play=fail
        await s.submit(b'human',1,False);await s.task
        self.assertEqual(s.failures,1);self.assertTrue(s.input_is_suppressed())
        self.now[0]+=1;self.assertFalse(s.input_is_suppressed())
        await s.close()

    async def test_busy_thinking_does_not_queue_old_commands(self):
        s=self.make();thinking=asyncio.Event();release=asyncio.Event()
        async def respond(text):thinking.set();await release.wait();return NS(speech='',continuing=True)
        s.respond=respond
        await s.submit(b'human',1,False);await thinking.wait()
        await s.submit(b'old-command',1,False)
        self.assertIsNone(s._pending);self.assertEqual(self.calls,[b'human'])
        release.set();await s.task
        self.assertFalse(s.input_is_suppressed());await s.close()

    async def test_delayed_homepod_tail_is_respected(self):
        s=self.make();s.output_tail_until=lambda:12.4
        await s.submit(b'human',1,False);await self.started.wait()
        self.finish.set();await s.task
        self.now[0]=11.
        await s.submit(b'delayed echo',1,False)
        self.assertEqual(self.calls,[b'human'])
        self.now[0]=12.5
        await s.submit(b'followup',1,False);await s.task
        self.assertEqual(self.calls,[b'human',b'followup']);await s.close()

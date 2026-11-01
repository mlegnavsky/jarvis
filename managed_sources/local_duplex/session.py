"""Response ownership for a continuously captured, bounded local conversation."""
import asyncio
from contextlib import suppress, aclosing
import time

if __package__:
    from .segmenter import Segmenter
else:
    from segmenter import Segmenter


class Session:
    def __init__(self, *, transcribe, respond, play, stop, idle_seconds=8,
                 clock=time.monotonic, gate=None, silence_seconds=.7,
                 max_seconds=240, max_turns=24,on_interrupt=None,input_timeout_seconds=5):
        self.transcribe=transcribe;self.respond=respond;self.play=play;self.stop=stop
        self.clock=clock;self.gate=gate;self.idle_seconds=idle_seconds
        self.on_interrupt=on_interrupt
        self.max_seconds=max_seconds;self.max_turns=max_turns
        self.input_timeout_seconds=input_timeout_seconds
        self.segmenter=Segmenter(silence_seconds=silence_seconds)
        self.task=None;self.interrupt_task=None;self.generation=0
        self.switch=asyncio.Lock();self.finished=asyncio.Event()
        self.stage='idle';self.done=False;self.closed=False
        self.idle_at=clock();self.frames=0;self.frames_during_output=0
        self.completed_turns=0;self.interruptions=0;self.failures=0;self.last_error=None
        self.truncated=0;self.reason=None

    def snapshot(self):
        return {key:getattr(self,key) for key in ('stage','frames','frames_during_output',
            'completed_turns','interruptions','failures','last_error','truncated','reason')}

    def request_close(self, reason):
        self.reason=reason;self.done=True;self.finished.set()

    async def interrupt(self):
        async with self.switch:
            self.generation+=1
            old,self.task=self.task,None
            if old is not None and not old.done():
                self.interruptions+=1
                if self.on_interrupt:self.on_interrupt()
                old.cancel()
                try:
                    async with asyncio.timeout(3):await self.stop()
                finally:
                    with suppress(asyncio.CancelledError):
                        async with asyncio.timeout(3):await old
            if not self.closed:self.stage='idle';self.idle_at=self.clock()

    async def submit(self, audio, voiced, truncated):
        if self.closed or self.done:return
        if self.interrupt_task is not None:
            await self.interrupt_task;self.interrupt_task=None
        if self.task is not None and not self.task.done():await self.interrupt()
        if truncated:
            self.truncated+=1;self.idle_at=self.clock();return
        self.generation+=1;generation=self.generation
        self.task=asyncio.create_task(self._turn(generation,audio,voiced))

    async def _turn(self, generation, audio, voiced):
        try:
            self.stage='transcribing'
            async with asyncio.timeout(30):text=await self.transcribe(audio,voiced,False)
            if generation!=self.generation or self.closed or not text:return
            self.stage='thinking'
            async with asyncio.timeout(60):result=await self.respond(text)
            if generation!=self.generation or self.closed:return
            if result.speech:
                self.stage='speaking'
                async with asyncio.timeout(100):await self.play(result.speech)
            if generation!=self.generation or self.closed:return
            self.completed_turns+=1
            if not result.continuing or self.completed_turns>=self.max_turns:
                self.request_close('conversation_finished' if not result.continuing else 'turn_limit')
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            self.failures+=1;self.last_error=type(exc).__name__
            if self.failures>=2:self.request_close('repeated_provider_failure')
        finally:
            if generation==self.generation and not self.closed:
                self.stage='idle';self.idle_at=self.clock()

    async def run(self, frames):
        started=self.clock()
        async def consume():
            async with aclosing(aiter(frames)) as source:
                while True:
                    try:
                        async with asyncio.timeout(self.input_timeout_seconds):frame=await anext(source)
                    except StopAsyncIteration:return
                    except TimeoutError:
                        self.request_close('audio_source_stalled');return
                    if self.done:return
                    self.frames+=1
                    if self.stage=='speaking':self.frames_during_output+=1
                    qualified=self.gate(frame,self) if self.gate else [(frame.audio,frame.speech_probability)]
                    for audio,probability in qualified:
                        for event in self.segmenter.feed(audio,probability or 0):
                            if event.kind=='onset':
                                if self.task is not None and not self.task.done():
                                    self.interrupt_task=asyncio.create_task(self.interrupt())
                            else:
                                await self.submit(event.audio,event.voiced_s,event.truncated)
                    busy=self.task is not None and not self.task.done()
                    if not busy and not self.segmenter.active and self.clock()-self.idle_at>=self.idle_seconds:
                        self.request_close('silence_timeout');return
                    if self.clock()-started>=self.max_seconds:
                        self.request_close('session_limit');return
        reader=asyncio.create_task(consume())
        finished=asyncio.create_task(self.finished.wait())
        try:
            async with asyncio.timeout(self.max_seconds+1):
                ready,_pending=await asyncio.wait({reader,finished},return_when=asyncio.FIRST_COMPLETED)
                if reader in ready:await reader
        finally:
            for task in (reader,finished):
                if not task.done():task.cancel()
            await asyncio.gather(reader,finished,return_exceptions=True)
            await self.close()

    async def close(self):
        if self.closed:return
        self.closed=True;self.generation+=1;self.finished.set()
        pending=[t for t in (self.interrupt_task,self.task) if t and not t.done()]
        for task in pending:task.cancel()
        try:
            async with asyncio.timeout(3):await asyncio.gather(*pending,return_exceptions=True)
        finally:
            try:
                async with asyncio.timeout(3):await self.stop()
            finally:self.stage='closed'

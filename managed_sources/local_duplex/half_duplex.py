"""Production turn-taking: discard microphone input while an answer is in flight.

The native microphone transport stays connected. Its bytes are drained and
replaced with silence before VAD, never queued, transcribed or used as commands.
Experimental overlap/echo decisions are intentionally absent from this path.
"""
from contextlib import aclosing

if __package__:
    from .session import Session
    from .segmenter import Segmenter
else:
    from session import Session
    from segmenter import Segmenter


class HalfDuplexSession(Session):
    def __init__(self, *, play, output_tail_until=None, **kwargs):
        self.output_tail_until=output_tail_until or (lambda:0.)
        self._output_play=play
        self.listen_after=0.
        self.discarded_input_bytes=0
        super().__init__(play=self._play_then_listen,**kwargs)
        self.gate=None
        self.interruptions_enabled=lambda:False
        self.interruption_policy='half_duplex_discard_through_output_tail'

    def input_is_suppressed(self):
        return (self.stage in ('transcribing','thinking','speaking')
                or self.task is not None and not self.task.done()
                or self.clock()<self.listen_after)

    async def submit(self, audio, voiced, truncated, *, captured_until=None):
        if self.input_is_suppressed():return
        return await super().submit(audio,voiced,truncated,captured_until=captured_until)

    async def _play_then_listen(self,text):
        self._pending=None
        self.segmenter=Segmenter(silence_seconds=self.segmenter.silence_seconds)
        try:
            return await self._output_play(text)
        finally:
            self.listen_after=max(self.clock()+.6,self.output_tail_until())
            self.segmenter=Segmenter(silence_seconds=self.segmenter.silence_seconds)
            self._pending=None

    async def enhanced_source(self,enhance,source):
        async def discard_output_input():
            async with aclosing(aiter(source)) as incoming:
                async for chunk in incoming:
                    if self.input_is_suppressed():
                        self.discarded_input_bytes+=len(chunk)
                        yield bytes(len(chunk))
                    else:yield chunk
        async with aclosing(discard_output_input()) as sanitized:
            async with aclosing(enhance(sanitized)) as enhanced:
                async for frame in enhanced:yield frame

    def snapshot(self):
        return {**super().snapshot(),'discarded_input_bytes':self.discarded_input_bytes,
                'input_suppressed':self.input_is_suppressed(),
                'raw_microphone_saved':False,'echo_analysis_enabled':False}

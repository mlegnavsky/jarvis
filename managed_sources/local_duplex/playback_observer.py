"""Bounded scalar observations of active-dialogue audio; no input decisions."""
from collections import deque
from contextlib import aclosing
import math
import time

if __package__:
    from .segmenter import samples
else:
    from segmenter import samples


class PlaybackObserver:
    def __init__(self, read_output, *, clock=time.monotonic):
        self.read_output=read_output;self.clock=clock
        self.frames=0;self.output_frames=0;self.unknown_frames=0;self.before_start_frames=0
        self.errors=0;self.clipped_frames=0;self.peak=0;self.max_rms=0.;self.max_receive_lag_ms=0.
        self.observations=deque(maxlen=32);self.turns=deque(maxlen=8)
        self.window=deque(maxlen=40);self.reference=None;self.closed=False

    def snapshot(self):
        rows=list(self.observations)
        return {'scope':'active_dialogue_scalar_playback_observations',
            'frames_seen':self.frames,'frames_during_output':self.output_frames,
            'timing_unavailable_frames':self.unknown_frames,'frames_before_sender_estimate':self.before_start_frames,
            'clipped_frames':self.clipped_frames,'peak_dbfs':round(20*math.log10(self.peak/32768),2) if self.peak else None,
            'max_rms':round(self.max_rms,6),'max_receive_minus_nominal_ms':round(self.max_receive_lag_ms,1),
            'capture_origin':'first_received_chunk_nominal_sample_count_not_hardware_clock',
            'observations':rows,'latest':rows[-1] if rows else None,'turns':list(self.turns),
            'diagnostic_errors':self.errors,'source_closed':self.closed,
            'input_modified':False,'raw_microphone_saved':False,
            'correlation_is_acoustic_proof':False}

    def observe(self, pcm, capture_end, received_at):
        self.frames+=1
        self.max_receive_lag_ms=max(self.max_receive_lag_ms,max(0.,received_at-capture_end)*1000)
        output=self.read_output()
        if not output.owned:
            self.window.clear();return
        self.output_frames+=1
        values=samples(pcm);peak=max(abs(x) for x in values)
        rms=math.sqrt(sum(x*x for x in values)/160)
        self.peak=max(self.peak,peak);self.max_rms=max(self.max_rms,rms/32768)
        self.clipped_frames+=int(peak>=32760)
        reference=getattr(output,'reference',None);started_at=getattr(output,'started_at',None)
        if reference is not self.reference:
            self.window.clear();self.reference=reference
        if reference is None or started_at is None or not math.isfinite(started_at):
            self.unknown_frames+=1;self.window.clear();return
        if capture_end<started_at:self.before_start_frames+=1
        self.window.append(rms)
        if len(self.window)<40 or self.output_frames%10:return
        microphone=list(self.window);mean=sum(microphone)/40
        centered=[x-mean for x in microphone];energy=sum(x*x for x in centered)
        if energy<1e-6:return
        expected=round((capture_end-started_at)*100)-40
        first=max(0,expected-150);last=min(len(reference.levels)-40,expected+150)
        best=None
        for offset in range(first,last+1):
            values=reference.levels[offset:offset+40];mean=sum(values)/40
            values=[x-mean for x in values];power=sum(x*x for x in values)
            if power<1e-6:continue
            correlation=sum(x*y for x,y in zip(centered,values))/math.sqrt(energy*power)
            if best is None or correlation>best[0]:best=(correlation,offset)
        if best is not None:
            self.observations.append({'elapsed_capture_s':round(self.frames/100,2),
                'correlation':round(best[0],4),'offset_ms':(expected-best[1])*10,
                'reference_window_frame':best[1],'window_ms':400,'search_ms':1500})

    async def source(self, source):
        pending=bytearray();origin=None;processed=0;incoming=aiter(source)
        try:
            async for chunk in incoming:
                if origin is None:origin=self.clock()
                try:
                    if not isinstance(chunk,bytes) or len(chunk)%2 or len(chunk)>65536:
                        raise ValueError('invalid_diagnostic_pcm')
                    pending.extend(chunk)
                    while len(pending)>=320:
                        frame=bytes(pending[:320]);del pending[:320];processed+=320
                        try:
                            self.observe(frame,origin+processed/32000,self.clock())
                        except Exception:
                            self.errors+=1;self.window.clear();self.reference=None
                except Exception:
                    self.errors+=1;pending.clear();self.window.clear();self.reference=None
                # Preserve original chunk boundaries, bytes and consumer
                # exceptions even when optional measurement is unavailable.
                yield chunk
        finally:
            pending.clear();self.window.clear();self.reference=None;self.closed=True
            close=getattr(incoming,'aclose',None)
            if close is not None:await close()

    async def enhanced_source(self, enhance, source):
        # Core's enhancer does not own/close its input when suspended at a
        # yielded enhanced frame. Own both layers explicitly, inner first.
        async with aclosing(self.source(source)) as observed:
            async with aclosing(enhance(observed)) as enhanced:
                async for frame in enhanced:yield frame

    async def play(self, play, text, timings, output_snapshot):
        before=dict(timings)
        try:
            return await play(text)
        finally:
            try:self.turns.append({'timings_ms':before,'output':output_snapshot()})
            except Exception:self.errors+=1

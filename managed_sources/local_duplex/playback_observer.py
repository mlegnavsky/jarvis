"""Bounded scalar observations of active-dialogue audio; no input decisions."""
from collections import deque
from contextlib import aclosing
import asyncio
from functools import partial
import math
import time

if __package__:
    from .segmenter import samples
    from .waveform_observer import measure_waveform
else:
    from segmenter import samples
    from waveform_observer import measure_waveform


class PlaybackObserver:
    def __init__(self, read_output, *, clock=time.monotonic,run_executor=None):
        self.read_output=read_output;self.clock=clock
        self.frames=0;self.output_frames=0;self.unknown_frames=0;self.before_start_frames=0
        self.errors=0;self.clipped_frames=0;self.peak=0;self.max_rms=0.;self.max_receive_lag_ms=0.
        self.observations=deque(maxlen=32);self.turns=deque(maxlen=8)
        self.window=deque(maxlen=40);self.reference=None;self.closed=False
        self.run_executor=run_executor;self.wave_window=deque(maxlen=40)
        self.wave_task=None;self.wave_next_at=float('-inf')
        self.wave_observations=deque(maxlen=8)
        self.wave_scheduled=0;self.wave_busy_skips=0;self.wave_errors=0;self.wave_stale=0

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
            'correlation_is_acoustic_proof':False,
            'waveform':{'scope':'raw_PCM_similarity_only_not_input_decision',
                'observations':list(self.wave_observations),
                'latest':self.wave_observations[-1] if self.wave_observations else None,
                'scheduled':self.wave_scheduled,'busy_skips':self.wave_busy_skips,
                'errors':self.wave_errors,'stale_results':self.wave_stale,
                'pending':bool(self.wave_task and not self.wave_task.done()),
                'raw_audio_saved':False,'input_modified':False}}

    def schedule_waveform(self,output,capture_end,received_at):
        if self.run_executor is None:return
        if not math.isfinite(received_at) or not math.isfinite(capture_end):return
        pcm=getattr(output.reference,'pcm',None)
        if not isinstance(pcm,bytes) or len(self.wave_window)<40 or received_at<self.wave_next_at:return
        if self.wave_task is not None and not self.wave_task.done():
            self.wave_busy_skips+=1;return
        reference=output.reference
        func=partial(measure_waveform,b''.join(self.wave_window),pcm,
            played_seconds=capture_end-output.started_at)
        elapsed=round(self.frames/100,2)
        async def work():return await self.run_executor(func)
        self.wave_next_at=received_at+1;self.wave_scheduled+=1
        self.wave_task=asyncio.create_task(work())
        def finished(task):
            if task.cancelled():return
            try:
                facts=task.result()
                if self.closed:return
                if self.reference is not reference:
                    self.wave_stale+=1;return
                if not isinstance(facts,dict) or any(not isinstance(v,(str,int,float,bool,type(None))) for v in facts.values()):
                    raise ValueError('non_scalar_waveform_result')
                self.wave_observations.append({'elapsed_capture_s':elapsed,**facts})
            except Exception:self.wave_errors+=1
        self.wave_task.add_done_callback(finished)

    def observe(self, pcm, capture_end, received_at):
        self.frames+=1
        self.max_receive_lag_ms=max(self.max_receive_lag_ms,max(0.,received_at-capture_end)*1000)
        output=self.read_output()
        if not output.owned:
            self.window.clear();self.wave_window.clear();return
        self.output_frames+=1
        values=samples(pcm);peak=max(abs(x) for x in values)
        rms=math.sqrt(sum(x*x for x in values)/160)
        self.peak=max(self.peak,peak);self.max_rms=max(self.max_rms,rms/32768)
        self.clipped_frames+=int(peak>=32760)
        reference=getattr(output,'reference',None);started_at=getattr(output,'started_at',None)
        if reference is not self.reference:
            self.window.clear();self.wave_window.clear();self.reference=reference
        if reference is None or started_at is None or not math.isfinite(started_at):
            self.unknown_frames+=1;self.window.clear();self.wave_window.clear();return
        if capture_end<started_at:self.before_start_frames+=1
        if self.run_executor is not None:
            self.wave_window.append(pcm)
            self.schedule_waveform(output,capture_end,received_at)
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
                            self.errors+=1;self.window.clear();self.wave_window.clear();self.reference=None
                except Exception:
                    self.errors+=1;pending.clear();self.window.clear();self.wave_window.clear();self.reference=None
                # Preserve original chunk boundaries, bytes and consumer
                # exceptions even when optional measurement is unavailable.
                yield chunk
        finally:
            pending.clear();self.window.clear();self.wave_window.clear();self.reference=None;self.closed=True
            if self.wave_task is not None and not self.wave_task.done():self.wave_task.cancel()
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
            try:
                facts=dict(output_snapshot())
                # Full32-row history belongs to current output only. Repeating
                # it in every retained turn can overflow the128KiB boot report.
                if isinstance(facts.get('transcript_guard'),list):
                    facts['transcript_guard']=facts['transcript_guard'][-1:]
                self.turns.append({'timings_ms':before,'output':facts})
            except Exception:self.errors+=1

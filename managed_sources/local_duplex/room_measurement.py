"""A single consented remote room measurement, with no speech recognition."""
import asyncio
from contextlib import aclosing
import math
import re
import time

if __package__:
    from .playback_observer import PlaybackObserver
else:
    from playback_observer import PlaybackObserver

MAX_SECONDS=30.
MARKER_PREFIX='jarvis-room-test:'
PASSAGE=('Na návsi stál starý dub. Každé ráno pod ním odpočíval malý pes a '
         'pozoroval, jak se vesnice probouzí. Jednoho dne se vedle něj posadila '
         'kočka. A od té chvíle už na ranní hlídku nikdy nebyl sám.')


def reserved_marker(value):
    return isinstance(value,str) and value.startswith(MARKER_PREFIX)


class RoomMeasurement:
    def __init__(self,*,calibration,prepare,start_native,stop_native,ready,isolate,
                 clock=time.monotonic,utc=time.time):
        self.calibration=calibration;self.prepare=prepare
        self.start_native=start_native;self.stop_native=stop_native;self.ready=ready
        self.isolate=isolate
        self.clock=clock;self.utc=utc;self.task=None;self.pipeline_task=None
        self.play_task=None;self.output=None;self.bundle=None;self.recorder=None
        self.pending=False;self.marker=None;self.finished=asyncio.Event()
        self.state='off';self.reason=None;self.error=None;self.cleanup_errors=[]
        self.frames=0;self.first_frame_at=None;self.last_frame_at=None
        self.native_start_sent=False;self.start_at=None;self.stop_at=None

    def snapshot(self):
        duration=0. if self.first_frame_at is None else max(0.,(self.last_frame_at or self.first_frame_at)-self.first_frame_at)
        return {'state':self.state,'reason':self.reason,'error_type':self.error,
            'pending':self.pending,'native_start_sent':self.native_start_sent,
            'maximum_seconds':30,'frames':self.frames,
            'microphone_window_s':round(duration,4),
            'request_window_s':round(max(0.,self.stop_at-self.start_at),4) if self.stop_at is not None else None,
            'cleanup_errors':list(self.cleanup_errors),'raw_audio_saved':False,
            'cloud_microphone_audio':False,'household_actions':False,
            'one_shot_scope':'one_remote_start_even_across_restart'}

    def accepts(self,marker):
        return bool(self.pending and marker==self.marker and self.pipeline_task is None)

    def abort(self,reason):
        if self.reason is None:self.reason=reason
        if self.task is not None and not self.task.done() and not self.task.cancelling():self.task.cancel()

    def claim(self,nonce):
        # This capability was approved for one remote start, not recurrence.
        # An existing record (even an unfamiliar schema) fails closed.
        if self.calibration.store.read('room-test-state.json') is not None:return False
        self.calibration.store.write('room-test-state.json',{'consumed':True,'nonce':nonce})
        return True

    async def cleanup(self,name,awaitable):
        try:
            async with asyncio.timeout(3):await awaitable
        except (Exception,asyncio.CancelledError) as error:
            self.cleanup_errors.append(name+':'+type(error).__name__)

    async def run(self,nonce,expires_at):
        if self.task is not None and self.task is not asyncio.current_task() and not self.task.done():return
        if (not isinstance(nonce,str) or not re.fullmatch('[a-f0-9]{32}',nonce)
                or type(expires_at) not in (int,float) or not math.isfinite(expires_at)
                or not self.utc()<expires_at<=self.utc()+120 or not self.ready()):
            self.state='rejected';return
        self.task=asyncio.current_task();cancelled=False
        try:
            if await self.calibration.execute(self.calibration.store.read,'room-test-state.json') is not None:
                self.state='already_consumed';return
            self.state='preparing'
            async with asyncio.timeout(30):self.bundle=await self.prepare()
            self.output=self.bundle.output
            if not self.ready() or not self.utc()<expires_at:
                self.state='rejected';return
            if not await self.calibration.arm(nonce,expires_at):
                self.state='capture_unavailable';return
            if not await self.calibration.execute(self.claim,nonce):
                self.state='already_consumed';return
            await self.isolate()
            self.marker=MARKER_PREFIX+nonce;self.pending=True;self.finished.clear()
            self.state='starting';self.start_at=self.clock();self.native_start_sent=True
            async with asyncio.timeout(MAX_SECONDS):
                await self.start_native(self.bundle.media_id,self.marker)
                await self.finished.wait()
            if self.reason is None:self.reason='audio_source_ended'
        except TimeoutError:
            self.reason='measurement_deadline' if self.native_start_sent else 'preparation_timeout'
        except asyncio.CancelledError:
            cancelled=self.reason is None
            if self.reason is None:self.reason='cancelled'
        except Exception as error:
            self.error=type(error).__name__;self.reason='measurement_error'
        finally:
            self.pending=False
            if self.native_start_sent:self.stop_at=self.clock()
            task=self.pipeline_task
            if task is not None and not task.done():
                task.cancel()
                await self.cleanup('pipeline',asyncio.gather(task,return_exceptions=True))
            if self.native_start_sent:
                await self.cleanup('native_stop',self.stop_native(self.marker,task))
            if self.play_task is not None and not self.play_task.done():self.play_task.cancel()
            if self.output is not None:await self.cleanup('speaker',self.output.stop())
            if self.play_task is not None:
                await self.cleanup('playback_task',asyncio.gather(self.play_task,return_exceptions=True))
            if self.recorder is not None and self.reason=='measurement_deadline' and not self.error and not self.cleanup_errors:
                self.calibration.finish(self.recorder);self.state='captured'
            else:
                await self.cleanup('erase',self.calibration.discard())
                if self.reason is not None:self.state='failed' if self.error else 'stopped'
            if self.bundle is not None:await self.cleanup('generated_resource',self.bundle.release())
            if self.cleanup_errors:self.state='cleanup_failed'
            if cancelled:raise asyncio.CancelledError()

    async def capture(self,source,enhance):
        if not self.pending or self.pipeline_task is not None:return
        self.pipeline_task=asyncio.current_task();self.state='capturing'
        self.recorder=self.calibration.attach(lambda:self.output)
        if self.recorder is None:
            self.reason='capture_unavailable';self.finished.set();return
        observer=PlaybackObserver(lambda:self.output,capture=self.recorder)
        try:
            async with aclosing(observer.enhanced_source(enhance,source)) as frames:
                while self.pending:
                    try:
                        async with asyncio.timeout(5):await anext(frames)
                    except StopAsyncIteration:break
                    now=self.clock();self.frames+=1
                    if self.first_frame_at is None:self.first_frame_at=now
                    self.last_frame_at=now
                    if self.play_task is None:self.play_task=asyncio.create_task(self.output.play(PASSAGE))
                    elif self.play_task.done():await self.play_task
                    if self.recorder.error:raise ValueError('memory_capture_failed')
        except asyncio.CancelledError:raise
        except Exception as error:
            self.error=type(error).__name__;self.reason='source_or_output_error'
        finally:self.finished.set()

"""One exact HomePod's existing HA-owned RAOP connection and complete speech files."""
import asyncio
import math
import re

if __package__:
    from .ha_io import LocalOutput
    from .segmenter import EchoReference
    from .speech_file import drain, release_prepared
else:
    from ha_io import LocalOutput
    from segmenter import EchoReference
    from speech_file import drain, release_prepared

HOME='media_player.homepod_obyvak_homepod_obyvak'
LOCAL_SPEECH=re.compile(r'media-source://media_source/local/jarvis_speech/jarvis-[a-f0-9]{32}\.wav')

class HomePodNotReady(ValueError):
    """Known pre-write connection/busy state; safe to check again later."""


def raop_audio(player,protocol=None):
    if player is None or not player.available:raise HomePodNotReady('homepod_unavailable')
    if player.entity_id!=HOME:raise ValueError('exact_homepod_required')
    if protocol is None:
        from pyatv.const import Protocol
        protocol=Protocol.RAOP
    try:return player.atv.audio._interfaces[protocol]
    except (AttributeError,KeyError):raise HomePodNotReady('homepod_raop_unavailable') from None


def level(value):
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or not 0<=value<=1:
        raise ValueError('homepod_volume_unavailable')
    return float(value)


async def prime_homepod(player,*,protocol=None):
    """Restore the owner's existing startup45 policy once, never after answers."""
    audio=raop_audio(player,protocol)
    if audio.playback_manager._is_acquired:raise HomePodNotReady('homepod_already_playing')
    await audio.set_volume(45.)
    observed=level(audio.volume/100)
    if abs(observed-.45)>.005:raise ValueError('homepod_startup_volume_unconfirmed')
    return {'status':'applied','volume':observed,'policy':'startup45_once_then_current_volume'}


def homepod_state(player,shared=None,*,protocol=None):
    audio=raop_audio(player,protocol)
    if shared is not None:
        if not isinstance(shared,dict) or set(shared)!={'volume','muted'} or type(shared['muted']) is not bool:
            raise ValueError('shared_volume_unavailable')
        volume=level(shared['volume']);muted=shared['muted'];source='shared_tv'
    else:volume=level(audio.volume/100);muted=False;source='raop'
    return {'volume':volume,'muted':muted or getattr(player,'is_volume_muted',None) is True,
        'source':source,'busy':audio.playback_manager._is_acquired}


def homepod_timing(player,*,protocol=None):
    manager=raop_audio(player,protocol).playback_manager;client=manager.stream_client
    if client is None:return None
    position=client.playback_info.position;context=manager.context
    rate=context.sample_rate;latency=context.latency
    if (any(isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value)
            for value in (position,rate,latency)) or not 0<position<=120 or not 8000<=rate<=192000
            or not 0<=latency<=rate*10):return None
    return {'position_s':float(position),'latency_s':float(latency/rate)}


async def play_homepod_file(player,media_id,volume,*,protocol=None):
    if not isinstance(media_id,str) or not LOCAL_SPEECH.fullmatch(media_id):
        raise ValueError('complete_local_speech_required')
    audio=raop_audio(player,protocol)
    if audio.playback_manager._is_acquired:raise ValueError('homepod_already_playing')
    await audio.set_volume(level(volume)*100)
    # Core AppleTV resolves this source to its path; miniaudio never fetches a TTS URL.
    await player.async_play_media('music',media_id)


class HomePodOutput(LocalOutput):
    def __init__(self,read_player,tts,start,read_state,timing,*,shared_volume=lambda:None,**kwargs):
        super().__init__(read_player,tts,start,None,**kwargs)
        self.read_state=read_state;self.timing=timing;self.shared_volume=shared_volume
        self.native_task=None;self.last_volume_decision=None;self.latency_s=None
        self.cleanup_tasks=set();self.stop_timeout=3.

    def snapshot(self):
        return {**super().snapshot(),'target':HOME,'transport':'native_raop_local_file',
            'volume_decision':self.last_volume_decision,'negotiated_latency_s':self.latency_s,
            'pending_resource_cleanup':len(self.cleanup_tasks)}

    def available_player(self):
        player=self.read_player()
        if player is None or not player.available:raise ValueError('homepod_unavailable')
        decision=self.read_state(player,self.shared_volume())
        self.last_volume_decision=decision
        if decision['busy'] or (str(player.state) in ('playing','buffering') and decision['source']!='shared_tv'):
            raise ValueError('homepod_already_playing')
        if decision['muted'] or decision['volume']==0:self.skipped+=1;return None
        return player

    def disown(self):
        super().disown()
        if self.native_task is not None and not self.native_task.done() and not self.native_task.cancelling():self.native_task.cancel()

    async def release_resource(self,prepared):
        task=self.native_task
        if task is not None and not task.done():
            # A timed-out teardown still owns its open audio source. Hand cleanup
            # to that exact task; neither unlink early nor block a new voice loop.
            async def after_native():
                _result,cancelled=await drain(asyncio.gather(task,return_exceptions=True))
                await release_prepared(prepared)
                if cancelled:raise asyncio.CancelledError()
            cleanup=asyncio.create_task(after_native());self.cleanup_tasks.add(cleanup)
            def finished(done):
                self.cleanup_tasks.discard(done)
                if not done.cancelled():done.exception()
            cleanup.add_done_callback(finished)
        else:await super().release_resource(prepared)

    async def play_prepared(self,prepared,owner):
        if owner!=self.generation or asyncio.current_task().cancelling():raise asyncio.CancelledError()
        player=self.available_player()
        if player is None:return
        self.reference=EchoReference(prepared.pcm);self.last_reference_duration_s=len(prepared.pcm)/32000
        self.started_at=None;self.latency_s=None;self.tail_until=0.;self.recent.clear();self.recent_bytes=0;self.pending.clear()
        self.owned=True
        self.native_task=asyncio.create_task(self.start(player,prepared.media_id,self.last_volume_decision['volume']))
        self.native_task.add_done_callback(lambda task:None if task.cancelled() else task.exception())
        self.started+=1;deadline=self.clock()+12
        try:
            async with asyncio.timeout(100):
                while not self.native_task.done():
                    if not self.owned or owner!=self.generation:raise asyncio.CancelledError()
                    if not player.available:raise ValueError('homepod_disconnected')
                    observed=self.timing(player)
                    if self.started_at is None and observed is not None:
                        self.latency_s=observed['latency_s']
                        self.started_at=self.clock()-observed['position_s']+self.latency_s
                    if self.started_at is None and self.clock()>=deadline:raise TimeoutError('homepod_audio_start_unobserved')
                    await self.sleep(.02)
                await self.native_task
            if not self.owned or owner!=self.generation:raise asyncio.CancelledError()
            if self.started_at is None:raise ValueError('homepod_audio_start_unobserved')
            self.completed+=1;self.owned=False;self.tail_until=self.clock()+.4
        except asyncio.CancelledError:
            await self.stop();raise
        except Exception as exc:
            self.last_error=type(exc).__name__
            await self.stop();raise

    async def stop(self):
        self.generation+=1
        was_owned=self.owned
        self.owned=False;started=self.clock();task=self.native_task
        if task is not None and not task.done():
            if was_owned and not task.cancelling():task.cancel()
            async with asyncio.timeout(self.stop_timeout):await asyncio.shield(asyncio.gather(task,return_exceptions=True))
        if was_owned:self.stopped+=1;self.last_stop_s=round(self.clock()-started,3)
        self.tail_until=self.clock()+.4

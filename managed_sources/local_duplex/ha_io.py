"""Local announcement ownership; imports HA only at its native boundary."""
import asyncio
from collections import deque
import io
import math
import time
import wave

if __package__:
    from .segmenter import EchoReference
else:
    from segmenter import EchoReference


def decode_reference(data):
    if not isinstance(data,bytes) or len(data)>32000*91:
        raise ValueError('reference_too_large')
    with wave.open(io.BytesIO(data),'rb') as audio:
        if (audio.getframerate(),audio.getnchannels(),audio.getsampwidth())!=(16000,1,2):
            raise ValueError('reference_format_not_pcm16k')
        pcm=audio.readframes(16000*90+1)
    if not 320<=len(pcm)<=32000*90:raise ValueError('reference_duration_unavailable')
    return pcm


def stop_announcement(player, *, stop_command=None):
    if stop_command is None:
        from aioesphomeapi import MediaPlayerCommand
        stop_command=MediaPlayerCommand.STOP
    player._client.media_player_command(player._key,command=stop_command,
        announcement=True,device_id=player._static_info.device_id)


def is_output_change(data,player_id,resolve):
    if data.get('domain')!='media_player' or data.get('service') not in (
        'play_media','media_stop','media_pause','media_play','media_play_pause','clear_playlist','turn_off'):
        return False
    targets=data.get('service_data') or {}
    entities=targets.get('entity_id',[])
    if entities=='all' or isinstance(entities,list) and 'all' in entities:return True
    selected=resolve(targets)
    return player_id in selected.referenced or player_id in selected.indirectly_referenced


class LocalOutput:
    def __init__(self,read_player,tts,start,send_stop,*,clock=time.monotonic,sleep=asyncio.sleep):
        self.read_player=read_player;self.tts=tts;self.start=start;self.send_stop=send_stop
        self.clock=clock;self.sleep=sleep;self.owned=False;self.generation=0
        self.reference=None;self.started_at=None;self.recent=deque();self.recent_bytes=0
        self.completed=0;self.skipped=0;self.started=0;self.stopped=0
        self.echo_frames=0;self.overlap_frames=0;self.discarded=0;self.last_stop_s=None
        self.last_reference_duration_s=None;self.last_error=None
        self.tail_until=0.;self.last_overlap_at=None
        self.pending=[]

    def snapshot(self):
        return {key:getattr(self,key) for key in ('owned','started','completed','skipped',
            'stopped','echo_frames','overlap_frames','discarded','last_stop_s',
            'last_reference_duration_s','last_error')}

    def disown(self):
        self.generation+=1;self.owned=False;self.reference=None;self.started_at=None
        self.pending.clear()
        self.discarded+=1

    def available_player(self):
        player=self.read_player()
        if not player or not player.available:raise ValueError('local_speaker_unavailable')
        if player.is_volume_muted is True or player.volume_level==0:
            self.skipped+=1;return None
        level=player.volume_level
        if isinstance(level,bool) or not isinstance(level,(int,float)) or not math.isfinite(level) or not 0<=level<=1:
            raise ValueError('local_speaker_volume_unknown')
        if str(player.state) not in ('idle','off','on'):
            raise ValueError('local_speaker_already_playing')
        return player

    async def play(self,text):
        self.generation+=1;owner=self.generation
        if self.available_player() is None:return
        prepared=await self.tts(text)
        if owner!=self.generation or asyncio.current_task().cancelling():raise asyncio.CancelledError()
        player=self.available_player()
        if player is None:return
        self.reference=EchoReference(prepared.pcm)
        self.last_reference_duration_s=len(prepared.pcm)/32000
        self.started_at=None;self.tail_until=0.;self.recent.clear();self.recent_bytes=0
        self.pending.clear()
        self.owned=True
        try:
            await self.start(player,prepared.media_id)
            self.started+=1
            async with asyncio.timeout(12):
                while self.owned and owner==self.generation and str(player.state)!='playing':
                    if not player.available:raise ValueError('local_speaker_disconnected')
                    await self.sleep(.02)
            if not self.owned or owner!=self.generation:raise asyncio.CancelledError()
            self.started_at=self.clock()
            async with asyncio.timeout(95):
                while self.owned and owner==self.generation and str(player.state)=='playing':
                    if not player.available:raise ValueError('local_speaker_disconnected')
                    await self.sleep(.02)
            if not self.owned or owner!=self.generation:raise asyncio.CancelledError()
            if not player.available or str(player.state) not in ('idle','off','on'):
                raise ValueError('local_playback_end_unconfirmed')
            self.completed+=1;self.owned=False;self.tail_until=self.clock()+.4
        except asyncio.CancelledError:
            await self.stop()
            raise
        except Exception as exc:
            self.last_error=type(exc).__name__
            await self.stop()
            raise

    async def stop(self):
        self.generation+=1
        if not self.owned:return
        player=self.read_player();self.owned=False
        if player is None or not player.available:raise ValueError('speaker_stop_unconfirmed')
        started=self.clock()
        await self.send_stop(player)
        async with asyncio.timeout(2):
            while player and player.available and str(player.state) not in ('idle','off','on'):await self.sleep(.02)
        if not player.available:raise ValueError('speaker_stop_unconfirmed')
        self.stopped+=1;self.last_stop_s=round(self.clock()-started,3);self.tail_until=self.clock()+.4

    def gate(self,frame,session):
        probability=frame.speech_probability or 0.
        candidate=(frame.audio,probability)
        session.segmenter.onset_seconds=.08
        active=self.owned or self.clock()<self.tail_until
        if not active or self.started_at is None or self.reference is None:
            self.recent.clear();self.recent_bytes=0
            pending,self.pending=self.pending,[]
            return pending+[candidate]
        if self.owned:self.overlap_frames+=1;self.last_overlap_at=self.clock()
        self.recent.append(frame.audio);self.recent_bytes+=len(frame.audio)
        while self.recent_bytes>12800:self.recent_bytes-=len(self.recent.popleft())
        if self.recent_bytes<7680:
            self.pending.append(candidate);return []
        candidates,self.pending=self.pending+[candidate],[]
        echo=self.reference.is_echo(b''.join(self.recent),played_seconds=self.clock()-self.started_at)
        if echo:
            self.echo_frames+=len(candidates)
            return [(audio,0.) for audio,_probability in candidates]
        return candidates

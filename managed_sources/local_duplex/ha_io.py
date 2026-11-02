"""Local announcement ownership; imports HA only at its native boundary."""
import asyncio
from collections import deque
import io
import math
import time
import wave

if __package__:
    from .segmenter import EchoReference, samples
    from .speech_file import release_prepared
    from .text_echo import TextEcho
else:
    from segmenter import EchoReference, samples
    from speech_file import release_prepared
    from text_echo import TextEcho


def pcm_signal(pcm):
    if not isinstance(pcm,bytes) or not pcm or len(pcm)%2 or len(pcm)>32000*90:
        raise ValueError('invalid_signal_pcm')
    values=samples(pcm);peak=max(abs(value) for value in values)
    rms=math.sqrt(sum(value*value for value in values)/len(values))
    return {'duration_s':round(len(pcm)/32000,3),'silent':peak==0,
        'peak_dbfs':round(20*math.log10(peak/32768),2) if peak else None,
        'rms_dbfs':round(20*math.log10(rms/32768),2) if rms else None}


def restart_allowed(registry,player,button,build_unique_id):
    unique=build_unique_id(player._entry_data.device_info.mac_address,button)
    entity_id=registry.async_get_entity_id('button','esphome',unique)
    entry=registry.async_get(entity_id) if entity_id else None
    return not entry or str(entry.disabled_by)!='user'


def restart_native(player, *, button_type=None,allowed=None):
    if button_type is None:
        from aioesphomeapi import ButtonInfo
        button_type=ButtonInfo
    entry=player._entry_data
    if entry.client is not player._client:raise ValueError('native_connection_mismatch')
    buttons=[info for info in entry.info.get(button_type,{}).values()
        if info.device_id==player._static_info.device_id and info.name=='Restart']
    if len(buttons)!=1:raise ValueError('exact_restart_button_unavailable')
    if allowed is not None and not allowed(buttons[0]):raise ValueError('restart_disabled_by_user')
    player._client.button_command(buttons[0].key,device_id=buttons[0].device_id)


def reassert_output(player, *, mute_command=None,unmute_command=None):
    level=player.volume_level;muted=player.is_volume_muted
    if not player.available or isinstance(level,bool) or not isinstance(level,(int,float)) or not math.isfinite(level) or not 0<=level<=1 or type(muted) is not bool:
        raise ValueError('fresh_output_settings_required')
    if mute_command is None or unmute_command is None:
        from aioesphomeapi import MediaPlayerCommand
        mute_command=MediaPlayerCommand.MUTE;unmute_command=MediaPlayerCommand.UNMUTE
    player._client.media_player_command(player._key,volume=level,device_id=player._static_info.device_id)
    if muted or level>0:
        player._client.media_player_command(player._key,command=mute_command if muted else unmute_command,
            device_id=player._static_info.device_id)


def fresh_output_state(player):
    try:
        state=player._state
        return state is not None and (type(state),player._static_info.device_id,player._key) not in player._entry_data.stale_state
    except (AttributeError,KeyError):return False


async def recover_native_output(read_player,restart,reassert,*,clock=time.monotonic,sleep=asyncio.sleep):
    player=read_player()
    if player is None or not player.available or str(player.state) not in ('idle','off','on'):
        raise ValueError('idle_speaker_required')
    restart(player)
    deadline=clock()+12
    while (current:=read_player()) is not None and current.available:
        if clock()>=deadline:raise TimeoutError('restart_disconnect_unobserved')
        await sleep(.1)
    deadline=clock()+60
    while (current:=read_player()) is None or not current.available or str(current.state) not in ('idle','off','on') or not fresh_output_state(current):
        if clock()>=deadline:raise TimeoutError('restart_reconnect_unobserved')
        await sleep(.2)
    reassert(current)
    return {'status':'restart_verified','disconnect_observed':True,'reconnect_observed':True,'fresh_state_observed':True,
        'microphone_opened':False,'firmware_changed':False,'audibility_confirmed':False}


def decode_reference(data):
    if not isinstance(data,bytes) or len(data)>32000*91:
        raise ValueError('reference_too_large')
    with wave.open(io.BytesIO(data),'rb') as audio:
        if (audio.getframerate(),audio.getnchannels(),audio.getsampwidth())!=(16000,1,2):
            raise ValueError('reference_format_not_pcm16k')
        pcm=audio.readframes(16000*90+1)
    if not 320<=len(pcm)<=32000*90:raise ValueError('reference_duration_unavailable')
    return pcm


def prime_native_vad(enhancer):
    """Fill microVAD1.0.1's74-feature context with silence, never microphone PCM."""
    vad=getattr(enhancer,'vad',None)
    if vad is None:raise ValueError('native_vad_required')
    for count in range(1,201):
        probability=vad.Process10ms(bytes(320))
        if isinstance(probability,bool) or not isinstance(probability,(int,float)) or not math.isfinite(probability):
            raise ValueError('native_vad_probability_invalid')
        if 0<=probability<=1:return count,probability
        if probability!=-1:raise ValueError('native_vad_probability_invalid')
    raise ValueError('native_vad_never_ready')


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
        self.echo_min_bytes=7680;self.text_echo=TextEcho();self.pending_text='';self.text_echo_suppressed=0

    def snapshot(self):
        return {key:getattr(self,key) for key in ('owned','started','completed','skipped',
            'stopped','echo_frames','overlap_frames','discarded','last_stop_s',
            'last_reference_duration_s','last_error','text_echo_suppressed')}

    def echo_tail_seconds(self):return .4

    def remember_speech(self):
        self.text_echo.remember(self.pending_text,started_at=self.started_at,
            duration=self.last_reference_duration_s,tail=.4)

    def is_own_transcript(self,text,audio,captured_until):
        matched=self.text_echo.matches(text,captured_from=captured_until-len(audio)/32000,
                                      captured_until=captured_until)
        if matched:self.text_echo_suppressed+=1
        return matched

    def playing(self):
        return self.owned and self.started_at is not None and self.clock()>=self.started_at

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
        self.pending_text=text
        try:await self.play_prepared(prepared,owner)
        finally:await self.release_resource(prepared)

    async def release_resource(self,prepared):
        await release_prepared(prepared)

    async def play_prepared(self,prepared,owner):
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
            self.remember_speech()
            async with asyncio.timeout(95):
                while self.owned and owner==self.generation and str(player.state)=='playing':
                    if not player.available:raise ValueError('local_speaker_disconnected')
                    await self.sleep(.02)
            if not self.owned or owner!=self.generation:raise asyncio.CancelledError()
            if not player.available or str(player.state) not in ('idle','off','on'):
                raise ValueError('local_playback_end_unconfirmed')
            self.completed+=1;self.owned=False;self.tail_until=self.clock()+self.echo_tail_seconds()
            self.text_echo.stopped(at=self.clock(),tail=.4)
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
        self.stopped+=1;self.last_stop_s=round(self.clock()-started,3);self.tail_until=self.clock()+self.echo_tail_seconds()
        self.text_echo.stopped(at=self.clock(),tail=self.echo_tail_seconds())

    def gate(self,frame,session):
        probability=frame.speech_probability or 0.
        candidate=(frame.audio,probability)
        session.segmenter.onset_seconds=.08
        active=self.owned or self.clock()<self.tail_until
        if not active or self.started_at is None or self.reference is None or self.clock()<self.started_at:
            self.recent.clear();self.recent_bytes=0
            pending,self.pending=self.pending,[]
            return pending+[candidate]
        if self.owned:self.overlap_frames+=1;self.last_overlap_at=self.clock()
        self.recent.append(frame.audio);self.recent_bytes+=len(frame.audio)
        while self.recent_bytes>12800:self.recent_bytes-=len(self.recent.popleft())
        if self.recent_bytes<self.echo_min_bytes:
            self.pending.append(candidate);return []
        candidates,self.pending=self.pending+[candidate],[]
        echo=self.reference.is_echo(b''.join(self.recent),played_seconds=self.clock()-self.started_at)
        if echo:
            self.echo_frames+=len(candidates)
            return [(audio,0.) for audio,_probability in candidates]
        return candidates

"""Bounded native audio facts; never persist device log text."""
import asyncio
from contextlib import contextmanager
import logging
import re


TAGS=frozenset(('aic3204','i2s_audio.speaker','speaker_mixer','resampler_speaker',
    'speaker_media_player','speaker_media_player.pipeline','speaker_source',
    'audio_decoder','audio_file','audio_http','media_source.audio_file','media_source.audio_http','voice_kit'))
ANSI=re.compile(r'\x1b\[[0-9;]*m')
HEADER=re.compile(r'\[[EWIDCV]\]\[([a-z0-9_.]+):[0-9]+\]: ?(.*)')
ERRORS={
    "The announcement pipeline's file reader encountered an error.":'announcement_reader_error',
    "The announcement pipeline's audio decoder encountered an error.":'announcement_decoder_error',
    "The media pipeline's file reader encountered an error.":'media_reader_error',
    "The media pipeline's audio decoder encountered an error.":'media_decoder_error',
    'Communication with AIC3204 failed!':'communication_error',
    'Communication failed':'communication_error',
    'Writing mute modes failed':'mute_write_error',
    'Writing volume failed':'volume_write_error',
    'Set volume failed':'volume_write_error',
    'Set mute failed':'mute_write_error',
    'Setup failed; cannot play audio':'setup_failed',
    'Speaker task setup failed (allocation, preload, or channel enable)':'task_setup_failed',
    'Failed to initialize I2S channel':'i2s_init_failed',
    'Failed to create event group':'allocation_failed',
    'Starting':'starting','Started':'started','Stopping':'stopping','Stopped':'stopped',
    'AIC3204:':'configured','Speaker:':'configured','I2S Audio Speaker:':'configured',
    'Mixer Speaker:':'configured','Mixer Source Speaker':'configured','Resampler Speaker:':'configured',
}
NUMERIC={'Pin':'pin','Buffer duration':'buffer_ms','Buffer Duration':'buffer_ms',
    'Target Bits Per Sample':'target_bits','Target Sample Rate':'target_rate','Timeout':'timeout_ms'}
ERROR_CODES=frozenset(('ESP_OK','ESP_FAIL','ESP_ERR_NO_MEM','ESP_ERR_INVALID_ARG',
    'ESP_ERR_INVALID_STATE','ESP_ERR_INVALID_SIZE','ESP_ERR_NOT_FOUND',
    'ESP_ERR_NOT_SUPPORTED','ESP_ERR_TIMEOUT','ESP_ERR_INVALID_RESPONSE',
    'ESP_ERR_INVALID_CRC','ESP_ERR_NOT_FINISHED'))


@contextmanager
def private_native_logs(client,title):
    """Prevent this audit's raw lines escaping through pre-existing loggers.

    Covers changes to HA/native DEBUG during the audit without altering log
    levels or removing another subscriber. Pinned native paths log the device
    identity as their first argument; unrelated devices retain their logs.
    """
    def allow(record):
        args=record.args
        identity=title if record.name=='homeassistant.components.esphome.manager' else getattr(client,'log_name',None)
        return not (isinstance(args,tuple) and args and identity is not None and args[0]==identity)
    loggers=[logging.getLogger(name) for name in ('homeassistant.components.esphome.manager',
        'aioesphomeapi.connection','aioesphomeapi._frame_helper.base')]
    for logger in loggers:logger.addFilter(allow)
    try:yield
    finally:
        for logger in loggers:logger.removeFilter(allow)


class AudioFacts:
    def __init__(self):
        self.facts=[];self.messages=0;self.truncated=False;self.logging_restored=False
        self.audio_messages=0;self.error_messages=0

    def add(self,fact):
        if fact in self.facts:return
        if len(self.facts)<64:self.facts.append(fact)
        else:self.truncated=True

    def feed(self,message):
        if self.messages>=512:self.truncated=True;return
        self.messages+=1
        raw=getattr(message,'message',b'')
        if not isinstance(raw,bytes) or len(raw)>8192:self.truncated=True;return
        tag=None
        for line in ANSI.sub('',raw.decode('utf-8','replace')).splitlines()[:64]:
            match=HEADER.search(line)
            if match:tag,text=match.groups()
            elif tag is not None and line.startswith(' '):text=line.strip()
            else:tag=None;continue
            if tag not in TAGS:continue
            self.audio_messages+=1
            if match and re.search(r'\[E\]\[',line):self.error_messages+=1
            fact={'component':tag}
            if text in ERRORS:self.add({**fact,'event':ERRORS[text]});continue
            decoded=re.fullmatch(r'Decoded audio has ([12]) channels, ([0-9]{4,6}) Hz sample rate, and ([0-9]{1,2}) bits per sample',text)
            if decoded:
                channels,rate,bits=map(int,decoded.groups())
                self.add({**fact,'event':'decoded_format','channels':channels,'sample_rate':rate,'bits_per_sample':bits})
                continue
            numeric=re.fullmatch(r'\s*('+'|'.join(NUMERIC)+r'): ([0-9]{1,6})(?: ms| Hz)?',text)
            if numeric:self.add({**fact,'event':NUMERIC[numeric[1]],'value':int(numeric[2])});continue
            error=re.fullmatch(r'(Media reader encountered an error|Decoder encountered an error|I2S channel allocation failed): (ESP_ERR_[A-Z0-9_]{1,40}|ESP_FAIL|ESP_OK)',text)
            if error:self.add({**fact,'event':{'Media reader encountered an error':'reader_error','Decoder encountered an error':'decoder_error','I2S channel allocation failed':'i2s_allocation_error'}[error[1]],'code':error[2] if error[2] in ERROR_CODES else 'unknown_error'})

    def snapshot(self):
        return {'messages_processed':self.messages,'audio_messages':self.audio_messages,
            'error_messages':self.error_messages,'facts':list(self.facts),'truncated':self.truncated,
            'logging_restored':self.logging_restored,'raw_logs_saved':False,'microphone_opened':False}


async def audit_native(player,playback,restore_level,*,ha_logging=lambda:False,debug_level=None,sleep=asyncio.sleep,facts=None):
    if player._entry_data.client is not player._client:raise ValueError('native_connection_mismatch')
    if not player.available:raise ValueError('local_speaker_unavailable')
    if ha_logging() or getattr(player._client,'_debug_enabled',False):
        raise ValueError('native_raw_logging_active')
    if debug_level is None:
        from aioesphomeapi import LogLevel
        debug_level=LogLevel.LOG_LEVEL_DEBUG
    facts=facts if facts is not None else AudioFacts()
    client=player._client;unsubscribe=None
    with private_native_logs(client,getattr(player._entry_data,'title',None)):
        try:
            unsubscribe=client.subscribe_logs(facts.feed,log_level=debug_level,dump_config=True)
            async with asyncio.timeout(25):
                await sleep(1)
                result=await playback()
                await sleep(.5)
        finally:
            if unsubscribe is not None:unsubscribe()
            restore=client.subscribe_logs(lambda _message:None,log_level=restore_level(),dump_config=False)
            restore();facts.logging_restored=True
            await sleep(.2)
    return {**facts.snapshot(),'playback':result}

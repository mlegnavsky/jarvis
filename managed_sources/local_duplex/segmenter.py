"""Bounded 16kHz PCM turns and local-playback envelope observations."""
from collections import deque
from dataclasses import dataclass
import array
import math
import sys

RATE_BYTES = 32000


def samples(pcm):
    value=array.array('h')
    value.frombytes(pcm)
    if sys.byteorder!='little':value.byteswap()
    return value


def envelopes(pcm):
    value=samples(pcm)
    return [math.sqrt(sum(x*x for x in value[i:i+160])/160)
            for i in range(0,len(value)-159,160)]


@dataclass(frozen=True)
class SpeechEvent:
    kind: str
    audio: bytes=b''
    voiced_s: float=0
    truncated: bool=False


class Segmenter:
    def __init__(self, *, silence_seconds=.7, onset_seconds=.08, max_seconds=30):
        if not .2<=silence_seconds<=2 or not .04<=onset_seconds<=.5 or not 1<=max_seconds<=30:
            raise ValueError('invalid_segment_limits')
        self.silence_seconds=silence_seconds
        self.onset_seconds=onset_seconds
        self.max_bytes=round(max_seconds*RATE_BYTES)
        self.pre=deque()
        self.pre_bytes=0
        self.audio=bytearray()
        self.candidate=0.
        self.voiced=0.
        self.silent=0.
        self.active=False
        self.blocked=False

    @property
    def buffered_bytes(self):return len(self.audio)+self.pre_bytes

    def feed(self, audio, probability):
        if not isinstance(audio,bytes) or not audio or len(audio)%2 or len(audio)>3200:
            raise ValueError('invalid_pcm_frame')
        if probability==-1:probability=0.  # Native microVAD: not enough features yet.
        if isinstance(probability,bool) or not isinstance(probability,(int,float)) or not math.isfinite(probability) or not 0<=probability<=1:
            raise ValueError('invalid_speech_probability')
        seconds=len(audio)/RATE_BYTES
        speech=probability>.6
        if self.blocked:
            self.silent=0 if speech else self.silent+seconds
            if self.silent>=self.silence_seconds:self.blocked=False;self.silent=0
            return []
        events=[]
        if not self.active:
            self.pre.append(audio);self.pre_bytes+=len(audio)
            while self.pre_bytes>10240:
                self.pre_bytes-=len(self.pre.popleft())
            self.candidate=self.candidate+seconds if speech else 0.
            if self.candidate+1e-9<self.onset_seconds:return []
            self.active=True;self.voiced=self.candidate;self.silent=0.
            self.audio=bytearray(b''.join(self.pre));self.pre.clear();self.pre_bytes=0
            events.append(SpeechEvent('onset'))
        else:
            self.audio.extend(audio)
            if speech:self.voiced+=seconds;self.silent=0.
            else:self.silent+=seconds
        truncated=len(self.audio)>=self.max_bytes
        if truncated or self.silent+1e-9>=self.silence_seconds:
            events.append(SpeechEvent('utterance',bytes(self.audio[:self.max_bytes]),self.voiced,truncated))
            self.audio.clear();self.active=False;self.candidate=0.;self.voiced=0.;self.silent=0.
            self.blocked=truncated
        return events


class EchoReference:
    """Correlation of local PCM energy shapes; not a proof of physical AEC.

    A local playback start observation supplies approximate alignment. Search a
    bounded450ms neighborhood to tolerate transport/codec startup variation.
    Unknown timing never becomes a positive echo identification.
    """
    def __init__(self, pcm):
        if not isinstance(pcm,bytes) or len(pcm)%2 or not 320<=len(pcm)<=RATE_BYTES*90:
            raise ValueError('invalid_reference_pcm')
        self.levels=envelopes(pcm)

    def is_echo(self, microphone, *, played_seconds):
        if played_seconds is None or not math.isfinite(played_seconds) or played_seconds<0:
            return False
        mic=envelopes(microphone[-12800:])
        if len(mic)<24:return False
        mean=sum(mic)/len(mic)
        centered=[x-mean for x in mic]
        energy=sum(x*x for x in centered)
        if energy<1e-6:return False
        expected=round(played_seconds*100)-len(mic)
        start=max(0,expected-45);end=min(len(self.levels)-len(mic),expected+45)
        for offset in range(start,end+1):
            ref=self.levels[offset:offset+len(mic)]
            ref_mean=sum(ref)/len(ref)
            values=[x-ref_mean for x in ref]
            ref_energy=sum(x*x for x in values)
            if ref_energy<1e-6:continue
            correlation=sum(x*y for x,y in zip(centered,values))/math.sqrt(energy*ref_energy)
            if correlation>.86:return True
        return False

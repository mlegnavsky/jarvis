"""One consented, bounded in-memory diagnostic. Audio is never serialized."""
import asyncio
from dataclasses import dataclass,field
import json
import math
import os
from pathlib import Path
import re
import stat
import threading
import time
import uuid

if __package__:
    from .speech_file import drain
else:
    from speech_file import drain

RATE=32000
MAX_PCM=3*1024*1024
REF_BUDGET=MAX_PCM-2*30*RATE


def erase(value):
    value[:]=bytes(len(value))
    try:value.clear()
    except BufferError:pass


@dataclass
class ReferenceData:
    pcm:bytearray=field(repr=False)
    started_at:float
    seen_until:float
    index:int


@dataclass
class CaptureData:
    raw:bytearray=field(repr=False)
    enhanced:bytearray=field(repr=False)
    references:list=field(repr=False)
    metadata:dict=field(default_factory=dict)
    abort:threading.Event=field(default_factory=threading.Event,repr=False)
    _guard:object=field(default_factory=threading.Lock,init=False,repr=False)
    _running:bool=field(default=False,init=False,repr=False)

    @property
    def pcm_bytes(self):return len(self.raw)+len(self.enhanced)+sum(len(r.pcm) for r in self.references)

    def wipe(self):
        erase(self.raw);erase(self.enhanced)
        for ref in self.references:erase(ref.pcm)
        self.references.clear()

    def begin_analysis(self):
        with self._guard:
            if self.abort.is_set():return False
            self._running=True
            return True

    def abort_analysis(self):
        with self._guard:
            self.abort.set()
            # A queued worker has no reader yet. Claiming this same lock before
            # reading prevents it from racing immediate expiry/discard erasure.
            if not self._running:self.wipe()


class Recorder:
    def __init__(self,read_output,*,clock=time.monotonic):
        self.read_output=read_output;self.clock=clock;self.state='waiting_for_playback'
        self.raw=bytearray();self.enhanced=bytearray();self.references=[];self.live=None
        self.raw_cursor=0;self.enhanced_cursor=0;self.start_sample=None;self.end_sample=None
        self.started_at=None;self.receives=[];self.vad=[];self.events=[]
        self.reference_bytes=0;self.reference_truncated=False;self.error=None

    def snapshot(self):
        return {'state':self.state,'seconds':round(len(self.raw)/RATE,3),
            'retained_audio_bytes':len(self.raw)+len(self.enhanced)+self.reference_bytes,
            'reference_count':len(self.references)+int(self.live is not None),
            'raw_audio_saved':False,'input_modified':False,'error_type':self.error}

    def fail(self,error='capture_invalid'):
        self.state='failed';self.error=error
        erase(self.raw);erase(self.enhanced)
        for ref in self.references:erase(ref.pcm)
        self.references.clear();self.reference_bytes=0;self.live=None

    def freeze_reference(self):
        if self.live is None:return
        obj,start,end,index=self.live;self.live=None
        room=max(0,REF_BUDGET-self.reference_bytes)
        wanted=max(0,round((end-start+2)*RATE))
        size=min(room,wanted);size-=size%2
        prefix=getattr(obj,'pcm_prefix',None)
        value=prefix(size) if prefix is not None else getattr(obj,'pcm',b'')[:size]
        if not isinstance(value,bytes):raise ValueError('invalid_reference')
        self.references.append(ReferenceData(bytearray(value),start,end,index))
        self.reference_bytes+=len(value)
        self.reference_truncated|=wanted>room

    def observe_output(self,now):
        output=self.read_output();owned=getattr(output,'owned',False)
        ref=getattr(output,'reference',None);start=getattr(output,'started_at',None)
        valid=owned and ref is not None and type(start) in (int,float) and math.isfinite(start)
        if self.live is not None and (not valid or self.live[0] is not ref):self.freeze_reference()
        if valid:
            if self.live is None:
                if len(self.references)>=8:self.reference_truncated=True;return
                self.live=[ref,float(start),now,len(self.references)]
            else:self.live[2]=now

    def observe_raw(self,audio,received_at):
        if self.state in ('failed','sealed','erased'):return
        try:
            if not isinstance(audio,bytes) or len(audio)%2 or len(audio)>65536 or not math.isfinite(received_at):
                raise ValueError('invalid_capture_frame')
            begin=self.raw_cursor;self.raw_cursor+=len(audio)//2
            if self.start_sample is None:
                output=self.read_output();start=getattr(output,'started_at',None)
                if not (getattr(output,'owned',False) and type(start) in (int,float)
                        and math.isfinite(start) and received_at>=start-.4):return
                self.start_sample=begin;self.end_sample=begin+30*16000
                self.started_at=received_at;self.state='capturing'
            if received_at<self.started_at:raise ValueError('capture_clock_rollback')
            if received_at-self.started_at>=30:self.end_sample=min(self.end_sample,begin)
            count=max(0,min(self.raw_cursor,self.end_sample)-max(begin,self.start_sample))
            if count:self.raw.extend(audio[:count*2])
            if len(self.receives)<320 and (not self.receives or begin-self.receives[-1][0]>=1600):
                self.receives.append([begin,round((received_at-self.started_at)*1000,3),len(audio)//2])
            if begin<self.end_sample:self.observe_output(received_at)
            if self.raw_cursor>=self.end_sample:self.state='captured'
        except Exception:self.fail('invalid_frame_or_reference')

    def observe_enhanced(self,frame):
        if self.state in ('failed','sealed','erased'):return
        try:
            audio=frame.audio
            if not isinstance(audio,bytes) or len(audio)%2 or len(audio)>65536:raise ValueError('invalid_enhanced_frame')
            begin=self.enhanced_cursor;self.enhanced_cursor+=len(audio)//2
            if self.start_sample is None:return
            low=max(begin,self.start_sample);high=min(self.enhanced_cursor,self.end_sample)
            if high<=low:return
            self.enhanced.extend(audio[(low-begin)*2:(high-begin)*2])
            probability=frame.speech_probability
            probability=round(float(probability),4) if type(probability) in (int,float) and math.isfinite(probability) else None
            if len(self.vad)<3000:self.vad.append([low-self.start_sample,probability])
        except Exception:self.fail('invalid_enhanced_frame')

    def mark_event(self,at):
        if self.start_sample is not None and math.isfinite(at) and len(self.events)<32:
            self.events.append(round((at-self.started_at)*1000,3))

    def finish(self):
        if self.state in ('failed','erased','sealed'):return None
        self.freeze_reference();self.state='sealed'
        data=CaptureData(self.raw,self.enhanced,self.references,
            {'start_sample':self.start_sample,'started_at':self.started_at,'receives':self.receives,
             'vad':self.vad,'event_ms':self.events,'reference_truncated':self.reference_truncated,
             'sample_rate':16000,'timing_origin':'first_received_sample_counts_not_hardware_clock'})
        self.raw=bytearray();self.enhanced=bytearray();self.references=[];self.reference_bytes=0
        if data.pcm_bytes>MAX_PCM:data.wipe();self.fail('capture_budget_exceeded');return None
        return data


class ScalarStore:
    def __init__(self,root):self.root=Path(root)
    def read(self,name):
        if self.root.is_symlink():raise ValueError('unsafe_capture_root')
        try:
            parent=os.open(self.root,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        except FileNotFoundError:return None
        try:
            try:fd=os.open(name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=parent)
            except FileNotFoundError:return None
            with os.fdopen(fd,'rb') as f:
                info=os.fstat(f.fileno())
                if not stat.S_ISREG(info.st_mode) or info.st_nlink!=1:raise ValueError('unsafe_capture_file')
                raw=f.read(245761)
            if len(raw)>245760:raise ValueError('capture_facts_too_large')
            return json.loads(raw)
        finally:os.close(parent)
    def write(self,name,facts):
        raw=json.dumps(facts,allow_nan=False,separators=(',',':')).encode()
        if len(raw)>245760:raise ValueError('capture_facts_too_large')
        if self.root.is_symlink():raise ValueError('unsafe_capture_root')
        self.root.mkdir(parents=True,exist_ok=True,mode=0o700)
        parent=os.open(self.root,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW);temporary='calibration-'+uuid.uuid4().hex+'.tmp'
        try:
            fd=os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=parent)
            with os.fdopen(fd,'wb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
            os.replace(temporary,name,src_dir_fd=parent,dst_dir_fd=parent)
        finally:
            try:os.unlink(temporary,dir_fd=parent)
            except FileNotFoundError:pass
            os.close(parent)
    def claim(self,nonce):
        old=self.read('calibration-state.json') or {'used':[]}
        used=old.get('used')
        if not isinstance(used,list) or any(not isinstance(x,str) or not re.fullmatch('[a-f0-9]{32}',x) for x in used):
            raise ValueError('invalid_capture_nonce_history')
        if nonce in used:return False
        self.write('calibration-state.json',{'used':(used+[nonce])[-16:]})
        return True


class CalibrationManager:
    def __init__(self,root,execute,*,clock=time.monotonic,utc=time.time,analyse=None,is_idle=lambda:True,ready=lambda:True):
        self.store=ScalarStore(root);self.execute=execute;self.clock=clock;self.utc=utc
        self.analyse=analyse;self.is_idle=is_idle;self.ready=ready;self.state='off';self.nonce=None;self.expires=0.
        self.recorder=None;self.data=None;self.analysis_task=None;self.timer=None;self.closed=False
        self.seconds=0.;self.error=None
        self.generation=0
    async def arm(self,nonce,expires_at):
        if (self.closed or not isinstance(nonce,str) or not re.fullmatch('[a-f0-9]{32}',nonce)
                or type(expires_at) not in (int,float) or not math.isfinite(expires_at)
                or not self.utc()<expires_at<=self.utc()+120):return False
        self.generation+=1;generation=self.generation
        try:claimed=await self.execute(self.store.claim,nonce)
        except Exception as error:
            if generation==self.generation and not self.closed:
                self.state='failed';self.error=type(error).__name__
            return False
        if self.closed or generation!=self.generation or not self.utc()<expires_at:return False
        if not claimed:return False
        if self.recorder is not None or self.analysis_task is not None and not self.analysis_task.done():return False
        if not self.ready():self.state='probe_required';return False
        self.nonce=nonce;self.expires=expires_at;self.state='armed';self.error=None
        if self.timer:self.timer.cancel()
        self.timer=asyncio.get_running_loop().call_later(max(0,expires_at-self.utc()),self.expire)
        return True
    def attach(self,read_output):
        if self.closed or self.state!='armed' or not self.utc()<self.expires:return None
        self.state='attached';self.recorder=Recorder(read_output,clock=self.clock)
        if self.timer:self.timer.cancel()
        self.timer=asyncio.get_running_loop().call_later(150,self.expire)
        return self.recorder
    def expire(self):
        self.state='expired'
        if self.recorder:self.recorder.fail('capture_expired');self.recorder=None
        if self.data:self.data.abort_analysis()
    def finish(self,recorder):
        if recorder is None or self.recorder is not recorder:return
        self.recorder=None;self.data=recorder.finish()
        if self.data is None:
            self.state='failed'
            if self.timer:self.timer.cancel();self.timer=None
            return
        self.seconds=len(self.data.raw)/RATE;self.state='waiting_for_idle'
        self.analysis_task=asyncio.create_task(self.run_analysis(self.data),name='jarvis-room-calibration')
    async def run_analysis(self,data):
        try:
            while not self.closed and not data.abort.is_set() and not self.is_idle():await asyncio.sleep(.1)
            if self.closed or data.abort.is_set():return
            self.state='analysing'
            def work():
                try:
                    if not data.begin_analysis():return {'status':'aborted'}
                    if self.analyse is None:
                        if __package__:from .calibration_analysis import analyse_capture
                        else:from calibration_analysis import analyse_capture
                        result=analyse_capture(data)
                    else:result=self.analyse(data)
                    return result
                except Exception as error:return {'status':'failed','error_type':type(error).__name__}
                finally:data.wipe()
            result,cancelled=await drain(self.execute(work))
            if self.closed or data.abort.is_set():return
            result={**result,'capture_id':self.nonce,'raw_audio_saved':False,'retained_audio_bytes':0}
            await self.execute(self.store.write,'calibration-result.json',result)
            self.state='complete' if result.get('status')=='complete' else result.get('status','failed')
            if cancelled:raise asyncio.CancelledError()
        except Exception as error:self.state='failed';self.error=type(error).__name__
        finally:
            data.wipe();self.data=None
            if self.timer:self.timer.cancel();self.timer=None
    def snapshot(self):
        captured=self.recorder.snapshot() if self.recorder else {}
        return {'state':captured.get('state',self.state),'capture_id':self.nonce,
            'expires_at':self.expires if self.state=='armed' else None,
            'captured_seconds':captured.get('seconds',self.seconds),
            'retained_audio_bytes':captured.get('retained_audio_bytes',self.data.pcm_bytes if self.data else 0),
            'raw_audio_saved':False,'input_modified':False,'error_type':self.error,
            'result_file':'jarvis_workspace/local_duplex/calibration-result.json'}
    async def probe(self,pcm):
        if __package__:from .calibration_analysis import calibration_probe
        else:from calibration_analysis import calibration_probe
        async with asyncio.timeout(5):return await self.execute(calibration_probe,pcm)
    async def discard(self):
        self.generation+=1
        if self.timer:self.timer.cancel();self.timer=None
        if self.recorder:self.recorder.fail('capture_closed');self.recorder=None
        if self.data:self.data.abort_analysis()
        if self.analysis_task is not None and not self.analysis_task.done():
            _result,cancelled=await drain(asyncio.gather(self.analysis_task,return_exceptions=True))
            if cancelled:raise asyncio.CancelledError()
        self.state='discarded'
    async def close(self):
        self.closed=True;await self.discard();self.state='off'

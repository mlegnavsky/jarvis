"""CPU-bounded waveform similarity facts; never an input/echo decision."""
import math
from array import array
from operator import mul
import time
import warnings

try:
    # Core3.14 pins audioop-lts0.2.2. Python3.12 test hosts use its stdlib predecessor.
    with warnings.catch_warnings():
        warnings.filterwarnings('ignore',message="'audioop' is deprecated.*",category=DeprecationWarning)
        from audioop import findfactor as _native_findfactor
except ImportError:
    _native_findfactor=None

if __package__:
    from .segmenter import samples
else:
    from segmenter import samples


def measure_waveform(microphone, reference, *, played_seconds, clock=time.perf_counter):
    started=clock();comparisons=0
    def result(status,**facts):
        finished=clock()
        if not math.isfinite(started) or not math.isfinite(finished) or finished<started:
            status='invalid_clock';facts={};elapsed=None
        else:
            elapsed=round((finished-started)*1000,3)
            if status=='measured' and finished-started>=.025:
                status='work_budget_exhausted';facts={}
        return {'status':status,'comparisons':comparisons,
            'processing_ms':elapsed,
            'kernel':'audioop_findfactor' if _native_findfactor is not None else 'python_dot',
            'acoustic_echo_proof':False,**facts}
    if (isinstance(played_seconds,bool) or not isinstance(played_seconds,(int,float))
            or not math.isfinite(played_seconds) or not 0<=played_seconds<=120):
        return result('invalid_timing')
    if (not isinstance(microphone,bytes) or not isinstance(reference,bytes)
            or len(microphone)%2 or len(reference)%2
            or len(microphone)>65536 or not 320<=len(reference)<=32000*90):
        return result('invalid_pcm')
    if len(microphone)<12800:return result('insufficient_audio')
    if played_seconds<.4:return result('insufficient_playback')
    count=200;rate=500
    expected=round((played_seconds-.4)*rate)
    first=max(0,expected-1000)
    last=min(len(reference)//64-count,expected+1000)
    if first>last:return result('insufficient_reference')
    # Only the relevant <=4.4s reference slice is decoded/averaged in the worker.
    raw=samples(microphone[-12800:])
    microphone=[round(sum(raw[i:i+32])/32) for i in range(0,len(raw),32)]
    raw=samples(reference[first*64:(last+count)*64])
    reference=[round(sum(raw[i:i+32])/32) for i in range(0,len(raw),32)]
    total_mic=sum(microphone);squared_mic=sum(x*x for x in microphone)
    power=squared_mic-total_mic*total_mic/count
    if power<1e-9:return result('no_variation')
    mic_pcm=array('h',microphone).tobytes();ref_pcm=array('h',reference).tobytes()
    prefix=[0];squares=[0]
    for value in reference:
        prefix.append(prefix[-1]+value);squares.append(squares[-1]+value*value)
    scores=[]
    for offset in range(last-first+1):
        if comparisons%16==0:
            current=clock()
            if not math.isfinite(current) or current<started:return result('invalid_clock')
            if current-started>=.025:return result('work_budget_exhausted')
        comparisons+=1
        total=prefix[offset+count]-prefix[offset]
        energy=squares[offset+count]-squares[offset]-total*total/count
        if energy<1e-9:continue
        if _native_findfactor is not None:
            dot=_native_findfactor(ref_pcm[offset*2:(offset+count)*2],mic_pcm)*squared_mic
        else:dot=sum(map(mul,microphone,reference[offset:offset+count]))
        score=(dot-total_mic*total/count)/math.sqrt(power*energy)
        scores.append((max(-1.,min(1.,score)),offset))
    if not scores:return result('no_reference_variation')
    score,offset=max(scores,key=lambda x:abs(x[0]))
    alternatives=[abs(value) for value,index in scores if abs(index-offset)>20]
    return result('measured',correlation=round(score,4),
        offset_ms=(expected-first-offset)*2,
        peak_margin=round(max(0.,abs(score)-max(alternatives)),4) if alternatives else None,
        alternative_count=len(alternatives),
        reference_window_sample=first+offset,window_ms=400,search_ms=2000,sample_rate=rate)

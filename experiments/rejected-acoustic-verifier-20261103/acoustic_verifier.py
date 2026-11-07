"""Positive-only generated-source verification; uncertainty preserves human input."""
import math
import time
import warnings
from array import array

try:
    with warnings.catch_warnings():
        warnings.filterwarnings('ignore',message="'audioop' is deprecated.*",category=DeprecationWarning)
        import audioop
except ImportError:
    audioop=None

if __package__:
    from .segmenter import samples
else:
    from segmenter import samples


def verify_own_audio(microphone,reference,*,played_seconds,clock=time.perf_counter):
    started=clock();minimum=None;blocks=0;offset=None;margin=None
    def result(status):
        elapsed=clock()-started
        if not math.isfinite(elapsed) or elapsed<0:status='invalid_clock'
        elif elapsed>=.15:status='work_budget_exhausted'
        return {'status':status,'own_audio':status=='own_audio','blocks':blocks,
            'min_correlation':round(minimum,4) if minimum is not None else None,
            'peak_margin':round(margin,4) if margin is not None else None,
            'offset_ms':round(offset/16,2) if offset is not None else None,
            'processing_ms':round(elapsed*1000,3) if math.isfinite(elapsed) else None}
    def check():
        now=clock()
        if not math.isfinite(now) or now<started or now-started>=.15:raise TimeoutError()
    if audioop is None:return result('native_unavailable')
    if (not isinstance(microphone,bytes) or not isinstance(reference,bytes)
            or len(microphone)%2 or len(reference)%2
            or not 12800<=len(microphone)<=32000*30 or not 12800<=len(reference)<=32000*90):
        return result('insufficient_audio')
    if (isinstance(played_seconds,bool) or not isinstance(played_seconds,(int,float))
            or not math.isfinite(played_seconds) or not 0<=played_seconds<=120):return result('invalid_timing')
    # One bounded utterance prefix establishes alignment; every captured block
    # must then agree. A short human insertion cannot be hidden by an average.
    count=len(microphone)//2;expected=round((played_seconds-count/16000)*16000)
    first=max(0,expected-32000);last=min(len(reference)//2-count,expected+32000)
    if first>last:return result('insufficient_reference')
    def emphasize(pcm):
        half=audioop.mul(pcm,2,.5)
        return audioop.add(half,audioop.mul(b'\0\0'+half[:-2],2,-.97),2)
    def decimate(pcm):
        a=samples(pcm)
        return array('h',(round(sum(a[i:i+8])/8) for i in range(0,len(a)-7,8))).tobytes()
    def correlation(a,b):
        a=audioop.bias(a,2,-audioop.avg(a,2));b=audioop.bias(b,2,-audioop.avg(b,2))
        if audioop.rms(a,2)<8 or audioop.rms(b,2)<8:return 0.
        product=audioop.findfactor(a,b)*audioop.findfactor(b,a)
        return math.sqrt(max(0.,min(1.,product)))
    def refine(mic,ref,predicted,slack=24):
        low=max(0,predicted-slack);high=min(len(ref)//2-len(mic)//2,predicted+slack)
        if high<low:return 0.,low
        at,_factor=audioop.findfit(ref[low*2:(high+len(mic)//2)*2],mic)
        at+=low
        return correlation(mic,ref[at*2:at*2+len(mic)]),at
    try:
        check();mic=emphasize(microphone);ref=emphasize(reference[first*2:(last+count)*2])
        lead=mic[:12800]
        coarse_ref=decimate(reference[first*2:(last+6400)*2])
        coarse_mic=decimate(microphone[:12800])
        check();coarse,_factor=audioop.findfit(coarse_ref,coarse_mic)
        score,at=refine(lead,ref,coarse*8);check()
        if score<.85:return result('different_audio')
        alternatives=[]
        for low,high in ((0,max(0,at//8-80)),(at//8+80,len(coarse_ref)//2-len(coarse_mic)//2)):
            if high<=low:continue
            p,_factor=audioop.findfit(coarse_ref[low*2:(high+len(coarse_mic)//2)*2],coarse_mic)
            value,_at=refine(lead,ref,(p+low)*8);alternatives.append(value);check()
        if not alternatives:return result('ambiguous')
        margin=score-max(alternatives)
        if margin<.1:return result('ambiguous')
        offset=expected-first-at
        for start in range(0,count,1280):
            block=mic[start*2:min(count,start+1280)*2]
            if len(block)<640:continue
            value,_at=refine(block,ref,at+start)
            blocks+=1;minimum=value if minimum is None else min(minimum,value);check()
            if value<.85:return result('different_audio')
        return result('own_audio' if blocks>=5 else 'insufficient_audio')
    except (TimeoutError,ValueError,OverflowError,audioop.error):return result('unavailable')

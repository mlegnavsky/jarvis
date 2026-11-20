"""On-device scalar calibration facts. Consistency never proves speaker identity."""
import cmath
import math
import time
import warnings
from array import array
from functools import lru_cache

try:
    with warnings.catch_warnings():
        warnings.filterwarnings('ignore',message="'audioop' is deprecated.*",category=DeprecationWarning)
        import audioop
except ImportError:audioop=None

if __package__:
    from .segmenter import samples
else:
    from segmenter import samples

N=512
HOP=160
BANDS=(0,250,500,1000,1500,2000,3000,4000,8000)
HANN=tuple(.5-.5*math.cos(2*math.pi*i/(N-1)) for i in range(N))

class InvalidClock(ValueError):pass


@lru_cache(maxsize=10)
def roots(size):return tuple(cmath.exp(-2j*math.pi*k/size) for k in range(size//2))


def fft(values):
    out=list(map(complex,values));count=len(out);j=0
    for i in range(1,count):
        bit=count>>1
        while j&bit:j^=bit;bit>>=1
        j^=bit
        if i<j:out[i],out[j]=out[j],out[i]
    width=2
    while width<=count:
        twiddle=roots(width);half=width//2
        for start in range(0,count,width):
            for k in range(half):
                a=out[start+k];b=out[start+k+half]*twiddle[k]
                out[start+k]=a+b;out[start+k+half]=a-b
        width*=2
    return out[:count//2+1]


def frames(pcm,check=lambda:None):
    values=samples(bytes(pcm));prepared=[]
    for start in range(0,len(values)-N+1,HOP):
        if len(prepared)%32==0:check()
        part=values[start:start+N];mean=sum(part)/N
        prepared.append([(value-mean)*weight for value,weight in zip(part,HANN)])
    try:import numpy as np
    except ImportError:return [fft(part) for part in prepared],'stdlib_radix2'
    if not prepared:return [],'numpy'
    return np.fft.rfft(np.asarray(prepared),axis=1),'numpy'


def coherence(microphone,reference,*,check=lambda:None):
    result={'status':'insufficient_audio','coherence':None,'source_identity_proof':False}
    if len(microphone)<12800 or len(reference)<12800:return result
    count=min(len(microphone),len(reference))
    a,kernel=frames(microphone[:count],check);b,_kernel=frames(reference[:count],check)
    count=min(len(a),len(b));check()
    if count<8:return result
    powers_a=[];powers_b=[];scores=[]
    for index in range(8,129):
        cross=0j;pa=0.;pb=0.
        for i in range(count):
            x=complex(a[i][index]);y=complex(b[i][index])
            cross+=x*y.conjugate();pa+=abs(x)**2;pb+=abs(y)**2
        powers_a.append(pa);powers_b.append(pb)
        scores.append(min(1.,abs(cross)**2/(pa*pb)) if pa*pb>1 else 0.)
    weights=[math.sqrt(x*y) for x,y in zip(powers_a,powers_b)];total=sum(weights)
    if total<1:return {**result,'status':'no_variation','kernel':kernel,'frames':count}
    value=sum(w*s for w,s in zip(weights,scores))/total
    effective=total*total/max(1.,sum(w*w for w in weights))
    energy=[]
    for row in b:energy.append(sum(abs(complex(v))**2 for v in row[8:129]))
    participation=sum(energy)**2/max(1.,sum(v*v for v in energy))
    bands=[]
    for low,high in zip(BANDS[:-1],BANDS[1:]):
        ids=[j for j in range(121) if low<=(j+8)*16000/N<high]
        denominator=sum(weights[j] for j in ids)
        bands.append(round(sum(weights[j]*scores[j] for j in ids)/denominator,4) if denominator>1 else None)
    return {'status':'measured','coherence':round(value,6),'effective_bins':round(effective,2),
        'energy_frame_participation':round(participation,2),'frames':count,
        'actual_duration_ms':round((N+(count-1)*HOP)/16,2),'subband_coherence':bands,
        'kernel':kernel,'source_identity_proof':False}


def emphasize(pcm):
    half=audioop.mul(bytes(pcm),2,.5)
    return audioop.add(half,audioop.mul(b'\0\0'+half[:-2],2,-.97),2)


def decimate(pcm):
    a=samples(bytes(pcm))
    return array('h',(round(sum(a[i:i+8])/8) for i in range(0,len(a)-7,8))).tobytes()


def correlation(a,b):
    a=audioop.bias(a,2,-audioop.avg(a,2));b=audioop.bias(b,2,-audioop.avg(b,2))
    if audioop.rms(a,2)<2 or audioop.rms(b,2)<2:return 0.
    product=audioop.findfactor(a,b)*audioop.findfactor(b,a)
    return math.sqrt(max(0.,min(1.,product)))


def band_rows(transforms):
    result=[]
    for row in transforms:
        result.append([math.log1p(sum(abs(complex(row[k]))**2 for k in range(max(1,math.ceil(low*N/16000)),min(N//2+1,math.ceil(high*N/16000)))))
            for low,high in zip(BANDS[:-1],BANDS[1:])])
    return result


def band_alignment(mic,reference,first,last,check):
    m=band_rows(mic);r=band_rows(reference);count=len(m)
    if count<8 or len(r)<count:return None,None,None
    mean=[sum(row[j] for row in m)/count for j in range(8)]
    centered=[[row[j]-mean[j] for j in range(8)] for row in m]
    energy=sum(x*x for row in centered for x in row)
    if energy<1e-9:return None,None,None
    low=max(0,first//HOP);high=min(len(r)-count,last//HOP);scores=[]
    for start in range(low,high+1):
        if (start-low)%16==0:check()
        rows=r[start:start+count];means=[sum(row[j] for row in rows)/count for j in range(8)]
        power=0.;dot=0.
        for left,right in zip(centered,rows):
            for j in range(8):
                value=right[j]-means[j];dot+=left[j]*value;power+=value*value
        if power>1e-9:scores.append((dot/math.sqrt(energy*power),start))
    if not scores:return None,None,None
    score,start=max(scores)
    other=[s for s,i in scores if abs(i-start)>10]
    return start*HOP,score,score-max(other) if other else None


def diagnose_pair(microphone,reference,expected_start_sample,*,clock=time.perf_counter,deadline=None,cache=None):
    began=clock();deadline=began+30 if deadline is None else deadline
    def check():
        now=clock()
        if not math.isfinite(began) or not math.isfinite(now) or now<began:raise InvalidClock()
        if now>=deadline:raise TimeoutError()
    result={'status':'unavailable','source_identity_proof':False,'waveform_lag_samples':None,
        'waveform_correlation':None,'coherence':None}
    try:
        check()
        if audioop is None:return {**result,'status':'native_unavailable'}
        if (len(microphone)!=12800 or len(reference)<len(microphone) or len(reference)%2
                or type(expected_start_sample) is not int):return {**result,'status':'insufficient_audio'}
        count=6400;first=max(0,expected_start_sample-40000)
        last=min(len(reference)//2-count,expected_start_sample+40000)
        if first>last:return {**result,'status':'insufficient_reference'}
        raw_ref=bytes(reference[first*2:(last+count)*2]);raw_mic=bytes(microphone)
        if audioop.rms(raw_mic,2)<2:return {**result,'status':'no_variation'}
        if audioop.rms(raw_ref,2)<2:return {**result,'status':'no_reference_variation'}
        coarse,_factor=audioop.findfit(decimate(raw_ref),decimate(raw_mic));check()
        mic=emphasize(raw_mic);ref=emphasize(raw_ref)
        def refine(prediction,radius):
            low=max(0,prediction-radius);high=min(len(ref)//2-count,prediction+radius)
            position,_factor=audioop.findfit(ref[low*2:(high+count)*2],mic)
            position+=low
            return first+position,correlation(mic,ref[position*2:(position+count)*2])
        at,score=refine(coarse*8,32);check()
        wave=coherence(raw_mic,reference[at*2:(at+count)*2],check=check)
        result.update(waveform_lag_samples=expected_start_sample-at,waveform_correlation=round(score,6),
            coherence=wave.get('coherence'),frames=wave.get('frames'),effective_bins=wave.get('effective_bins'),
            energy_frame_participation=wave.get('energy_frame_participation'),kernel=wave.get('kernel'),
            waveform_boundary_hit=at<=first+32 or at>=last-32)
        if cache is None:cache={}
        key=id(reference)
        if key not in cache:cache[key]=frames(reference,check)[0]
        mf,_kernel=frames(raw_mic,check)
        band_at,band_score,margin=band_alignment(mf,cache[key],first,last,check)
        if band_at is not None:
            refined,band_wave=refine(band_at-first,320);check()
            band_coh=coherence(raw_mic,reference[refined*2:(refined+count)*2],check=check)
            result.update(band_lag_samples=expected_start_sample-refined,band_score=round(band_score,6),
                band_peak_margin=round(margin,6) if margin is not None else None,
                band_runner_exclusion_ms=100,band_waveform_correlation=round(band_wave,6),
                band_coherence=band_coh.get('coherence'))
        result['status']='measured';check();result['processing_ms']=round((clock()-began)*1000,3)
        return result
    except TimeoutError:return {**result,'status':'work_budget_exhausted'}
    except InvalidClock:return {**result,'status':'invalid_clock'}
    except InterruptedError:return {**result,'status':'aborted'}
    except (ValueError,OverflowError,audioop.error if audioop else ValueError):return {**result,'status':'invalid_clock_or_signal'}


def analyse_capture(data,*,clock=time.perf_counter):
    start=clock();deadline=start+30;metadata=data.metadata
    def checked_clock():
        if data.abort.is_set():raise InterruptedError()
        return clock()
    result={'status':'complete','algorithm_version':1,'sample_rate':16000,'fft_samples':N,'hop_samples':HOP,
        'raw_samples':len(data.raw)//2,'enhanced_samples':len(data.enhanced)//2,
        'metadata':metadata,'references':[{'index':r.index,'samples':len(r.pcm)//2,
            'started_at':r.started_at,'seen_until':r.seen_until} for r in data.references],
        'windows':[],'source_identity_proof':False,'input_modified':False,'audio_saved':False}
    if not data.raw or metadata.get('started_at') is None:return {**result,'status':'no_audio'}
    offsets=[]
    for end_ms in metadata.get('event_ms',[]):
        for before in (1200,800,400):offsets.append(max(0,round((end_ms-before)*16/160)*160))
    offsets+=list(range(0,max(0,len(data.raw)//2-6400)+1,16000))
    offsets=list(dict.fromkeys(offsets))[:60];cache={}
    try:
        for offset in offsets:
            if data.abort.is_set():result['status']='aborted';break
            if clock()>=deadline:result['status']='work_budget_exhausted';break
            moment=metadata['started_at']+offset/16000
            for reference in data.references:
                if moment<reference.started_at-3 or moment>reference.seen_until+3:continue
                expected=round((moment-reference.started_at)*16000)
                for mode,audio in (('raw',data.raw),('enhanced',data.enhanced)):
                    chunk=audio[offset*2:(offset+6400)*2]
                    if len(chunk)!=12800:continue
                    facts=diagnose_pair(chunk,reference.pcm,expected,clock=checked_clock,deadline=deadline,cache=cache)
                    result['windows'].append({'offset_ms':offset/16,'mode':mode,'reference_index':reference.index,
                        'mic_rms':audioop.rms(chunk,2)/32768 if audioop else None,**facts})
                    if facts['status']=='work_budget_exhausted':result['status']='work_budget_exhausted';break
                if result['status']!='complete':break
            if result['status']!='complete':break
    finally:cache.clear()
    result['processing_ms']=round((clock()-start)*1000,3)
    return result


def calibration_probe(pcm):
    started=time.perf_counter();at=min(8000,max(0,len(pcm)//2-6400))
    facts=diagnose_pair(pcm[at*2:(at+6400)*2],pcm,at+20000)
    passed=(facts['status']=='measured' and facts.get('waveform_correlation',0)>.999
        and facts.get('coherence',0)>.999 and abs((facts.get('waveform_lag_samples') or 0)-20000)<=2)
    return {'status':'passed' if passed else 'failed','scope':'generated_reference_only_no_microphone',
        'processing_ms':round((time.perf_counter()-started)*1000,3),'facts':facts,'acoustic_echo_proof':False}

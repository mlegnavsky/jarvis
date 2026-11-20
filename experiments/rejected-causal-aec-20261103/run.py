"""Past-only candidate; generated audio only. No runtime imports or live IO."""
from pathlib import Path
import sys,json,time,resource
import numpy as np
from scipy.signal import resample_poly,fftconvolve
SRC=Path(__file__).resolve().parents[1]/'rejected-spectral-echo-20261103'
sys.path.insert(0,str(SRC));import spike as sp
ROOT=Path(__file__).parent;sp.ROOT=ROOT
FS=16000;RATE=4000;P=512
TEXTS=[
'A small boat left the quiet harbour before sunrise. Anna carried a map and a lantern. Her friend Daniel watched the water.',
'The morning wind moved the clouds. A narrow path led from the beach to a wooden door. Behind the door was a garden.',
'Every spring they repaired the paths and planted new trees. Anna opened her map and marked the safe route through the rocks.',
'The next morning they sailed home with a new map and a promise to return. Which part of their journey would you like to hear about next?',
'Please turn off the kitchen lights and stop speaking. I would like you to listen carefully to my next question before answering.',
'Weather patterns change quickly along the coast. People gather their umbrellas and hurry toward the nearest station when it begins to rain.',
'Our new project should finish on Friday. Before lunch we need to check the measurements and write down all of the remaining questions.',
'She placed the green notebook beside the old wooden table. He opened the window and listened to footsteps coming from the garden.']

def past_filter(ref,mic,cut_s):
 t=time.perf_counter();ncut=round(cut_s*FS)
 # Nothing after cut_s is read by alignment, model fitting or validation.
 xp=ref[:ncut];yp=mic[:ncut]
 try: loc=sp.metrics(xp,yp)
 except Exception:return dict(ready=False,reason='no_alignment',elapsed_ms=(time.perf_counter()-t)*1000),None
 lag=(loc['lag_ms']-16)*4
 x=resample_poly(xp,1,4);y=resample_poly(yp-350,1,4)
 # Never access target samples beyond the past boundary. Train first2.0s,
 # validate future .8s; full reference convolution remains causal.
 n=min(round(2.8*RATE),int((len(y)-lag-2)))
 if n<round(2.6*RATE):return dict(ready=False,reason='insufficient_past',elapsed_ms=(time.perf_counter()-t)*1000),None
 xx=x[:n];rows=np.arange(P-1,n);A=np.lib.stride_tricks.sliding_window_view(xx,P)[:,::-1].copy()
 train=rows<2*RATE;valid=(rows>=2*RATE)&(rows<2.8*RATE)
 at=A[train];gram=at.T@at;scale=np.trace(gram)/P
 erank=float(np.trace(gram)**2/max(np.sum(gram**2),1e-20))
 best=None
 for drift in (0,-80,80):
  target=np.interp(lag+np.arange(n)/(1+drift*1e-6),np.arange(len(y)),y)[P-1:]
  h=np.linalg.solve(gram+np.eye(P)*scale*1e-4,at.T@target[train])
  prediction=A[valid]@h;obs=target[valid]
  err=float(np.sum((obs-prediction)**2)/max(np.sum(obs**2),1e-20))
  item=(err,drift,h)
  if best is None or item[0]<best[0]:best=item
 err,drift,h=best
 ready=bool(loc['score']>=.65 and loc['rich']>=.8 and loc['rank']>=1.4 and erank>=5 and err<=.05)
 stats=dict(ready=ready,reason='validated' if ready else 'failed_past_validation',validation_error=err,validation_erle_db=float(-10*np.log10(max(err,1e-15))),lag_ms=loc['lag_ms'],trajectory=loc['score'],rich=loc['rich'],shape_rank=loc['rank'],gram_effective_rank=erank,drift_fit=drift,elapsed_ms=(time.perf_counter()-t)*1000,training_seconds=2.,past_validation_seconds=.8,past_cut_s=cut_s)
 model=(h,lag,drift) if ready else None
 return stats,model

def predict(ref,model,n):
 if model is None:return np.zeros(n)
 h,lag,drift=model
 x=resample_poly(ref,1,4);p=fftconvolve(x,h)[:len(x)]
 return np.interp((np.arange(n)/4-lag)*(1+drift*1e-6),np.arange(len(p)),p,left=0,right=0)

def metrics(e,h,p,a,b,guard=True):
 # Frozen coefficients; optional current power guard can only bypass subtraction.
 e=e[a:b];h=h[a:b];p=p[a:b].copy();pb=p.copy();mic=e+h
 bypass=False
 if guard and np.mean(p*p)>4*max(np.mean(mic*mic),1e-20):p[:]=0;bypass=True
 out=mic-p;res=e-p
 # Compare against processing the same echo without CURRENT human.
 # A current energy guard can itself change subtraction, so quantify it.
 if guard and np.mean(pb*pb)>4*max(np.mean(e*e),1e-20):pb[:]=0
 transfer=out-(e-pb)
 he=float(np.sum(h*h));ee=float(np.sum(e*e));outdiff=out-h
 return dict(echo_attenuation_db=float(10*np.log10(max(ee,1e-20)/max(np.sum(res*res),1e-20))),human_projection_gain=None if he<1e-15 else float(out@h/he),human_target_snr_db=None if he<1e-15 else float(10*np.log10(he/max(outdiff@outdiff,1e-20))),human_component_gain=None if he<1e-15 else float(transfer@h/he),human_component_error_ratio=None if he<1e-15 else float(np.sum((transfer-h)**2)/he),guard_bypass=bypass,echo_rms=float(np.sqrt(ee/max(len(e),1))),predicted_rms=float(np.sqrt(np.mean(p*p))),human_rms=float(np.sqrt(he/max(len(h),1))))

def dsp(e,which,delay):
 z=e.copy();start=round((delay+3.2)*FS)
 if which=='gain_down':z[start:]*=.25
 elif which=='gain_up':z[start:]*=2.
 elif which=='gate_future':
  q=np.sqrt(np.convolve(z*z,np.ones(160)/160,mode='same'));threshold=np.percentile(q[start:start+round(2*FS)],65);z[start:]*=(q[start:]>=threshold)
 elif which=='agc_all':
  q=np.sqrt(np.convolve(z*z,np.ones(320)/320,mode='same'));target=np.percentile(q[q>1],60) if np.any(q>1) else 1
  z*=np.clip(target/np.maximum(q,1),.25,4)
 return z

def main():
 began=time.perf_counter();rows=[];fits=[]
 voices=[sp.voice(t,('slt','rms','awb')[i%3],i) for i,t in enumerate(TEXTS)]
 stop=sp.voice('Stop. Stop speaking now. Listen to me please.','rms',90)
 for i,x in enumerate(voices):
  for room in (0,1,2):
   ref,mic,clean,meta=sp.echo(x,i,room);n=len(ref);delay=meta['delay_ms']/1000;cut=delay+2.8
   other=np.pad(voices[(i+3)%8],(0,n-len(x)))
   shifted=np.interp(np.arange(n)-delay*FS,np.arange(n),other,left=0,right=0)
   boot_end=round((delay+2.8)*FS);boot_start=round(delay*FS)
   for bootstrap in ('none','human_half','human_equal'):
    boot=np.zeros(n)
    if bootstrap!='none':
     q=.5 if bootstrap=='human_half' else 1.
     sl=slice(boot_start,boot_end);boot[sl]=shifted[sl]*q*np.sqrt(np.mean(clean[sl]**2))/max(np.sqrt(np.mean(shifted[sl]**2)),1e-20)
    stats,model=past_filter(ref,mic+boot,cut);fits.append(dict(clip=i,split='train' if i<4 else 'holdout',bootstrap=bootstrap,**meta,**stats))
    p=predict(ref,model,n)
    # Same model frozen throughout all CURRENT80–400ms variants; no current fit.
    for mode in ('linear','gain_down','gain_up','gate_future'):
     echo=dsp(clean,mode,delay)
     for width in (.08,.16,.4):
      for ratio in (0.,.5,1.):
       at=3.5;a=round((delay+at)*FS);b=a+round(width*FS);h=np.zeros(n)
       if ratio:
        hh=stop[round(.08*FS):round(.08*FS)+(b-a)].copy();hh*=ratio*np.sqrt(np.mean(echo[a:b]**2))/max(np.sqrt(np.mean(hh**2)),1e-20);h[a:b]=hh
       rows.append(dict(case='future',clip=i,split='train' if i<4 else 'holdout',room=room,bootstrap=bootstrap,dsp=mode,width_ms=width*1000,ratio=ratio,ready=stats['ready'],**metrics(echo,h,p,a,b)))
   # Nonlinear upstream AGC present during both training and future.
   ag=dsp(clean,'agc_all',delay);stats,model=past_filter(ref,ag+(mic-clean),cut);fits.append(dict(clip=i,split='train' if i<4 else 'holdout',bootstrap='agc_all',**meta,**stats));p=predict(ref,model,n)
   for ratio in (0.,.5,1.):
    a=round((delay+3.5)*FS);b=a+round(.08*FS);h=np.zeros(n)
    if ratio:h[a:b]=stop[1280:1280+(b-a)]*ratio*np.sqrt(np.mean(ag[a:b]**2))/max(np.sqrt(np.mean(stop[1280:1280+(b-a)]**2)),1e-20)
    rows.append(dict(case='future',clip=i,split='train' if i<4 else 'holdout',room=room,bootstrap='agc_all',dsp='agc_all',width_ms=80.,ratio=ratio,ready=stats['ready'],**metrics(ag,h,p,a,b)))
  print(json.dumps(dict(event='clip_done',clip=i,elapsed_s=time.perf_counter()-began,rows=len(rows))),flush=True)
  (ROOT/'results.json').write_text(json.dumps(dict(elapsed_s=time.perf_counter()-began,fit_stats=fits,rows=rows),indent=2))
 # Bootstrap stop from first playback sample: before a model is validated, pass through.
 for i in range(8):
  ref,mic,e,meta=sp.echo(voices[i],i,0);n=len(ref);a=round(meta['delay_ms']*16);b=a+1280;h=np.zeros(n);h[a:b]=stop[1280:2560];stats,model=past_filter(ref,mic+h,(a+1280)/FS);rows.append(dict(case='stop_from_start',clip=i,ready=stats['ready'],**metrics(e,h,predict(ref,model,n),a,b)))
 # Echo-free humans and periodic controls during all past/future windows.
 for i in range(8):
  ref,mic,e,meta=sp.echo(voices[i],i,0);n=len(ref);d=meta['delay_ms']/1000;other=np.pad(voices[(i+3)%8],(0,n-6*FS))
  for kind in ('independent','same_envelope'):
   h=other.copy()
   if kind=='same_envelope':h=sp.old.envmatch(ref,h)
   h=np.interp(np.arange(n)-d*FS,np.arange(n),h,left=0,right=0)
   stats,model=past_filter(ref,h+350,d+2.8);a=round((d+3.5)*FS);b=a+6400;rows.append(dict(case=kind,clip=i,human_output_error_ratio=float(np.sum(predict(ref,model,n)[a:b]**2)/max(np.sum(h[a:b]**2),1e-20)),**stats))
 t=np.arange(10*FS)/FS;env=.6+.4*np.sin(2*np.pi*2*t)
 for k in range(3):
  x=sum(np.sin(2*np.pi*j*140*t)/j for j in range(1,21))*env*2500
  y=sum(np.sin(2*np.pi*j*140*t+j*.913)/j for j in range(1,21))*env*2500
  stats,model=past_filter(x,y+350,4.);rows.append(dict(case='same_F0_phase',clip=k,**stats))
 for name,xx,yy in [('silence',np.zeros(4*FS),np.zeros(4*FS)+350),('dc',np.ones(4*FS)*1000,np.ones(4*FS)*700+350)]:
  stats,model=past_filter(xx,yy,4.);rows.append(dict(case=name,**stats))
 result=dict(elapsed_s=time.perf_counter()-began,fit_stats=fits,rows=rows,max_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
 (ROOT/'results.json').write_text(json.dumps(result,indent=2));print(json.dumps(dict(event='done',elapsed_s=result['elapsed_s'],rows=len(rows),fits=len(fits),max_rss_kib=result['max_rss_kib'])),flush=True)
if __name__=='__main__':main()

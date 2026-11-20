from __future__ import annotations
import sys, json, time, subprocess, importlib.util
from pathlib import Path
import numpy as np
from scipy.signal import fftconvolve, butter, sosfilt
sys.path.insert(0,str(Path(__file__).parent))
import helpers as old
FS=16000; HOP=160; FFT=512; ROOT=Path(__file__).parent
F=np.fft.rfftfreq(FFT,1/FS); E=700*(10**(np.linspace(2595*np.log10(1+180/700),2595*np.log10(1+6000/700),33)/2595)-1)
B=[np.flatnonzero((F>=a)&(F<b)) for a,b in zip(E[:-1],E[1:])]
WIN=np.hanning(FFT)
def feat(a):
 z=old.stft(a); p=abs(z)**2
 q=np.stack([np.mean(p[:,i],axis=1) for i in B],axis=1)
 floor=np.maximum(q.max(axis=0)*1e-5,1e-10)
 return np.log(np.maximum(q,floor)), q.sum(axis=1)
def align(x,y):
 xx,ex=feat(x); yy,ey=feat(y); pairs=[]
 for lag in range(-300,301):
  a=max(0,-lag); b=min(len(xx),len(yy)-lag)
  if b-a<100:continue
  active=ex[a:b]>ex.max()*1e-3
  z=old.corr_features(xx[a:b],yy[a+lag:b+lag],active)
  if z:pairs.append((z[0],lag))
 pairs.sort(reverse=True)
 score,lag=pairs[0]
 return lag*HOP,score,score-next((z[0] for z in pairs[1:] if abs(z[1]-lag)>10),-1)
def metrics(x,y,lag=None):
 t=time.perf_counter()
 if lag is None:lag,_,margin=align(x,y)
 else: margin=None
 best=None
 for off in range(-96,97,16):
  L=lag+off;a=max(0,-L);b=min(len(x),len(y)-L)
  xx,ex=feat(x[a:b]);yy,ey=feat(y[a+L:b+L]);act=ex>ex.max()*1e-3
  pair=old.corr_features(xx,yy,act)
  if pair and (best is None or pair[0]>best[0]):best=(pair[0],L,xx,yy,ex,ey,act)
 score,lag,xx,yy,ex,ey,act=best
 # Per-band channel offset cancels stationary filtering and gain.
 delta=yy-xx; delta-=np.median(delta[act],axis=0)
 # Candidate max local residual. All frames retained except shared low energy.
 residual=np.sqrt(np.mean(delta**2,axis=1))
 active=(ex>ex.max()*1e-3)|(ey>ey.max()*1e-3)
 local=np.convolve(residual*active,np.ones(8),mode='valid')/np.maximum(np.convolve(active.astype(float),np.ones(8),mode='valid'),1)
 valid=np.convolve(active.astype(float),np.ones(8),mode='valid')>=6
 local=local[valid]
 shape=xx[act]-xx[act].mean(axis=1,keepdims=True);shape-=shape.mean(axis=0)
 eig=np.linalg.eigvalsh(shape.T@shape/max(1,len(shape)))
 rank=float(eig.sum()**2/max(np.sum(eig**2),1e-15));rich=float(np.sqrt(np.mean(shape**2)))
 return dict(score=float(score),margin=margin,lag_ms=lag/16,rich=rich,rank=rank,r80_max=float(local.max()),r80_p95=float(np.percentile(local,95)),r80_median=float(np.median(local)),elapsed_ms=(time.perf_counter()-t)*1000)
def voice(text,voice,i):
 path=ROOT/f'text{i}.txt';path.write_text(text)
 r=subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-f','lavfi','-i',f'flite=textfile={path}:voice={voice}','-ac','1','-ar','16000','-f','s16le','pipe:1'],capture_output=True,check=True)
 x=np.frombuffer(r.stdout,np.int16).astype(float)
 # Vary clips, retaining natural phrase timing. 6 s cropped/padded, speech starts immediately.
 x=np.pad(x,(0,max(0,6*FS-len(x))))[:6*FS]
 x*=3200/max(np.sqrt(np.mean(x*x)),1)
 return x
def echo(x,seed,roomid=0):
 n=len(x)+FS*4;ref=np.pad(x,(0,n-len(x)))
 delay=(1.253,2.347,.777,1.7)[seed%4];drift=(0,80,-80)[seed%3];gain=(.2,.7,1.2)[seed%3]
 sampled=np.interp((np.arange(n)-delay*FS)*(1+drift*1e-6),np.arange(n),ref,left=0,right=0)
 rng=np.random.default_rng(seed+5432)
 if roomid==0:
  room=np.zeros(1380);room[[0,297,877,1379]]=[.58,.19,-.1,.055]
 else:
  room=rng.normal(size=3200)*np.exp(-np.arange(3200)/(500 if roomid==1 else 900))*.012
  room[0]+=.55;room[263]+=.25;room[873]-=.15;room[1600]+=.08
 out=fftconvolve(sampled,room)[:n]
 hp=(0,150,300,500)[(seed+roomid)%4]
 if hp:out=sosfilt(butter(3,hp,btype='highpass',fs=FS,output='sos'),out)
 out*=gain
 mic=out+rng.normal(0,8,n)+350
 return ref,mic,out,dict(delay_ms=delay*1000,drift_ppm=drift,gain=gain,highpass_hz=hp,room=roomid)
def main():
 begin=time.perf_counter();rows=[]
 texts=[
 'A small boat left the quiet harbour before sunrise. Anna carried a map and a lantern. Her friend Daniel watched the water.',
 'The morning wind moved the clouds. A narrow path led from the beach to a wooden door. Behind the door was a garden.',
 'Every spring they repaired the paths and planted new trees. Anna opened her map and marked the safe route through the rocks.',
 'The next morning they sailed home with a new map and a promise to return. Which part of their journey would you like to hear about next?',
 'Please turn off the kitchen lights and stop speaking. I would like you to listen carefully to my next question before answering.',
 'Weather patterns change quickly along the coast. People gather their umbrellas and hurry toward the nearest station when it begins to rain.',
 'Our new project should finish on Friday. Before lunch we need to check the measurements and write down all of the remaining questions.',
 'She placed the green notebook beside the old wooden table. He opened the window and listened to footsteps coming from the garden.']
 voices=[voice(txt,('slt','rms','awb')[i%3],i) for i,txt in enumerate(texts)]
 print(json.dumps({'event':'voices_ready','elapsed_s':time.perf_counter()-begin}),flush=True)
 cache={}
 for i,x in enumerate(voices):
  for roomid in (0,1,2):
   ref,mic,clean,meta=echo(x,i,roomid);m=metrics(ref,mic);cache[i,roomid]=(ref,mic,clean,meta,m)
   rows.append(dict(case='echo',clip=i,split='train' if i<4 else 'holdout',**meta,**m))
 print(json.dumps({'event':'echo_done','n':len(rows),'elapsed_s':time.perf_counter()-begin,'score_min':min(r['score'] for r in rows),'r80_max':max(r['r80_max'] for r in rows)}),flush=True)
 for i,x in enumerate(voices):
  ref,mic,clean,meta,baseline=cache[i,1]; n=len(ref);delay=meta['delay_ms']/1000
  h=np.pad(voices[(i+3)%8],(0,n-len(x)))
  for label,hh in [('different_words',h),('same_words',voice(texts[i],('rms' if i%3==0 else 'slt'),100+i))]:
   hh=np.pad(hh,(0,max(0,n-len(hh))))[:n]
   shifted=np.interp(np.arange(n)-delay*FS,np.arange(n),hh,left=0,right=0)
   rows.append(dict(case=label,clip=i,split='train' if i<4 else 'holdout',**metrics(ref,shifted+350)))
   matched=old.envmatch(ref,hh)
   shifted=np.interp(np.arange(n)-delay*FS,np.arange(n),matched,left=0,right=0)
   rows.append(dict(case='exact_envelope_'+label,clip=i,split='train' if i<4 else 'holdout',**metrics(ref,shifted+350)))
  for roomid in (0,1,2):
   ref,mic,clean,meta,baseline=cache[i,roomid]
   for width in (.08,.16,.4):
    for ratio in (.5,1.):
     # Human snippets positioned inside voiced portions, at two independent points.
     for at in (1.8,3.5):
      a=round((meta['delay_ms']/1000+at)*FS);b=a+round(width*FS)
      hh=voices[(i+3)%8][round(.7*FS):round(.7*FS)+(b-a)].copy()
      hh*=ratio*np.sqrt(np.mean(clean[a:b]**2))/max(np.sqrt(np.mean(hh**2)),1e-9)
      mixed=mic.copy();mixed[a:b]+=hh
      m=metrics(ref,mixed,round(baseline['lag_ms']*16))
      rows.append(dict(case='mixed',clip=i,split='train' if i<4 else 'holdout',width_ms=width*1000,ratio=ratio,at_s=at,**meta,**m))
  print(json.dumps({'event':'clip_done','clip':i,'n':len(rows),'elapsed_s':time.perf_counter()-begin}),flush=True)
 # Same F0 with phase differences, exactly same envelope, cannot supply rich trajectories.
 t=np.arange(6*FS)/FS
 for variant in (0,1,2):
  env=(.6+.4*np.sin(2*np.pi*2*t))
  x=sum(np.sin(2*np.pi*k*140*t)/k for k in range(1,21))*env*2500
  y=sum(np.sin(2*np.pi*k*140*t+(k*.913 if variant else np.pi/2))/k for k in range(1,21))*env*2500
  if variant==2:x*=.8+.2*np.sin(2*np.pi*.7*t);y=old.envmatch(x,y)
  rows.append(dict(case='same_F0_phase',clip=variant,**metrics(x,y)))
 result=dict(elapsed_s=time.perf_counter()-begin,rows=rows)
 (ROOT/'results.json').write_text(json.dumps(result,indent=2))
 print(json.dumps({'event':'done','elapsed_s':result['elapsed_s'],'rows':len(rows)}),flush=True)
if __name__=='__main__':main()

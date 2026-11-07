"""Limited held-out causal FIR feasibility, 4kHz, no live or production writes."""
import sys,json,time
from pathlib import Path
import numpy as np
from scipy.signal import resample_poly
sys.path.insert(0,str(Path(__file__).parent));import spike
FS=4000;P=384;ROOT=Path(__file__).parent

def fitmetrics(ref,mic,lag_ms,drift_grid=(0,-80,80)):
 started=time.perf_counter();x=resample_poly(ref,1,4);y=resample_poly(mic-350,1,4)
 lag=(lag_ms-16)*4; best=None
 # 6 second reference speech; fixed fold assignment by disjoint 80ms blocks.
 n=min(len(x),6*FS);x=x[:n];rows=np.arange(P-1,n);fold=(rows//320)%2
 A=np.lib.stride_tricks.sliding_window_view(x,P)[:,::-1].copy()
 Ax=[A[fold==f] for f in (0,1)]
 # Reference-tail restriction affects each holdout metric equally.
 xx=[a.T@a for a in Ax]
 scale=np.trace(xx[0])/P
 for drift in drift_grid:
  ywarp=np.interp(lag+np.arange(n)/(1+drift*1e-6),np.arange(len(y)),y,left=0,right=0)[P-1:]
  residual=np.zeros(len(ywarp));predict=np.zeros(len(ywarp))
  for f in (0,1):
   h=np.linalg.solve(xx[1-f]+np.eye(P)*scale*1e-5,Ax[1-f].T@ywarp[fold==1-f])
   predict[fold==f]=Ax[f]@h
  residual=ywarp-predict
  mean=float(np.sum(residual**2)/max(np.sum(ywarp**2),1e-20))
  block=[]
  for a in range(0,len(rows)-320+1,160):
   sl=slice(a,a+320); en=np.mean(ywarp[sl]**2)
   if en>np.max(ywarp**2)*1e-4:
    block.append(float(np.mean(residual[sl]**2)/max(en,1e-20)))
  result=dict(mean_residual=mean,max80=max(block),p95_80=float(np.percentile(block,95)),drift_fit=drift)
  if best is None or result['mean_residual']<best['mean_residual']:best=result
 best['elapsed_ms']=(time.perf_counter()-started)*1000
 return best

def main():
 begin=time.perf_counter();rows=[]
 texts=['A small boat left the quiet harbour before sunrise. Anna carried a map and a lantern. Her friend Daniel watched the water.',
 'The morning wind moved the clouds. A narrow path led from the beach to a wooden door. Behind the door was a garden.',
 'Every spring they repaired the paths and planted new trees. Anna opened her map and marked the safe route through the rocks.',
 'The next morning they sailed home with a new map and a promise to return. Which part of their journey would you like to hear about next?',
 'Please turn off the kitchen lights and stop speaking. I would like you to listen carefully to my next question before answering.',
 'Weather patterns change quickly along the coast. People gather their umbrellas and hurry toward the nearest station when it begins to rain.',
 'Our new project should finish on Friday. Before lunch we need to check the measurements and write down all of the remaining questions.',
 'She placed the green notebook beside the old wooden table. He opened the window and listened to footsteps coming from the garden.']
 voices=[spike.voice(t,('slt','rms','awb')[i%3],i) for i,t in enumerate(texts)]
 prior=json.loads((ROOT/'results.json').read_text())['rows']
 for i,x in enumerate(voices):
  for room in (0,1,2):
   ref,mic,clean,meta=spike.echo(x,i,room)
   lag=next(r['lag_ms'] for r in prior if r['case']=='echo' and r['clip']==i and r['room']==room)
   base=fitmetrics(ref,mic,lag);rows.append(dict(case='echo',clip=i,split='train' if i<4 else 'holdout',**meta,**base))
   # 80ms, 0.5x is the weakest target; extend only if it separates.
   for width in (.08,.16,.4):
    for ratio in (.5,1.):
     at=1.8;a=round((meta['delay_ms']/1000+at)*16000);b=a+round(width*16000)
     hh=voices[(i+3)%8][11200:11200+(b-a)].copy()
     hh*=ratio*np.sqrt(np.mean(clean[a:b]**2))/max(np.sqrt(np.mean(hh**2)),1e-9)
     mixed=mic.copy();mixed[a:b]+=hh
     m=fitmetrics(ref,mixed,lag)
     rows.append(dict(case='mixed',clip=i,split='train' if i<4 else 'holdout',width_ms=width*1000,ratio=ratio,**meta,**m))
  (ROOT/'fir-results.json').write_text(json.dumps(dict(elapsed_s=time.perf_counter()-begin,rows=rows),indent=2))
  print(json.dumps({'event':'fir_clip_done','clip':i,'elapsed_s':time.perf_counter()-begin,'rows':len(rows)}),flush=True)
if __name__=='__main__':main()

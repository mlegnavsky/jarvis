"""Numerical experiment helpers; never imported by runtime."""
import numpy as np
FFT=512; HOP=160; WIN=np.hanning(FFT)

def stft(a):
 a=np.asarray(a,float)
 frames=np.lib.stride_tricks.sliding_window_view(a,FFT)[::HOP]
 frames=frames-frames.mean(axis=1,keepdims=True)
 return np.fft.rfft(frames*WIN,axis=1)

def corr_features(x,y,active):
 # Candidate-wise temporal normalization, average across usable log bands.
 x=x[active];y=y[active]
 if len(x)<40:return None
 x=x-x.mean(axis=0);y=y-y.mean(axis=0)
 ex=np.sum(x*x,axis=0);ey=np.sum(y*y,axis=0)
 valid=(ex>1e-4)&(ey>1e-4)
 if np.count_nonzero(valid)<6:return None
 cc=np.sum(x*y,axis=0)[valid]/np.sqrt(ex[valid]*ey[valid])
 return float(np.mean(cc)),len(x)

def envmatch(ref,human):
 # Exactly match each 10 ms block RMS, using independent voice phase/pitch.
 out=human.copy()
 for a in range(0,len(ref)-HOP+1,HOP):
  xr=np.sqrt(np.mean(ref[a:a+HOP]**2));hr=np.sqrt(np.mean(human[a:a+HOP]**2))
  out[a:a+HOP]*=xr/max(hr,1e-9)
 return out

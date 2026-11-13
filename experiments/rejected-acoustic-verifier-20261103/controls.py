import sys,json
from acoustic_verifier import verify_own_audio
from fixture import speech_like,pcm
from scipy.signal import butter,sosfilt
import numpy as np
room=np.zeros(1400);room[[0,297,877,1379]]=[.58,.19,-.10,.055]
for seed in [52,53,54,71,72]:
 r=speech_like(5,seed);echo=np.convolve(r,room)[:len(r)];start=20003;raw=r[start:start+16000]
 h=speech_like(1,seed+918273)
 for cutoff in [0,150,300]:
  er=echo if not cutoff else sosfilt(butter(3,cutoff,fs=16000,btype='highpass',output='sos'),echo)
  mic=er[start:start+16000]
  for case,m in [('echo',mic),('independent',h),('double_talk',mic+h*.8)]:
   print(json.dumps(dict(seed=seed,hp=cutoff,case=case,**verify_own_audio(pcm(m).tobytes(),pcm(r).tobytes(),played_seconds=3.2))))

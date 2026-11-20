"""Single-thread local multilingual CAMPPlus speaker embeddings, no storage."""
from pathlib import Path
import hashlib
import time
import wave
import numpy as np
import sherpa_onnx

MODEL_SHA='aa3cfc16963a10586a9393f5035d6d6b57e98d358b347f80c2a30bf4f00ceba2'
MODEL_ID='campplus-aa3cfc16-v1'
def quality(pcm):
 if len(pcm)>384000 or len(pcm)%2:raise ValueError('invalid_pcm_size')
 seconds=len(pcm)/32000
 if seconds<2.5:return {'status':'too_short','seconds':seconds}
 x=np.frombuffer(pcm,dtype='<i2').astype(np.float32)/32768
 rms=float(np.sqrt(np.mean(x*x)))
 clipped=float(np.mean(np.abs(x)>=.995))
 status='quiet' if rms<.004 else 'clipped' if clipped>.02 else 'ok'
 return {'status':status,'seconds':round(seconds,3),'rms':round(rms,5),'clipped_fraction':round(clipped,5)}

class Extractor:
 def __init__(self,model):
  if hashlib.sha256(Path(model).read_bytes()).hexdigest()!=MODEL_SHA:raise ValueError('model_checksum')
  self.extractor=sherpa_onnx.SpeakerEmbeddingExtractor(sherpa_onnx.SpeakerEmbeddingExtractorConfig(model=str(model),num_threads=1,provider='cpu'))
 def vector(self,pcm):
  stream=self.extractor.create_stream()
  x=np.frombuffer(pcm,dtype='<i2').astype(np.float32)/32768
  stream.accept_waveform(sample_rate=16000,waveform=x);stream.input_finished()
  if not self.extractor.is_ready(stream):raise ValueError('not_ready')
  v=np.array(self.extractor.compute(stream),dtype=np.float64)
  if not np.all(np.isfinite(v)) or np.linalg.norm(v)<1e-8:raise ValueError('invalid_embedding')
  return (v/np.linalg.norm(v)).tolist()
 def process(self,pcm):
  q=quality(pcm)
  if q['status']!='ok':return {'status':q['status'],'quality':q,'model':MODEL_ID}
  start=time.monotonic();v=self.vector(pcm);windows=[]
  if len(pcm)>=192000:
   middle=(len(pcm)//4)*2
   windows=[self.vector(pcm[:middle]),self.vector(pcm[middle:])]
   consistency=sum(a*b for a,b in zip(*windows))
   if consistency<.55:return {'status':'inconsistent','quality':q,'model':MODEL_ID}
  return {'status':'ok','vector':v,'windows':windows,'quality':q,'model':MODEL_ID,'inference_ms':round((time.monotonic()-start)*1000,1)}
 def probe(self,folder):
  names=['fangjun-sr-1.wav','fangjun-test-sr-1.wav','leijun-sr-1.wav','leijun-test-sr-1.wav']
  vectors=[];start=time.monotonic()
  for name in names:
   with wave.open(str(Path(folder)/name)) as wav:
    if (wav.getnchannels(),wav.getsampwidth(),wav.getframerate())!=(1,2,16000):raise ValueError('fixture_format')
    vectors.append(self.vector(wav.readframes(wav.getnframes())))
  cos=lambda a,b:sum(x*y for x,y in zip(vectors[a],vectors[b]))
  same_a=cos(0,1);same_b=cos(2,3);cross=max(cos(a,b) for a in (0,1) for b in (2,3))
  return {'passed':same_a>.75 and same_b>.60 and cross<.5,'same_a':round(same_a,4),'same_b':round(same_b,4),
          'maximum_cross':round(cross,4),'elapsed_ms':round((time.monotonic()-start)*1000,1),
          'scope':'four upstream public speech fixtures; not household accuracy'}

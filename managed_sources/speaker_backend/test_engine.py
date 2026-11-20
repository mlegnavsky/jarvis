import unittest
import numpy as np
from engine import quality
class AudioTests(unittest.TestCase):
 def test_silence_short_and_clipped_audio_rejected(self):
  self.assertEqual(quality(bytes(16000*2*4))['status'],'quiet')
  self.assertEqual(quality(bytes(100))['status'],'too_short')
  pcm=np.full(16000*4,32767,dtype='<i2').tobytes()
  self.assertEqual(quality(pcm)['status'],'clipped')
 def test_bounded_pcm_requires_complete_samples(self):
  for data in [bytes(384002),bytes(100001)]:
   with self.assertRaises(ValueError):quality(data)

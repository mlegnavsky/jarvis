import importlib
import math
import unittest
from test_waveform_observer import pcm, shaped
from segmenter import samples


class AcousticVerifierTests(unittest.TestCase):
    def verify(self,mic,ref,played=3.2,**kw):
        try:module=importlib.import_module('acoustic_verifier')
        except ModuleNotFoundError:self.fail('independent acoustic source verifier missing')
        return module.verify_own_audio(mic,ref,played_seconds=played,**kw)

    def test_actual_source_accepted_at_finer_than_old_two_ms_resolution(self):
        ref=shaped(52,5)
        start=20003
        mic=pcm(round(x*.6) for x in samples(ref[start*2:(start+16000)*2]))
        facts=self.verify(mic,ref,clock=lambda:0.)
        self.assertTrue(facts['own_audio'],facts)
        self.assertAlmostEqual(facts['offset_ms'],(3.2-1-start/16000)*1000,delta=1)

    def test_same_envelope_independent_source_is_never_accepted(self):
        for seed in (71,72,73):
            self.assertFalse(self.verify(shaped(seed,1),shaped(52,5),clock=lambda:0.)['own_audio'])

    def test_short_human_in_middle_of_echo_remains_eligible(self):
        ref=shaped(52,5);start=20003
        base=list(samples(ref[start*2:(start+16000)*2]));human=list(samples(shaped(81,1)))
        for i in range(6000,7280):base[i]=round(.5*base[i]+.7*human[i])
        self.assertFalse(self.verify(pcm(base),ref,clock=lambda:0.)['own_audio'])

    def test_repeated_tone_does_not_establish_a_source(self):
        ref=pcm(round(5000*math.sin(2*math.pi*180*i/16000)) for i in range(80000))
        self.assertFalse(self.verify(ref[32000:64000],ref,clock=lambda:0.)['own_audio'])

    def test_quiet_short_invalid_and_expired_are_unknown(self):
        ref=shaped(52,5)
        for mic,played in ((bytes(32000),3.2),(shaped(52,.1),3.2),(ref[:32000],float('nan'))):
            self.assertFalse(self.verify(mic,ref,played,clock=lambda:0.)['own_audio'])
        ticks=iter([0.,.2,.2])
        self.assertFalse(self.verify(ref[:32000],ref,clock=lambda:next(ticks,.2))['own_audio'])

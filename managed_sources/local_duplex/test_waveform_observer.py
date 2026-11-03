import array
import importlib
import json
import math
import random
import sys
import unittest


def pcm(values):
    data=array.array('h',values)
    if sys.byteorder!='little':data.byteswap()
    return data.tobytes()


def shaped(seed,seconds=4):
    # Independent sample signs have identical per10ms RMS for the same envelope.
    rng=random.Random(seed)
    return pcm((1 if rng.getrandbits(1) else -1)*(1000+(i//160*331)%6000)
               for i in range(round(16000*seconds)))


class WaveformObserverTests(unittest.TestCase):
    def test_generated_reference_retains_immutable_pcm_for_optional_probe(self):
        data=shaped(4,1)
        reference=importlib.import_module('segmenter').EchoReference(data)
        self.assertIs(getattr(reference,'pcm',None),data)

    def measure(self,microphone,reference,**kwargs):
        try:module=importlib.import_module('waveform_observer')
        except ModuleNotFoundError as exc:
            if exc.name=='waveform_observer':self.fail('bounded raw-waveform observer is missing')
            raise
        return module.measure_waveform(microphone,reference,**kwargs)

    def delayed(self,reference,delay=1.25,played=2.7):
        received=(bytes(round(delay*32000))+reference)[:round(played*32000)]
        return received[-12800:]

    def test_raw_pcm_delay_beyond_rms_gate_is_measured(self):
        reference=shaped(42)
        mic=self.delayed(reference)
        result=self.measure(mic,reference,played_seconds=2.7,clock=lambda:0.)
        self.assertEqual(result['status'],'measured')
        self.assertEqual(result['offset_ms'],1250)
        self.assertGreater(result['correlation'],.999)
        self.assertGreater(result['peak_margin'],.4)

    def test_independent_waveform_with_identical_energy_envelope_is_different(self):
        reference=shaped(42)
        mic=self.delayed(shaped(81))
        result=self.measure(mic,reference,played_seconds=2.7,clock=lambda:0.)
        self.assertEqual(result['status'],'measured')
        self.assertLess(abs(result['correlation']),.6)
        self.assertFalse(result['acoustic_echo_proof'])
        self.assertNotIn('is_echo',result)

    def test_inverted_scaled_waveform_retains_polarity(self):
        reference=shaped(99)
        inverted=pcm(round(-.35*x) for x in importlib.import_module('segmenter').samples(reference))
        result=self.measure(self.delayed(inverted),reference,played_seconds=2.7,clock=lambda:0.)
        self.assertEqual(result['status'],'measured')
        self.assertEqual(result['offset_ms'],1250)
        self.assertLess(result['correlation'],-.999)

    def test_periodic_waveform_reports_ambiguous_peak(self):
        reference=pcm(round(6000*math.sin(2*math.pi*100*i/16000)) for i in range(64000))
        result=self.measure(self.delayed(reference),reference,played_seconds=2.7,clock=lambda:0.)
        self.assertEqual(result['status'],'measured')
        self.assertLess(result['peak_margin'],.001)
        self.assertFalse(result['acoustic_echo_proof'])

    def test_silence_and_constant_signal_do_not_invent_similarity(self):
        reference=shaped(3)
        for mic in (bytes(12800),pcm([2000]*6400)):
            with self.subTest(mic=mic[:2]):
                result=self.measure(mic,reference,played_seconds=2.7,clock=lambda:0.)
                self.assertEqual(result['status'],'no_variation')
                self.assertNotIn('correlation',result)

    def test_constant_reference_is_unavailable(self):
        result=self.measure(shaped(3,.4),pcm([2000]*64000),played_seconds=2.7,clock=lambda:0.)
        self.assertEqual(result['status'],'no_reference_variation')

    def test_invalid_time_and_short_input_are_unavailable(self):
        for played in (None,True,float('nan'),float('inf'),-1):
            with self.subTest(played=played):
                self.assertEqual(self.measure(shaped(1,.4),shaped(2),played_seconds=played)['status'],'invalid_timing')
        self.assertEqual(self.measure(bytes(320),shaped(2),played_seconds=2.)['status'],'insufficient_audio')

    def test_cooperative_budget_exhaustion_is_not_a_partial_positive_match(self):
        value=0.
        def clock():
            nonlocal value
            value+=.03
            return value
        result=self.measure(self.delayed(shaped(1)),shaped(1),played_seconds=2.7,clock=clock)
        self.assertEqual(result['status'],'work_budget_exhausted')
        self.assertLessEqual(result['comparisons'],16)
        self.assertNotIn('correlation',result)

    def test_deadline_expiry_after_last_checkpoint_cannot_report_success(self):
        reference=shaped(42,6)
        for final_time,status in ((.026,'work_budget_exhausted'),(-1.,'invalid_clock'),(float('nan'),'invalid_clock')):
            with self.subTest(final_time=final_time):
                calls=0
                def clock():
                    nonlocal calls
                    calls+=1
                    return 0. if calls<128 else final_time
                result=self.measure(reference[96000:108800],reference,played_seconds=3.4,clock=clock)
                self.assertEqual(result['status'],status)
                self.assertNotIn('correlation',result)
                self.assertNotIn('offset_ms',result)

    def test_single_short_periodic_candidate_has_unknown_peak_margin(self):
        reference=pcm(round(6000*math.sin(2*math.pi*100*i/16000)) for i in range(6400))
        result=self.measure(reference,reference,played_seconds=1.65,clock=lambda:0.)
        self.assertEqual(result['status'],'measured')
        self.assertEqual(result['comparisons'],1)
        self.assertIsNone(result['peak_margin'])
        self.assertEqual(result['alternative_count'],0)

    def test_result_is_bounded_scalar_json_and_input_bytes_are_unchanged(self):
        reference=shaped(7,90);mic=self.delayed(reference,played=45)
        before=(mic,reference)
        result=self.measure(mic,reference,played_seconds=45,clock=lambda:0.)
        self.assertEqual((mic,reference),before)
        self.assertLessEqual(result['comparisons'],2001)
        self.assertLess(len(json.dumps(result)),2048)
        self.assertTrue(all(isinstance(v,(str,int,float,bool,type(None))) for v in result.values()))

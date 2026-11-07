import importlib
import json
import math
from unittest.mock import patch
import unittest
from segmenter import samples
from test_waveform_observer import pcm,shaped


class CalibrationAnalysisTests(unittest.TestCase):
    def test_nonfinite_initial_clock_never_becomes_measured_or_json_nan(self):
        facts=self.module().diagnose_pair(shaped(52,.4),shaped(52,5),40003,clock=lambda:float('nan'))
        self.assertEqual(facts['status'],'invalid_clock')
        json.dumps(facts,allow_nan=False)

    def module(self):
        try:return importlib.import_module('calibration_analysis')
        except ModuleNotFoundError:self.fail('private on-Green scalar calibration analyzer missing')

    def test_fine_waveform_lag_and_coherence_are_actual_measurements(self):
        ref=shaped(52,5);at=20003
        mic=pcm(round(.6*x) for x in samples(ref[at*2:(at+6400)*2]))
        facts=self.module().diagnose_pair(mic,ref,40003)
        self.assertEqual(facts['status'],'measured',facts)
        self.assertAlmostEqual(facts['waveform_lag_samples'],20000,delta=2)
        self.assertGreater(facts['waveform_correlation'],.999)
        self.assertGreater(facts['coherence'],.999)
        self.assertFalse(facts['source_identity_proof'])
        json.dumps(facts,allow_nan=False)

    def test_identical_rms_independent_waveforms_are_reported_as_low_coherence(self):
        facts=self.module().coherence(shaped(52,.4),shaped(81,.4))
        self.assertLess(facts['coherence'],.2)
        self.assertGreaterEqual(facts['frames'],20)
        self.assertFalse(facts['source_identity_proof'])

    def test_periodic_matching_voices_do_not_become_identity_proof(self):
        a=pcm(round(5000*math.sin(2*math.pi*250*i/16000)) for i in range(6400))
        b=pcm(round(5000*math.sin(2*math.pi*250*i/16000+.7)) for i in range(6400))
        facts=self.module().coherence(a,b)
        self.assertGreater(facts['coherence'],.98)
        self.assertFalse(facts['source_identity_proof'])
        self.assertLess(facts['effective_bins'],5)

    def test_stdlib_fft_fallback_matches_real_coherence(self):
        a=shaped(52,.4);b=pcm(round(.6*x) for x in samples(a))
        normal=self.module().coherence(a,b)
        with patch.dict('sys.modules',{'numpy':None}):fallback=self.module().coherence(a,b)
        self.assertEqual(fallback['kernel'],'stdlib_radix2')
        self.assertAlmostEqual(fallback['coherence'],normal['coherence'],places=8)

    def test_silence_short_and_expired_are_explicit_unknowns(self):
        module=self.module()
        self.assertNotEqual(module.coherence(bytes(12800),bytes(12800))['status'],'measured')
        self.assertNotEqual(module.coherence(shaped(52,.02),shaped(52,.02))['status'],'measured')
        ticks=iter([0.,31.,31.])
        facts=module.diagnose_pair(shaped(52,.4),shaped(52,5),40003,clock=lambda:next(ticks,31.))
        self.assertIn(facts['status'],('work_budget_exhausted','invalid_clock'))

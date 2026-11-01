"""Real PCM behavior at the continuous listening boundary."""
import array
import importlib
import math
import random
import unittest


def pcm(level, count=160):
    return array.array('h', [round(level * 12000 * math.sin(i * .31)) for i in range(count)]).tobytes()


class SegmentTests(unittest.TestCase):
    def segmenter(self, **kwargs):
        module = importlib.import_module('segmenter')
        return module.Segmenter(**kwargs)

    def feed(self, gate, seconds, probability, level=.2):
        events=[]
        for _ in range(round(seconds*100)):
            events.extend(gate.feed(pcm(level), probability))
        return events

    def test_short_answer_retains_preroll_and_finishes(self):
        gate=self.segmenter()
        quiet=pcm(.01)
        for _ in range(20):gate.feed(quiet,0)
        events=self.feed(gate,.18,.99)+self.feed(gate,.75,0)
        self.assertEqual([e.kind for e in events],['onset','utterance'])
        self.assertTrue(events[-1].audio.startswith(quiet*20))
        self.assertGreaterEqual(events[-1].voiced_s,.17)

    def test_long_utterance_is_bounded_and_marked_truncated(self):
        gate=self.segmenter(max_seconds=1)
        events=self.feed(gate,2,.99)
        utterances=[e for e in events if e.kind=='utterance']
        self.assertTrue(utterances)
        self.assertLessEqual(len(utterances[0].audio),32000)
        self.assertTrue(utterances[0].truncated)

    def test_silence_never_opens_a_turn(self):
        gate=self.segmenter()
        self.assertEqual(self.feed(gate,10,0),[])
        self.assertLessEqual(gate.buffered_bytes,32000)

    def test_invalid_audio_or_probability_is_rejected(self):
        gate=self.segmenter()
        for audio, probability in ((b'x',.8),(pcm(.1),float('nan')),(pcm(.1),2)):
            with self.assertRaises(ValueError):gate.feed(audio,probability)


class ReferenceTests(unittest.TestCase):
    def reference(self, seed):
        rng=random.Random(seed)
        return b''.join(pcm(rng.uniform(.05,.8)) for _ in range(250))

    def test_delayed_scaled_own_playback_is_echo(self):
        module=importlib.import_module('segmenter')
        ref=self.reference(4);gate=module.EchoReference(ref)
        source=array.array('h');source.frombytes(ref)
        scaled=array.array('h',[int(x*.12) for x in source[160*70:160*110]]).tobytes()
        self.assertTrue(gate.is_echo(scaled,played_seconds=1.2))

    def test_different_speech_over_reference_is_not_echo(self):
        module=importlib.import_module('segmenter')
        ref=self.reference(4);human=self.reference(71)
        own=array.array('h');own.frombytes(ref[160*2*70:160*2*110])
        speech=array.array('h');speech.frombytes(human[:len(own)*2])
        mixed=array.array('h',[int(a*.1+b*.8) for a,b in zip(own,speech)]).tobytes()
        self.assertFalse(module.EchoReference(ref).is_echo(mixed,played_seconds=1.2))

    def test_unknown_timing_does_not_claim_verified_echo(self):
        module=importlib.import_module('segmenter')
        self.assertFalse(module.EchoReference(self.reference(2)).is_echo(pcm(.1)*40,played_seconds=None))

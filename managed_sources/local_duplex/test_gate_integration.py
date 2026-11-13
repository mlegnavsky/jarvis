"""Real PCM passes through output gating and utterance segmentation together."""
import importlib
from types import SimpleNamespace as NS
import unittest
import test_segmenter as pcm_fixtures


class GateIntegrationTests(unittest.TestCase):
    def feed(self, audio, probabilities, *, ended=False):
        io=importlib.import_module('ha_io');seg=importlib.import_module('segmenter')
        self.time=0.
        self.output=io.LocalOutput(lambda:None,None,None,None,clock=lambda:self.time)
        self.output.reference=seg.EchoReference(pcm_fixtures.ReferenceTests().reference(4))
        self.output.started_at=0.;self.output.owned=not ended;self.output.tail_until=.4 if ended else 0.
        session=NS(segmenter=seg.Segmenter())
        events=[]
        for index,probability in enumerate(probabilities):
            self.time=(index+1)/100
            frame=NS(audio=audio[index*320:(index+1)*320],speech_probability=probability)
            gated=self.output.gate(frame,session)
            # Current API is scalar; repaired gate may release retained real frames.
            qualified=[(frame.audio,gated)] if isinstance(gated,(int,float)) else gated
            for pcm,p in qualified:events.extend(session.segmenter.feed(pcm,p))
        return events

    def test_first_syllable_survives_initial_reference_window(self):
        human=pcm_fixtures.ReferenceTests().reference(71)[:320*50]
        events=self.feed(human+bytes(320*80),[.99]*50+[0]*80)
        utterance=next(e for e in events if e.kind=='utterance')
        self.assertTrue(utterance.audio.startswith(human))

    def test_short_answer_inside_initial_window_is_retained(self):
        human=pcm_fixtures.ReferenceTests().reference(71)[:320*12]
        events=self.feed(human+bytes(320*90),[.99]*12+[0]*90)
        utterance=next(e for e in events if e.kind=='utterance')
        self.assertTrue(utterance.audio.startswith(human))
        self.assertAlmostEqual(utterance.voiced_s,.12)

    def test_short_answer_after_question_survives_echo_tail(self):
        human=pcm_fixtures.ReferenceTests().reference(71)[:320*12]
        events=self.feed(bytes(320*5)+human+bytes(320*90),[0]*5+[.99]*12+[0]*90,ended=True)
        self.assertEqual([e.kind for e in events],['onset','utterance'])
        self.assertIn(human,events[-1].audio)

    def test_own_reference_alone_does_not_open_turn(self):
        reference=pcm_fixtures.ReferenceTests().reference(4)
        events=self.feed(reference[:320*100],[.99]*100)
        self.assertEqual(events,[])

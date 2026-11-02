import asyncio
import importlib
import json
import math
import random
import struct
from types import SimpleNamespace as NS
import unittest


class PlaybackObserverTests(unittest.IsolatedAsyncioTestCase):
    def observer(self, output):
        return importlib.import_module('playback_observer').PlaybackObserver(lambda:output, clock=lambda:0.)

    async def test_real_envelope_offset_outside_old_window_is_measured_without_changing_audio(self):
        rng=random.Random(42)
        amplitudes=[rng.randint(500,8000) for _ in range(300)]
        frames=[struct.pack('<160h',*(round(a*math.sin(2*math.pi*197*i/16000)) for i in range(160))) for a in amplitudes]
        reference=importlib.import_module('segmenter').EchoReference(b''.join(frames))
        observer=self.observer(NS(owned=True,started_at=0.,reference=reference))
        # Mic is exactly800ms behind the sender estimate, beyond old450ms search.
        original=bytes(320*80)+b''.join(frames[:220])
        chunks=[original[:160]]+[original[i:i+2560] for i in range(160,len(original),2560)]
        async def source():
            for chunk in chunks:yield chunk
        received=[chunk async for chunk in observer.source(source())]
        self.assertEqual(received,chunks)
        stats=observer.snapshot()
        self.assertEqual(stats['frames_during_output'],300)
        self.assertEqual(stats['latest']['offset_ms'],800)
        self.assertGreater(stats['latest']['correlation'],.99)
        self.assertLessEqual(len(stats['observations']),32)
        self.assertFalse(stats['input_modified'])
        self.assertFalse(stats['raw_microphone_saved'])

    async def test_missing_playback_timing_never_blocks_or_invents_a_measurement(self):
        observer=self.observer(NS(owned=True,started_at=None,reference=None))
        async def source():yield b'\x01\x00'*320
        self.assertEqual([x async for x in observer.source(source())],[b'\x01\x00'*320])
        stats=observer.snapshot()
        self.assertEqual(stats['timing_unavailable_frames'],2)
        self.assertIsNone(stats['latest'])

    async def test_diagnostic_failure_does_not_terminate_microphone_input(self):
        def broken():raise RuntimeError('diagnostic only')
        observer=importlib.import_module('playback_observer').PlaybackObserver(broken,clock=lambda:0.)
        chunks=[b'\x01\x00'*160,b'\x02\x00'*160]
        async def source():
            for chunk in chunks:yield chunk
        self.assertEqual([x async for x in observer.source(source())],chunks)
        self.assertEqual(observer.snapshot()['diagnostic_errors'],2)

    async def test_closing_observer_closes_its_source(self):
        closed=[]
        observer=self.observer(NS(owned=False))
        async def source():
            try:
                yield bytes(320)
                await asyncio.Event().wait()
            finally:closed.append(True)
        stream=observer.source(source())
        self.assertEqual(await anext(stream),bytes(320))
        await stream.aclose()
        self.assertEqual(closed,[True])
        self.assertTrue(observer.snapshot()['source_closed'])

    async def test_cancelled_playback_keeps_timings_before_interruption_clears_them(self):
        observer=self.observer(NS(owned=False));timings={'stt':2100.,'agent':1500.}
        async def play(_text):
            timings.clear()
            raise asyncio.CancelledError()
        with self.assertRaises(asyncio.CancelledError):
            await observer.play(play,'private speech',timings,lambda:{'stopped':1})
        turn=observer.snapshot()['turns'][0]
        self.assertEqual(turn['timings_ms'],{'stt':2100.,'agent':1500.})
        self.assertEqual(turn['output'],{'stopped':1})
        self.assertNotIn('private speech',str(observer.snapshot()))

    async def test_turn_history_does_not_repeat_full_transcript_diagnostics(self):
        observer=self.observer(NS(owned=False))
        rows=[{'decision':'generated_asr_variant','candidate_words':6,'reference_words':14,
            'shared_words':5,'edit_distance':1,'overlap_ratio':1.,'capture_audio_ms':1200,
            'output_owned_at_check':True} for _ in range(32)]
        original={'transcript_guard':rows,'completed':1}
        async def play(_text):pass
        for _ in range(12):await observer.play(play,'not saved',{'stt':123.},lambda:original)
        snapshot=observer.snapshot()
        self.assertEqual(len(snapshot['turns']),8)
        self.assertTrue(all(len(x['output']['transcript_guard'])==1 for x in snapshot['turns']))
        self.assertEqual(len(original['transcript_guard']),32)
        self.assertLess(len(json.dumps(snapshot,indent=2).encode()),128*1024)

    async def test_enhancer_early_close_closes_the_observed_input(self):
        closed=[];observer=self.observer(NS(owned=False))
        async def source():
            try:
                yield bytes(320)
                await asyncio.Event().wait()
            finally:closed.append(True)
        async def core_enhance(stream):
            # Core2026.6.4 process_enhance_audio has this ownership pattern:
            # closing while suspended at yield does not close its input.
            async for chunk in stream:yield NS(audio=chunk,speech_probability=0.)
        stream=observer.enhanced_source(core_enhance,source())
        self.assertEqual((await anext(stream)).audio,bytes(320))
        await stream.aclose()
        self.assertEqual(closed,[True])
        self.assertTrue(observer.closed)

    async def test_diagnostic_error_inside_large_chunk_keeps_nominal_frame_count(self):
        calls=0
        def output():
            nonlocal calls
            calls+=1
            if calls==1:raise RuntimeError('one optional diagnostic failure')
            return NS(owned=False)
        observer=importlib.import_module('playback_observer').PlaybackObserver(output,clock=lambda:0.)
        chunks=[bytes(3200)]*3
        async def source():
            for chunk in chunks:yield chunk
        self.assertEqual([x async for x in observer.source(source())],chunks)
        self.assertEqual(observer.snapshot()['frames_seen'],30)
        self.assertEqual(observer.snapshot()['diagnostic_errors'],1)

    async def test_valid_async_iterator_without_aclose_remains_valid(self):
        class Source:
            def __init__(self):self.sent=False
            def __aiter__(self):return self
            async def __anext__(self):
                if self.sent:raise StopAsyncIteration
                self.sent=True;return bytes(320)
        observer=self.observer(NS(owned=False))
        self.assertEqual([x async for x in observer.source(Source())],[bytes(320)])

    async def test_enhancer_failure_closes_source_after_a_yielded_frame(self):
        closed=[];observer=self.observer(NS(owned=False))
        async def source():
            try:
                yield bytes(320)
                await asyncio.Event().wait()
            finally:closed.append(True)
        async def enhance(stream):
            async for chunk in stream:
                yield chunk
                raise RuntimeError('native enhancement failed')
        stream=observer.enhanced_source(enhance,source())
        self.assertEqual(await anext(stream),bytes(320))
        with self.assertRaisesRegex(RuntimeError,'native enhancement failed'):await anext(stream)
        self.assertEqual(closed,[True])
        self.assertTrue(observer.closed)

    async def test_cancelling_enhanced_input_closes_waiting_upstream(self):
        closed=[];waiting=asyncio.Event();observer=self.observer(NS(owned=False))
        async def source():
            try:
                yield bytes(320)
                waiting.set();await asyncio.Event().wait()
            finally:closed.append(True)
        async def enhance(stream):
            async for chunk in stream:yield chunk
        async def consume():return [x async for x in observer.enhanced_source(enhance,source())]
        task=asyncio.create_task(consume());await waiting.wait();task.cancel()
        with self.assertRaises(asyncio.CancelledError):await task
        self.assertEqual(closed,[True])
        self.assertTrue(observer.closed)

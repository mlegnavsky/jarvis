"""One consented native run must stop, erase and never replay."""
import asyncio
import importlib
import importlib.util
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

from calibration import CalibrationManager


class RoomMeasurementTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.directory=tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.assertIsNotNone(importlib.util.find_spec('room_measurement'),
            'bounded one-shot room measurement is not implemented')
        self.module=importlib.import_module('room_measurement')
        self.closed=[];self.stops=[];self.released=[];self.tasks=[]
        self.ready=True;self.start_error=None;self.prepare_error=None
        self.output_error=None;self.start_block=False;self.source_stalls=False
        self.started=asyncio.Event();self.analysed=[]
        self.isolated=False
        async def execute(fn,*args):return await asyncio.to_thread(fn,*args)
        def analyse(data):
            self.analysed.append(len(data.raw))
            return {'status':'complete','raw_samples':len(data.raw)//2}
        self.calibration=CalibrationManager(Path(self.directory.name),execute,analyse=analyse)
        self.addAsyncCleanup(self.calibration.close)
        owner=self
        class Output:
            owned=False;started_at=None;reference=None
            async def play(output,text):
                if owner.output_error:raise owner.output_error
                output.reference=NS(pcm=b'\x01\x00'*16000)
                output.owned=True;output.started_at=time.monotonic()
                owner.started.set()
                await asyncio.Event().wait()
            async def stop(output):output.owned=False
        self.output=Output()
        async def release():self.released.append(True)
        async def prepare():
            if self.prepare_error:raise self.prepare_error
            return NS(output=self.output,media_id='fixed-generated-silent',release=release)
        async def source():
            try:
                while True:
                    if self.source_stalls:await asyncio.Event().wait()
                    yield b'\x01\x00'*160
                    await asyncio.sleep(.001)
            finally:self.closed.append(True)
        async def enhance(source):
            async for audio in source:yield NS(audio=audio,speech_probability=.5)
        async def start(media_id,marker):
            self.assertTrue(self.isolated,'isolation must precede native transmission')
            self.assertEqual(media_id,'fixed-generated-silent')
            if self.start_error:raise self.start_error
            if self.start_block:await asyncio.Event().wait()
            task=asyncio.create_task(self.measurement.capture(source(),enhance))
            self.tasks.append(task)
        async def stop(marker,task):self.stops.append((marker,task))
        async def isolate():self.isolated=True
        self.kw=dict(calibration=self.calibration,prepare=prepare,start_native=start,
            stop_native=stop,ready=lambda:self.ready,isolate=isolate)
        self.measurement=self.module.RoomMeasurement(**self.kw)

    async def run_once(self,nonce='a'*32):
        with patch.object(self.module,'MAX_SECONDS',.12):
            await self.measurement.run(nonce,time.time()+60)
        if self.calibration.analysis_task:await self.calibration.analysis_task

    async def test_deadline_closes_source_and_owned_tasks_and_wipes_after_analysis(self):
        await self.run_once()
        self.assertTrue(self.closed)
        self.assertTrue(all(t.done() for t in self.tasks))
        self.assertFalse(self.output.owned)
        self.assertEqual(len(self.stops),1)
        self.assertEqual(self.released,[True])
        self.assertTrue(self.analysed and self.analysed[0]>0)
        self.assertEqual(self.calibration.snapshot()['retained_audio_bytes'],0)
        self.assertFalse(self.measurement.snapshot()['pending'])
        self.assertLess(self.measurement.snapshot()['microphone_window_s'],.5)

    async def test_durable_global_one_shot_rejects_new_nonce_after_restart(self):
        await self.run_once()
        restarted=self.module.RoomMeasurement(**self.kw)
        await restarted.run('b'*32,time.time()+60)
        self.assertEqual(len(self.stops),1)
        self.assertEqual(len(self.tasks),1)
        self.assertEqual(restarted.snapshot()['state'],'already_consumed')

    async def test_invalid_expired_and_unready_requests_never_start(self):
        for nonce,expiry in [('x',time.time()+60),('c'*32,time.time()-1),('d'*32,time.time()+180)]:
            await self.measurement.run(nonce,expiry)
        self.ready=False
        await self.measurement.run('e'*32,time.time()+60)
        self.assertEqual(self.tasks,[]);self.assertEqual(self.stops,[])
        self.assertEqual(self.released,[])

    async def test_prepare_failure_does_not_consume_remote_start(self):
        self.prepare_error=ValueError('generated-only preparation failed')
        await self.run_once()
        self.assertEqual(self.tasks,[]);self.assertEqual(self.stops,[])
        self.assertFalse((Path(self.directory.name)/'room-test-state.json').exists())
        self.assertEqual(self.calibration.snapshot()['retained_audio_bytes'],0)

    async def test_start_failure_is_not_retried_and_generated_files_release(self):
        self.start_error=ValueError('native start failed')
        await self.run_once()
        self.assertEqual(len(self.stops),1);self.assertEqual(self.released,[True])
        self.assertEqual(self.tasks,[])
        self.assertEqual(self.calibration.snapshot()['retained_audio_bytes'],0)
        self.assertTrue((Path(self.directory.name)/'room-test-state.json').exists())

    async def test_blocked_start_still_gets_terminal_cleanup(self):
        self.start_block=True
        await self.run_once()
        self.assertEqual(len(self.stops),1);self.assertEqual(self.released,[True])
        self.assertEqual(self.tasks,[])
        self.assertEqual(self.calibration.snapshot()['retained_audio_bytes'],0)

    async def test_external_abort_drops_audio_and_closes_capture(self):
        task=asyncio.create_task(self.measurement.run('f'*32,time.time()+60))
        await asyncio.wait_for(self.started.wait(),1)
        self.measurement.abort('microphone_muted')
        await task
        self.assertTrue(self.closed);self.assertFalse(self.output.owned)
        self.assertEqual(self.analysed,[])
        self.assertEqual(self.calibration.snapshot()['retained_audio_bytes'],0)
        self.assertEqual(self.measurement.snapshot()['reason'],'microphone_muted')

    async def test_output_failure_erases_without_analysis(self):
        self.output_error=ValueError('speaker failed')
        await self.run_once()
        self.assertTrue(self.closed);self.assertEqual(self.analysed,[])
        self.assertEqual(self.calibration.snapshot()['retained_audio_bytes'],0)
        self.assertFalse(self.measurement.snapshot()['pending'])

    async def test_stale_and_other_markers_never_claim_capture(self):
        self.assertFalse(self.measurement.accepts('jarvis-room-test:'+'a'*32))
        task=asyncio.create_task(self.measurement.run('a'*32,time.time()+60))
        await asyncio.wait_for(self.started.wait(),1)
        self.assertFalse(self.measurement.accepts('jarvis-room-test:'+'b'*32))
        self.assertFalse(self.measurement.accepts('jarvis-room-test:'+'a'*32))
        self.measurement.abort('test_finished');await task

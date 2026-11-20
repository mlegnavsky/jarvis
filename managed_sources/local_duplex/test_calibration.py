import asyncio
import importlib
import json
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace as NS
import unittest
from segmenter import EchoReference
from test_waveform_observer import shaped


def calibration(test):
    try:return importlib.import_module('calibration')
    except ModuleNotFoundError:test.fail('bounded memory calibration is missing')


class RecorderTests(unittest.TestCase):
    def setup_recorder(self):
        module=calibration(self);self.time=10.
        self.output=NS(owned=True,started_at=10.,reference=EchoReference(shaped(52,35)))
        return module.Recorder(lambda:self.output,clock=lambda:self.time)

    def test_capture_is_bounded_and_raw_and_enhanced_share_sample_indices(self):
        r=self.setup_recorder();audio=shaped(81,1)
        for i in range(35):
            self.time=10+i
            r.observe_raw(audio,self.time)
            r.observe_enhanced(NS(audio=audio,speech_probability=.9))
        data=r.finish()
        self.assertEqual(len(data.raw),30*32000)
        self.assertEqual(data.raw,data.enhanced)
        self.assertLessEqual(data.pcm_bytes,3*1024*1024)
        self.assertNotIn('pcm',json.dumps(r.snapshot()).lower())
        self.assertNotIn('\\x',repr(data))
        raw=data.raw;data.wipe()
        self.assertFalse(any(raw));self.assertEqual(data.pcm_bytes,0)

    def test_waits_for_owned_playback_and_preserves_different_source_outputs(self):
        r=self.setup_recorder();self.output.owned=False;audio=shaped(81,1)
        r.observe_raw(audio,9.)
        r.observe_enhanced(NS(audio=audio,speech_probability=.9))
        self.output.owned=True
        r.observe_raw(audio,10.);r.observe_enhanced(NS(audio=audio,speech_probability=.9))
        self.output.owned=False;r.observe_raw(audio,11.)
        self.output=NS(owned=True,started_at=12.,reference=EchoReference(shaped(53,4)))
        r.observe_raw(audio,12.)
        data=r.finish()
        self.assertEqual(len(data.raw),3*32000)
        self.assertEqual(len(data.references),2)
        self.assertEqual(data.metadata['start_sample'],16000)
        data.wipe()

    def test_invalid_clock_disables_only_recording_and_erases_buffers(self):
        r=self.setup_recorder();r.observe_raw(shaped(81,1),10.)
        r.observe_raw(b'bad',float('nan'))
        self.assertEqual(r.snapshot()['state'],'failed')
        self.assertEqual(r.snapshot()['retained_audio_bytes'],0)


class ManagerTests(unittest.IsolatedAsyncioTestCase):
    async def test_discard_invalidates_arm_while_nonce_claim_waits_in_executor(self):
        module=calibration(self)
        with tempfile.TemporaryDirectory() as d:
            entered=asyncio.Event();release=asyncio.Event()
            async def delayed(function,*args):
                entered.set();await release.wait()
                return await asyncio.to_thread(function,*args)
            manager=module.CalibrationManager(Path(d),delayed,utc=lambda:100.)
            pending=asyncio.create_task(manager.arm('3'*32,180.))
            await entered.wait();await manager.discard();release.set()
            self.assertFalse(await pending)
            self.assertEqual(manager.snapshot()['state'],'discarded')
            self.assertIsNone(manager.attach(lambda:None))
            await manager.close()

    async def test_expiry_erases_queued_analysis_before_executor_can_start(self):
        module=calibration(self);analysed=[]
        with tempfile.TemporaryDirectory() as d:
            queued=asyncio.Event();release=asyncio.Event()
            async def delayed(function,*args):
                if function.__name__=='work':queued.set();await release.wait()
                return await asyncio.to_thread(function,*args)
            manager=module.CalibrationManager(Path(d),delayed,utc=lambda:100.,
                analyse=lambda data:analysed.append(True) or {'status':'complete'})
            await manager.arm('4'*32,180.)
            output=NS(owned=True,started_at=0.,reference=EchoReference(shaped(52,3)))
            recorder=manager.attach(lambda:output);recorder.observe_raw(shaped(81,1),0.)
            manager.finish(recorder);held=manager.data
            await queued.wait();manager.expire()
            try:
                self.assertEqual(held.pcm_bytes,0)
                self.assertEqual(manager.snapshot()['retained_audio_bytes'],0)
            finally:
                release.set();await manager.analysis_task
                await manager.close()
            self.assertEqual(analysed,[])
            self.assertFalse((Path(d)/'calibration-result.json').exists())

    async def test_generated_probe_never_arms_opens_or_saves_microphone_audio(self):
        module=calibration(self)
        with tempfile.TemporaryDirectory() as d:
            manager=module.CalibrationManager(Path(d),asyncio.to_thread)
            facts=await manager.probe(shaped(52,3))
            self.assertEqual(facts['status'],'passed',facts)
            self.assertEqual(manager.snapshot()['state'],'off')
            self.assertIsNone(manager.attach(lambda:None))
            self.assertEqual(list(Path(d).iterdir()),[])
            await manager.close()

    async def test_actual_analysis_writes_only_bounded_json_and_releases_all_audio(self):
        module=calibration(self)
        with tempfile.TemporaryDirectory() as d:
            manager=module.CalibrationManager(Path(d),asyncio.to_thread,utc=lambda:100.)
            await manager.arm('f'*32,180.)
            reference=shaped(52,3)
            output=NS(owned=True,started_at=9.,reference=EchoReference(reference))
            recorder=manager.attach(lambda:output)
            audio=reference[8000:20800]
            recorder.observe_raw(audio,10.)
            recorder.observe_enhanced(NS(audio=audio,speech_probability=.9))
            manager.finish(recorder);held=manager.data
            await manager.analysis_task
            facts=json.loads((Path(d)/'calibration-result.json').read_text())
            self.assertEqual(facts['status'],'complete',facts)
            self.assertEqual(len(facts['windows']),2)
            self.assertAlmostEqual(facts['windows'][0]['waveform_lag_samples'],12000,delta=2)
            self.assertEqual(facts['retained_audio_bytes'],0)
            self.assertEqual(held.pcm_bytes,0)
            self.assertEqual({p.name for p in Path(d).iterdir()},
                {'calibration-state.json','calibration-result.json'})
            self.assertLess((Path(d)/'calibration-result.json').stat().st_size,245760)
            await manager.close()

    async def test_expiry_while_waiting_for_idle_wipes_without_writing_a_result(self):
        module=calibration(self)
        with tempfile.TemporaryDirectory() as d:
            manager=module.CalibrationManager(Path(d),asyncio.to_thread,utc=lambda:100.,is_idle=lambda:False)
            await manager.arm('1'*32,180.)
            output=NS(owned=True,started_at=0.,reference=EchoReference(shaped(52,3)))
            recorder=manager.attach(lambda:output);recorder.observe_raw(shaped(81,1),0.)
            manager.finish(recorder);held=manager.data
            manager.expire();await manager.analysis_task
            self.assertEqual(held.pcm_bytes,0)
            self.assertEqual(manager.snapshot()['state'],'expired')
            self.assertFalse((Path(d)/'calibration-result.json').exists())
            self.assertIsNone(manager.attach(lambda:output))
            await manager.close()

    async def test_discard_joins_abortable_analysis_before_return_and_never_writes_audio(self):
        module=calibration(self);entered=threading.Event();held=[]
        def analyse(data):
            held.append(data);entered.set()
            if not data.abort.wait(3):raise TimeoutError('test analysis was not aborted')
            return {'status':'aborted'}
        with tempfile.TemporaryDirectory() as d:
            manager=module.CalibrationManager(Path(d),asyncio.to_thread,utc=lambda:100.,analyse=analyse)
            await manager.arm('2'*32,180.)
            output=NS(owned=True,started_at=0.,reference=EchoReference(shaped(52,3)))
            recorder=manager.attach(lambda:output);recorder.observe_raw(shaped(81,1),0.)
            manager.finish(recorder)
            self.assertTrue(await asyncio.to_thread(entered.wait,3))
            await manager.discard()
            self.assertTrue(manager.analysis_task.done())
            self.assertEqual(held[0].pcm_bytes,0)
            self.assertEqual(manager.snapshot()['state'],'discarded')
            self.assertFalse((Path(d)/'calibration-result.json').exists())
            await manager.close()

    async def test_rejected_arm_is_consumed_and_cannot_replay_after_proof(self):
        module=calibration(self)
        with tempfile.TemporaryDirectory() as d:
            manager=module.CalibrationManager(Path(d),asyncio.to_thread,utc=lambda:100.)
            manager.ready=lambda:False
            self.assertFalse(await manager.arm('d'*32,180.))
            await manager.close()
            restarted=module.CalibrationManager(Path(d),asyncio.to_thread,utc=lambda:100.)
            self.assertFalse(await restarted.arm('d'*32,180.))
            await restarted.close()

    async def test_result_write_error_is_explicit_and_never_keeps_audio(self):
        module=calibration(self)
        with tempfile.TemporaryDirectory() as d:
            manager=module.CalibrationManager(Path(d),asyncio.to_thread,utc=lambda:100.,analyse=lambda d:{'status':'complete'})
            await manager.arm('e'*32,180.)
            output=NS(owned=True,started_at=0.,reference=EchoReference(shaped(52,3)))
            recorder=manager.attach(lambda:output);recorder.observe_raw(shaped(81,1),0.)
            def fail(*a):raise OSError('full')
            manager.store.write=fail
            manager.finish(recorder)
            await manager.analysis_task
            self.assertEqual(manager.snapshot()['state'],'failed')
            self.assertEqual(manager.snapshot()['retained_audio_bytes'],0)
            await manager.close()

    async def test_default_off_one_arm_and_restart_replay_never_reopens(self):
        module=calibration(self)
        with tempfile.TemporaryDirectory() as d:
            manager=module.CalibrationManager(Path(d),asyncio.to_thread,utc=lambda:100.)
            self.assertIsNone(manager.attach(lambda:None))
            self.assertTrue(await manager.arm('a'*32,180.))
            recorder=manager.attach(lambda:None)
            self.assertIsNotNone(recorder);self.assertIsNone(manager.attach(lambda:None))
            await manager.close()
            restarted=module.CalibrationManager(Path(d),asyncio.to_thread,utc=lambda:100.)
            self.assertIsNone(restarted.attach(lambda:None))
            self.assertFalse(await restarted.arm('a'*32,180.))
            self.assertFalse(await restarted.arm('b'*32,221.))
            await restarted.close()

    async def test_analysis_failure_never_writes_audio_and_wipes_held_data(self):
        module=calibration(self);held=[]
        def analyse(data):held.append(data);raise ValueError('fail')
        with tempfile.TemporaryDirectory() as d:
            manager=module.CalibrationManager(Path(d),asyncio.to_thread,utc=lambda:100.,analyse=analyse)
            await manager.arm('c'*32,180.)
            output=NS(owned=True,started_at=0.,reference=EchoReference(shaped(52,3)))
            recorder=manager.attach(lambda:output)
            recorder.observe_raw(shaped(81,1),0.)
            recorder.observe_enhanced(NS(audio=shaped(81,1),speech_probability=.9))
            manager.finish(recorder)
            await manager.analysis_task
            self.assertEqual(held[0].pcm_bytes,0)
            self.assertEqual(manager.snapshot()['retained_audio_bytes'],0)
            for path in Path(d).iterdir():
                self.assertEqual(path.suffix,'.json')
                facts=json.loads(path.read_text())
                self.assertNotIn('base64',str(facts));self.assertNotIn('\\x',str(facts))
            await manager.close()

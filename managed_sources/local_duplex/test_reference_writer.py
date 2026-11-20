import asyncio
import importlib
import struct
import unittest
from types import SimpleNamespace as NS
from reference_tap import ReferenceQueue
from reference_timing import TimedPCM, TimingError

try:
    module = importlib.import_module('reference_writer')
except ModuleNotFoundError:
    module = None

class Clock:
    def __init__(self): self.now = 10_000_000
    def now_us(self): return self.now

class Push:
    def __init__(self): self.calls=[];self.is_stopped=False;self.pending=None
    def prepare_audio(self, pcm, fmt):
        if self.pending is not None: raise AssertionError('overlapping prepare')
        self.pending=pcm
    async def commit_audio(self, *, play_start_us):
        self.calls.append((self.pending,play_start_us));self.pending=None
        return play_start_us
    async def flush_audio(self): self.calls.append('flush')
    def clear(self): self.calls.append('clear')

class Endpoint:
    def __init__(self): self.calls=[];self.state=2;self.generation=7;self.boot_id=123
    async def cancel(self, generation):
        self.calls.append(('cancel',generation)); self.state=3
        return {'accepted':True}
    async def status(self):
        return {'schema':1,'boot_id':self.boot_id,'generation':self.generation,
            'state':self.state,'physical_stopped':self.state==0,'buffer_empty':self.state==0,
            'stream_open':self.state!=0}

class Group:
    def __init__(self,endpoint): self.endpoint=endpoint;self.stops=0
    async def stop(self): self.stops+=1;self.endpoint.state=0

class WriterTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.assertIsNotNone(module,'reference writer missing')
        self.clock=Clock();self.push=Push();self.queue=ReferenceQueue()
        self.role=NS(get_required_lead_time_us=lambda:150000,
            get_min_buffer_us=lambda:100000,get_output_delay_us=lambda:0)
        self.owned=True
        self.writer=module.ReferenceWriter(self.queue,self.push,self.role,self.clock,
            'a'*32,lambda:self.owned,audio_format='sdk-format')
    def put(self, offset=0, **overrides):
        args=dict(generation='a'*32,sequence=offset%65536,start_frame=offset*352,
            presentation_ns=11_500_000_000+offset*352*1_000_000_000//44100,
            uncertainty_ns=400000,pcm_s16be=struct.pack('!hh',0x1234,-12)*352)
        args.update(overrides);self.queue.commit(self.queue.reserve(TimedPCM(**args)))
    async def test_exact_bytes_and_pts_without_auto_rebase(self):
        self.put();self.put(1);self.queue.finish()
        await self.writer.run()
        self.assertEqual(self.push.calls[0],(struct.pack('<hh',0x1234,-12)*352,11500000))
        self.assertEqual(self.push.calls[1][1],11507981)
        self.assertEqual(self.push.calls[-1],'flush')
        self.assertEqual(self.writer.frames,704)
    async def test_stale_generation_rejected_before_prepare(self):
        self.put(generation='b'*32);self.queue.finish()
        with self.assertRaisesRegex(TimingError,'generation'):await self.writer.run()
        self.assertEqual(self.push.calls,[])
    async def test_late_packet_is_not_rebased_into_future(self):
        self.put(presentation_ns=10_100_000_000);self.queue.finish()
        with self.assertRaisesRegex(TimingError,'lead'):await self.writer.run()
        self.assertEqual(self.push.calls,[])
    async def test_frame_discontinuity_and_changed_format(self):
        self.put(start_frame=352);self.queue.finish()
        with self.assertRaisesRegex(TimingError,'continuity'):await self.writer.run()
        self.assertEqual(self.push.calls,[])
    async def test_unknown_clock_uncertainty_rejected(self):
        self.put(uncertainty_ns=10_000_001);self.queue.finish()
        with self.assertRaisesRegex(TimingError,'uncertainty'):await self.writer.run()
    async def test_foreign_owner_never_touched(self):
        self.put();self.queue.finish();self.owned=False
        with self.assertRaisesRegex(TimingError,'owner'):await self.writer.run()
        self.assertEqual(self.push.calls,[])
    async def test_failed_producer_is_not_natural_eof(self):
        self.queue.close('send_failed')
        with self.assertRaisesRegex(TimingError,'send_failed'):await self.writer.run()
        self.assertEqual(self.push.calls,[])
    async def test_cancel_requires_matching_physical_and_stream_ack(self):
        endpoint=Endpoint();group=Group(endpoint)
        result=await module.stop_reference(self.push,group,endpoint,generation=7,boot_id=123,
            owned=lambda:True)
        self.assertEqual(endpoint.calls,[('cancel',7)])
        self.assertEqual(self.push.calls,['clear'])
        self.assertEqual(group.stops,1)
        self.assertTrue(result['physical_stopped'])
    async def test_stop_preserves_replaced_group(self):
        endpoint=Endpoint();group=Group(endpoint)
        with self.assertRaisesRegex(TimingError,'owner'):
            await module.stop_reference(self.push,group,endpoint,generation=7,boot_id=123,
                owned=lambda:False)
        self.assertEqual(group.stops,0);self.assertEqual(self.push.calls,[])
    async def test_boot_or_generation_change_is_not_our_stop_ack(self):
        endpoint=Endpoint();endpoint.boot_id=456;group=Group(endpoint)
        with self.assertRaisesRegex(TimingError,'identity'):
            await module.stop_reference(self.push,group,endpoint,generation=7,boot_id=123,
                owned=lambda:True)

    async def test_gradual_clock_drift_does_not_accumulate_false_discontinuity(self):
        async def feed():
            for i in range(1200):
                pts=11_500_000_000+i*352*1_000_000_000//44100+i*1596
                self.clock.now=pts//1000-1500000
                self.put(i,presentation_ns=pts)
                await asyncio.sleep(0)
            self.queue.finish()
        producer=asyncio.create_task(feed())
        try:
            await self.writer.run()
            self.assertEqual(self.writer.frames,1200*352)
        finally:
            producer.cancel()
            await asyncio.gather(producer,return_exceptions=True)

    async def test_fault_already_drained_hardware_still_ends_owned_stream(self):
        endpoint=Endpoint();group=Group(endpoint)
        async def status():
            return dict(schema=1,boot_id=123,generation=7,state=0,
                physical_stopped=True,buffer_empty=True,stream_open=not group.stops)
        endpoint.status=status
        async def unexpected_cancel(_):raise AssertionError('lease already released')
        endpoint.cancel=unexpected_cancel
        await module.stop_reference(self.push,group,endpoint,generation=7,boot_id=123,owned=lambda:True)
        self.assertEqual(group.stops,1)

    async def test_native_cancel_failure_still_stops_owned_network_producer(self):
        endpoint=Endpoint();group=Group(endpoint)
        async def unavailable(_):raise ValueError('native_offline')
        endpoint.cancel=unavailable
        with self.assertRaisesRegex(ValueError,'native_offline'):
            await module.stop_reference(self.push,group,endpoint,generation=7,boot_id=123,owned=lambda:True)
        self.assertEqual(group.stops,1)

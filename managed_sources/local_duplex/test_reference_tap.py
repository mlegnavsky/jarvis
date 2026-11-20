import asyncio
import importlib
import io
import struct
import unittest
import wave
from types import SimpleNamespace as NS

try:
    tap_module = importlib.import_module('reference_tap')
except ModuleNotFoundError:
    tap_module = None

try:
    from pyatv.protocols.raop import RaopStream, StreamContext
    from pyatv.protocols.raop.stream_client import StreamClient
    from pyatv.settings import Settings
    from pyatv.core import MutableService
    from pyatv.const import Protocol
    from pyatv.interface import MediaMetadata
    NATIVE = True
except ImportError:
    NATIVE = False

from reference_timing import RaopTimeline, TimingError


def sync():
    return struct.pack('!BBHIIII', 0x90, 0xd4, 7, 0, 2208988900, 0, 66150)


class Wire:
    def __init__(self): self.sent=[];self.closed=False
    def sendto(self, packet, address=None): self.sent.append(bytes(packet))
    def is_closing(self): return self.closed
    def close(self): self.closed=True


class QueueTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.assertIsNotNone(tap_module, 'owned native reference tap is missing')

    def packet(self):
        t=RaopTimeline('b'*32, 10_000_000_000, 100_000_000_000, 10_000_000_000)
        t.observe_sync(sync(),now_ns=10_000_000_000)
        return t.packet(struct.pack('!BBHII',0x80,0x60,1,66150,2),b'\0'*1408,now_ns=10_000_000_000)

    async def test_reservation_not_visible_until_original_send_commits(self):
        q=tap_module.ReferenceQueue(max_packets=1)
        ticket=q.reserve(self.packet())
        reader=asyncio.create_task(q.get())
        await asyncio.sleep(0)
        self.assertFalse(reader.done())
        q.commit(ticket)
        self.assertEqual((await reader).start_frame,0)

    async def test_overflow_close_and_foreign_ticket_cannot_replay(self):
        q=tap_module.ReferenceQueue(max_packets=1)
        ticket=q.reserve(self.packet())
        with self.assertRaises(TimingError):q.reserve(self.packet())
        with self.assertRaises(TimingError):q.commit(ticket)
        self.assertIsNone(await q.get())
        other=tap_module.ReferenceQueue()
        foreign=other.reserve(self.packet())
        q2=tap_module.ReferenceQueue()
        with self.assertRaises(TimingError):q2.commit(foreign)

    async def test_close_erases_committed_and_reserved_audio_and_wakes_reader(self):
        q=tap_module.ReferenceQueue()
        q.commit(q.reserve(self.packet()))
        q.reserve(self.packet())
        q.close('cancelled')
        self.assertIsNone(await q.get())
        self.assertEqual(q.snapshot()['retained_pcm_bytes'],0)


@unittest.skipUnless(NATIVE,'native pyatv interoperability dependency missing')
class NativeTapTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.assertIsNotNone(tap_module,'owned native reference tap is missing')

    async def scenario(self, *, busy=False, fail_send=False, foreign_setup=False):
        context=StreamContext();wire=Wire();control_wire=Wire();observed=[]
        owner=asyncio.current_task()
        async def send(transport,header,payload):
            await asyncio.sleep(0)
            if fail_send:raise OSError('injected transport failure')
            transport.sendto(header+payload)
            return struct.unpack('!H',header[2:4])[0],header+payload
        protocol=NS(send_audio_packet=send)
        client=StreamClient(NS(session_id=22),context,protocol,Settings())
        manager=NS(_is_acquired=busy,stream_client=None,context=context)
        async def initialize(properties):
            client.control_client=NS(transport=control_wire)
        client.initialize=initialize
        async def setup(service):
            manager.stream_client=client
            return client,context
        manager.setup=setup
        def acquire():
            if manager._is_acquired:raise ValueError('busy')
            manager._is_acquired=True
        manager.acquire=acquire
        async def teardown():manager.stream_client=None;manager._is_acquired=False
        manager.teardown=teardown
        async def send_audio(source,metadata,volume=None):
            context.reset();context.start_ts=2208988900*44100;context.head_ts=context.start_ts
            context.rtpseq=65535
            client.control_client.transport.sendto(sync(),('test',9))
            first=True
            while await client._send_packet(source,first,wire):
                first=False
            if foreign_setup:
                manager.setup=lambda *_:None
        client.send_audio=send_audio
        service=MutableService('fixture',Protocol.RAOP,7000,{})
        core=NS(service=service,takeover=lambda *_:lambda:None)
        audio=NS(has_changed_volume=True,volume=45)
        async def set_volume(value): pass
        audio.set_volume=set_volume
        stream=RaopStream(core,None,audio,manager)
        source=io.BytesIO()
        with wave.open(source,'wb') as wav:
            wav.setnchannels(2);wav.setsampwidth(2);wav.setframerate(44100)
            wav.writeframes(struct.pack('<hh',1234,-321)*441)
        source.seek(0)
        q=tap_module.ReferenceQueue()
        tap=tap_module.OwnedRaopTap(q,'b'*32,clock_ns=lambda:10_000_000_000,
                                   wall_ns=lambda:100_000_000_000)
        async def consume():
            while (packet:=await q.get()) is not None:observed.append(packet)
        consumer=asyncio.create_task(consume())
        error=None
        try:
            await tap.run(stream,source,metadata=MediaMetadata(title='test'))
        except (TimingError,OSError,ValueError) as exc:error=exc
        finally:
            q.finish();await consumer
        return NS(tap=tap,q=q,wire=wire,control_wire=control_wire,observed=observed,
                  manager=manager,setup=setup,client=client,send=send,initialize=initialize,
                  protocol=protocol,error=error,owner=owner)

    async def test_real_native_sender_taps_big_endian_pcm_and_eof_padding(self):
        r=await self.scenario()
        self.assertIsNone(r.error)
        self.assertEqual(r.observed[0].pcm_s16be[:4],b'\x04\xd2\xfe\xbf')
        self.assertEqual(len(r.observed),190)
        self.assertEqual(len(r.wire.sent),190)
        self.assertEqual(r.observed[1].pcm_s16be[89*4:],b'\0'*(263*4))
        self.assertEqual(r.observed[-1].pcm_s16be,b'\0'*1408)
        self.assertEqual(r.observed[-1].start_frame,66528)
        self.assertEqual(r.manager.setup,r.setup)
        self.assertIs(r.protocol.send_audio_packet,r.send)
        self.assertIs(r.client.initialize,r.initialize)
        self.assertIs(r.client.control_client.transport,r.control_wire)
        self.assertFalse(r.tap.snapshot()['receiver_timing_verified'])

    async def test_busy_manager_is_untouched(self):
        r=await self.scenario(busy=True)
        self.assertIsInstance(r.error,TimingError)
        self.assertTrue(r.manager._is_acquired)
        self.assertIs(r.manager.setup,r.setup)
        self.assertEqual(r.wire.sent,[])

    async def test_send_failure_does_not_commit_reference_or_keep_pcm(self):
        r=await self.scenario(fail_send=True)
        self.assertIsInstance(r.error,OSError)
        self.assertEqual(r.observed,[])
        self.assertEqual(r.q.snapshot()['retained_pcm_bytes'],0)
        self.assertTrue(r.tap.snapshot()['send_outcome_unknown'])
        self.assertIs(r.manager.setup,r.setup)

    async def test_cleanup_does_not_overwrite_foreign_replacement(self):
        r=await self.scenario(foreign_setup=True)
        self.assertIsNone(r.error)
        self.assertIsNot(r.manager.setup,r.setup)


if __name__=='__main__':unittest.main()

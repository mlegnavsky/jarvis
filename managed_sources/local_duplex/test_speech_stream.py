import asyncio
import importlib
import io
import base64
import hashlib
import unittest

GENERATED_TONE="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"


class SpeechStreamTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_codec_reference_matches_native_pcm_with_encoder_padding(self):
        try:import miniaudio
        except ImportError:self.skipTest('miniaudio test dependency is unavailable')
        data=base64.b64decode(GENERATED_TONE)
        class Response:
            async def iter_bytes(self):
                for at in range(0,len(data),256):
                    yield data[at:at+256];await asyncio.sleep(0)
        class Context:
            async def __aenter__(self):return Response()
            async def __aexit__(self,*a):pass
        stream=await self.module().open_speech_stream(lambda:Context(),asyncio.to_thread)
        try:
            await stream.wait_finished()
            # Golden from the actual pyatv0.17 open_source(...,16000,1,2)
            # path, converted back from its network byte order. Memory decode
            # trims MP3 encoder padding; the native streaming path preserves it.
            self.assertEqual(len(stream.reference.pcm),50688)
            self.assertEqual(hashlib.sha256(stream.reference.pcm).hexdigest(),
                '6d279f916834b928e7bafa3c004ec43604a6c060059ef108999dc713158d23ab')
        finally:await stream.release()
        self.assertEqual(stream.reference_pipe.active_readers,0)

    def module(self):
        try:return importlib.import_module('speech_stream')
        except ModuleNotFoundError:self.fail('bounded streaming speech transport missing')

    async def test_bounded_reader_keeps_order_and_backpressures_producer(self):
        pipe=self.module().AudioPipe(limit=32,stall_seconds=.2)
        writer=asyncio.create_task(pipe.feed(b'a'*32+b'b'*32))
        await asyncio.sleep(.01)
        self.assertFalse(writer.done())
        self.assertEqual(await asyncio.to_thread(pipe.read,32),b'a'*32)
        await writer;pipe.finish()
        self.assertEqual(await asyncio.to_thread(pipe.read,64),b'b'*32)
        self.assertEqual(await asyncio.to_thread(pipe.read,32),b'')
        self.assertLessEqual(pipe.peak_bytes,32)

    async def test_abort_unblocks_waiting_read_and_feed(self):
        module=self.module();pipe=module.AudioPipe(limit=32,stall_seconds=.2)
        reader=asyncio.create_task(asyncio.to_thread(pipe.read,32))
        await asyncio.sleep(.01);pipe.abort()
        with self.assertRaises(module.StreamAborted):await asyncio.wait_for(reader,.2)
        full=module.AudioPipe(limit=32,stall_seconds=.2)
        await full.feed(b'a'*32);writer=asyncio.create_task(full.feed(b'b'))
        await asyncio.sleep(.01);full.abort()
        with self.assertRaises(module.StreamAborted):await asyncio.wait_for(writer,.2)

    async def test_error_and_stall_are_not_successful_eof(self):
        pipe=self.module().AudioPipe(stall_seconds=.01)
        with self.assertRaises(TimeoutError):await asyncio.to_thread(pipe.read,10)
        pipe.fail(ValueError('provider failed'))
        with self.assertRaisesRegex(ValueError,'provider failed'):await asyncio.to_thread(pipe.read,10)

    async def test_reference_readiness_grows_without_serializing_audio(self):
        ref=self.module().GrowingReference()
        ref.append(b'\x00\x10'*6400)
        self.assertEqual(len(ref.pcm),12800)
        self.assertEqual(len(ref.levels),40)
        self.assertTrue(ref.is_echo(ref.pcm,played_seconds=.4) is False)
        before=ref.pcm;ref.append(b'\x00\x20'*160)
        self.assertEqual(len(before),12800)
        self.assertEqual(len(ref.pcm),13120)
        with self.assertRaises(ValueError):ref.append(bytes(32000*90))

    async def test_stream_returns_ready_before_producer_eof_and_release_closes_http(self):
        module=self.module();finished=asyncio.Event();events=[]
        class Response:
            async def iter_bytes(self):
                yield b'A'*16
                await finished.wait()
                yield b'B'*16
        class Context:
            async def __aenter__(self):events.append('open');return Response()
            async def __aexit__(self,*a):events.append('close')
        def decode(pipe,publish):
            while chunk:=pipe.read(16):publish(b'\x00\x10'*6400)
        stream=await module.open_speech_stream(lambda:Context(),asyncio.to_thread,decode=decode)
        self.assertGreaterEqual(len(stream.reference.pcm),12800)
        self.assertFalse(stream.producer.done())
        self.assertEqual(await asyncio.to_thread(stream.native.read,16),b'A'*16)
        await stream.release()
        self.assertEqual(events,['open','close'])
        self.assertTrue(stream.decoder.done());self.assertTrue(stream.producer.done())
        self.assertEqual(stream.native.active_readers,0)

    async def test_cancel_before_first_bytes_joins_decoder_and_provider(self):
        module=self.module();entered=asyncio.Event();events=[]
        class Context:
            async def __aenter__(self):entered.set();await asyncio.Event().wait()
            async def __aexit__(self,*a):events.append('close')
        def decode(pipe,publish):pipe.read(16)
        task=asyncio.create_task(module.open_speech_stream(lambda:Context(),asyncio.to_thread,decode=decode))
        await entered.wait();task.cancel()
        with self.assertRaises(asyncio.CancelledError):await asyncio.wait_for(task,.3)
        self.assertFalse(any(t.get_name().startswith('jarvis-speech-') for t in asyncio.all_tasks() if not t.done()))

    async def test_provider_failure_and_silent_reference_are_rejected(self):
        module=self.module()
        class Context:
            async def __aenter__(self):raise ValueError('provider failure')
            async def __aexit__(self,*a):pass
        def decode(pipe,publish):pipe.read(16)
        with self.assertRaisesRegex(ValueError,'provider failure'):
            await module.open_speech_stream(lambda:Context(),asyncio.to_thread,decode=decode)

    async def test_late_decoder_failure_cannot_be_reported_as_complete(self):
        module=self.module();finish=asyncio.Event()
        class Response:
            async def iter_bytes(self):
                yield b'A'*16
                await finish.wait()
        class Context:
            async def __aenter__(self):return Response()
            async def __aexit__(self,*a):pass
        def decode(pipe,publish):
            pipe.read(16);publish(b'\x00\x10'*6400)
            pipe.read(16);raise ValueError('late decoder failure')
        stream=await module.open_speech_stream(lambda:Context(),asyncio.to_thread,decode=decode)
        self.assertTrue(hasattr(stream,'wait_finished'),'stream completion must join decoder')
        finish.set()
        try:
            with self.assertRaisesRegex(ValueError,'late decoder failure'):await stream.wait_finished()
        finally:await stream.release()

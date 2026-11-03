"""One bounded, generation-owned TTS stream and its identical decoded reference."""
import asyncio
import io
import threading
import time
from contextlib import AsyncExitStack

if __package__:
    from .segmenter import EchoReference,envelopes
    from .speech_file import drain
else:
    from segmenter import EchoReference,envelopes
    from speech_file import drain


class StreamAborted(OSError):
    pass


class AudioPipe(io.BufferedIOBase):
    """Async producer, blocking codec consumer, bounded memory and real errors."""
    def __init__(self,*,limit=262144,stall_seconds=5):
        super().__init__()
        self.loop=asyncio.get_running_loop();self.limit=limit;self.stall=stall_seconds
        self.condition=threading.Condition();self.buffer=bytearray()
        self.eof=False;self.error=None;self.peak_bytes=0;self.active_readers=0
        self.space=asyncio.Event();self.space.set()

    def readable(self):return True
    def seekable(self):return False

    def wake(self):
        if not self.loop.is_closed():self.loop.call_soon_threadsafe(self.space.set)

    async def feed(self,data):
        if not isinstance(data,bytes):raise ValueError('invalid_speech_chunk')
        offset=0
        while offset<len(data):
            self.space.clear()
            with self.condition:
                if self.error is not None:raise self.error
                if self.eof:raise StreamAborted('speech_pipe_closed')
                count=min(len(data)-offset,self.limit-len(self.buffer))
                self.buffer.extend(data[offset:offset+count]);offset+=count
                self.peak_bytes=max(self.peak_bytes,len(self.buffer));self.condition.notify_all()
            if not count:
                async with asyncio.timeout(self.stall):await self.space.wait()

    def finish(self):
        with self.condition:self.eof=True;self.condition.notify_all()
        self.wake()

    def fail(self,error):
        with self.condition:
            if self.error is None:self.error=error
            self.eof=True;self.buffer.clear();self.condition.notify_all()
        self.wake()

    def abort(self):self.fail(StreamAborted('speech_stream_aborted'))

    def read(self,size=-1):
        if size==0:return b''
        if not isinstance(size,int) or size<0:raise ValueError('bounded_speech_read_required')
        requested=min(size,self.limit);deadline=time.monotonic()+self.stall
        with self.condition:
            self.active_readers+=1
            try:
                while not self.eof and len(self.buffer)<requested:
                    left=deadline-time.monotonic()
                    if left<=0:raise TimeoutError('speech_reader_stalled')
                    self.condition.wait(left)
                if self.error is not None:raise self.error
                result=bytes(self.buffer[:requested]);del self.buffer[:requested]
                return result
            finally:self.active_readers-=1;self.wake()

    def close(self):
        if hasattr(self,'condition'):self.abort()
        super().close()


class GrowingReference(EchoReference):
    def __init__(self):
        self._pcm=bytearray();self.levels=[];self.pending=bytearray()

    @property
    def pcm(self):return bytes(self._pcm)

    @property
    def duration_seconds(self):return len(self._pcm)/32000

    def pcm_prefix(self,limit):
        if type(limit) is not int or not 0<=limit<=32000*90:raise ValueError('invalid_reference_prefix')
        return memoryview(self._pcm)[:limit].tobytes()

    def append(self,pcm):
        if not isinstance(pcm,bytes) or len(pcm)%2 or len(self._pcm)+len(pcm)>32000*90:
            raise ValueError('speech_duration_limit')
        self._pcm.extend(pcm);self.pending.extend(pcm)
        count=len(self.pending)//320*320
        if count:self.levels.extend(envelopes(bytes(self.pending[:count])));del self.pending[:count]


def decode_reference(pipe,publish):
    """Public miniaudio API; replay codec probing exactly as the native reader."""
    import miniaudio
    class Source(miniaudio.StreamableSource):
        def __init__(self):
            super().__init__();self.prefix=bytearray();self.position=0;self.end=0
        def read(self,size):
            head=bytes(self.prefix[self.position:min(self.position+size,len(self.prefix))])
            if len(head)==size:self.position+=size;return head
            data=pipe.read(size-len(head))
            if self.end<32768:self.prefix.extend(data[:32768-self.end])
            self.end+=len(data);self.position+=len(head)+len(data)
            return head+data
        def seek(self,offset,origin=miniaudio.SeekOrigin.START):
            if origin==miniaudio.SeekOrigin.CURRENT:offset+=self.position
            elif origin!=miniaudio.SeekOrigin.START:return False
            if offset==self.position:return True
            if self.end<=32768 and 0<=offset<len(self.prefix):self.position=offset;return True
            return False
    source=Source()
    decoder=miniaudio.stream_any(source,source_format=miniaudio.FileFormat.UNKNOWN,
        output_format=miniaudio.SampleFormat.SIGNED16,nchannels=1,sample_rate=16000,frames_to_read=1024)
    try:
        total=0
        for decoded in decoder:
            pcm=decoded.tobytes();total+=len(pcm)
            if total>32000*90:raise ValueError('speech_duration_limit')
            publish(pcm)
    finally:decoder.close()


class SpeechStream:
    def __init__(self,create_response,execute,decode):
        self.loop=asyncio.get_running_loop();self.native=AudioPipe();self.reference_pipe=AudioPipe()
        self.reference=GrowingReference();self.ready=asyncio.Event();self.closed=False;self.error=None
        self.compressed_bytes=0;self.started=time.monotonic();self.first_reference_ms=None
        self.producer_eof_ms=None;self.cleanup_pending=False;self._release=None
        self.create_response=create_response
        async def decoding():
            await execute(decode,self.reference_pipe,self.publish)
        self.decoder=asyncio.create_task(decoding(),name='jarvis-speech-decoder')
        self.producer=asyncio.create_task(self.produce(),name='jarvis-speech-producer')
        self.decoder.add_done_callback(self.decoded)

    @property
    def pcm(self):return self.reference.pcm

    def snapshot(self):
        return {'transport':'native_raop_mp3_stream','compressed_bytes':self.compressed_bytes,
            'reference_seconds':round(len(self.reference._pcm)/32000,3),
            'first_reference_ms':self.first_reference_ms,'producer_eof_ms':self.producer_eof_ms,
            'producer_done':self.producer.done(),'decoder_done':self.decoder.done(),
            'native_pending_peak':self.native.peak_bytes,'reference_pending_peak':self.reference_pipe.peak_bytes,
            'cleanup_pending':self.cleanup_pending,'error_type':type(self.error).__name__ if self.error else None,
            'raw_microphone_saved':False}

    def failed(self,error):
        if self.error is None:self.error=error
        self.native.fail(error);self.reference_pipe.fail(error);self.ready.set()

    def accept(self,pcm):
        if self.closed or self.error is not None:return
        try:self.reference.append(pcm)
        except Exception as error:self.failed(error);return
        if self.first_reference_ms is None:self.first_reference_ms=round((time.monotonic()-self.started)*1000,1)
        if len(self.reference._pcm)>=12800 and any(self.reference._pcm):self.ready.set()

    def publish(self,pcm):
        if not self.loop.is_closed():self.loop.call_soon_threadsafe(self.accept,pcm)

    def decoded(self,task):
        if task.cancelled():return
        error=task.exception()
        if self.closed:return
        if error is not None:self.failed(error)
        elif self.reference._pcm and any(self.reference._pcm):self.ready.set()
        else:self.failed(ValueError('tts_reference_is_silent'))

    async def produce(self):
        try:
            async with AsyncExitStack() as stack:
                async with asyncio.timeout(5):response=await stack.enter_async_context(self.create_response())
                chunks=aiter(response.iter_bytes())
                while True:
                    try:
                        async with asyncio.timeout(5):chunk=await anext(chunks)
                    except StopAsyncIteration:break
                    if not isinstance(chunk,bytes) or not chunk:raise ValueError('invalid_speech_chunk')
                    self.compressed_bytes+=len(chunk)
                    if self.compressed_bytes>8*1024*1024:raise ValueError('speech_byte_limit')
                    await self.reference_pipe.feed(chunk);await self.native.feed(chunk)
            self.producer_eof_ms=round((time.monotonic()-self.started)*1000,1)
            self.reference_pipe.finish();self.native.finish()
        except asyncio.CancelledError:raise
        except Exception as error:self.failed(error)

    def abort(self):
        self.closed=True;self.native.abort();self.reference_pipe.abort();self.ready.set()

    def raise_if_failed(self):
        if self.error is not None:raise self.error

    async def wait_finished(self):
        async with asyncio.timeout(5):
            await asyncio.gather(asyncio.shield(self.producer),asyncio.shield(self.decoder))
        self.raise_if_failed()

    async def release(self):
        if self._release is None:
            async def cleanup():
                self.abort()
                if not self.producer.done():self.producer.cancel()
                await asyncio.gather(self.producer,return_exceptions=True)
                try:
                    async with asyncio.timeout(3):await asyncio.shield(self.decoder)
                except TimeoutError:
                    self.cleanup_pending=True
                    self.decoder.add_done_callback(lambda t:None if t.cancelled() else t.exception())
                except Exception:pass
            self._release=asyncio.create_task(cleanup())
        _result,cancelled=await drain(self._release)
        if cancelled:raise asyncio.CancelledError()


async def open_speech_stream(create_response,execute,*,decode=decode_reference):
    stream=SpeechStream(create_response,execute,decode)
    try:
        async with asyncio.timeout(10):await stream.ready.wait()
        stream.raise_if_failed()
        if stream.closed:raise StreamAborted('speech_stream_aborted')
        return stream
    except BaseException:
        await stream.release();raise

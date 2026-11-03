"""Owned pyatv0.17 packet tap. No global patches and no microphone operations."""
import asyncio
from collections import deque
from importlib.metadata import version
import time

if __package__:
    from .reference_timing import RaopTimeline, TimingError, TimedPCM
else:
    from reference_timing import RaopTimeline, TimingError, TimedPCM


class ReferenceQueue:
    """Reserve before transport send; publish only after that send returns."""
    def __init__(self, *, max_packets=64):
        if type(max_packets) is not int or not 1 <= max_packets <= 256:
            raise ValueError('invalid_reference_queue_bound')
        self.limit=max_packets
        self.items=deque();self.reserved={};self.event=asyncio.Event()
        self.closed=False;self.error=None;self.peak=0

    def reserve(self, packet):
        if self.closed or not isinstance(packet, TimedPCM):
            raise TimingError('reference_queue_closed_or_invalid')
        if len(self.items)+len(self.reserved) >= self.limit:
            self.close('reference_queue_overflow')
            raise TimingError('reference_queue_overflow')
        ticket=object();self.reserved[ticket]=packet
        self.peak=max(self.peak,(len(self.items)+len(self.reserved))*1408)
        return ticket

    def commit(self, ticket):
        if self.closed or ticket not in self.reserved:
            raise TimingError('reference_reservation_invalid')
        self.items.append(self.reserved.pop(ticket));self.event.set()

    async def get(self):
        while True:
            if self.items:
                return self.items.popleft()
            if self.closed:
                return None
            self.event.clear()
            await self.event.wait()

    def finish(self):
        if self.reserved:
            self.close('reference_send_incomplete')
        else:
            self.closed=True;self.event.set()

    def close(self, reason):
        self.closed=True;self.error=reason
        self.items.clear();self.reserved.clear();self.event.set()

    def snapshot(self):
        return {'closed':self.closed,'error':self.error,
                'retained_pcm_bytes':(len(self.items)+len(self.reserved))*1408,
                'peak_pcm_bytes':self.peak}


class _SyncTransport:
    def __init__(self, transport, observe):
        self.transport=transport;self.observe=observe

    def sendto(self, data, addr=None):
        result=self.transport.sendto(data,addr)
        if len(data)>=2 and data[1]==0xd4:
            self.observe(bytes(data))
        return result

    def __getattr__(self, name):
        return getattr(self.transport,name)


class OwnedRaopTap:
    def __init__(self, queue, generation, *, clock_ns=time.monotonic_ns, wall_ns=time.time_ns):
        self.queue=queue;self.generation=generation
        self.clock_ns=clock_ns;self.wall_ns=wall_ns
        self.timeline=None;self.owner=None;self.manager=None;self.client=None
        self.restore=[];self.context_signature=None
        self.send_outcome_unknown=False;self.error=None;self.used=False

    def pair(self):
        before=self.clock_ns();wall=self.wall_ns();after=self.clock_ns()
        return before,wall,after

    def bind(self, obj, name, value):
        old=getattr(obj,name);had=name in vars(obj)
        setattr(obj,name,value)
        self.restore.append((obj,name,value,old,had))

    def owned(self, *, task=True):
        if (not self.manager._is_acquired or self.manager.stream_client is not self.client
                or task and asyncio.current_task() is not self.owner):
            raise TimingError('reference_session_owner_changed')

    def validate_context(self):
        self.owned(task=False)
        context=self.manager.context
        if self.client.context is not context:
            raise TimingError('reference_context_changed')
        signature=(context.start_ts,context.latency,context.sample_rate,
                   context.channels,context.bytes_per_channel)
        if signature[2:] != (44100,2,2):
            raise TimingError('unsupported_reference_format')
        if self.context_signature is None:
            self.context_signature=signature
        elif self.context_signature!=signature:
            raise TimingError('reference_epoch_changed')

    def sync(self, data):
        self.validate_context()
        if self.timeline is None:
            self.timeline=RaopTimeline(self.generation,*self.pair())
        else:
            self.timeline.check_wall(*self.pair())
        self.timeline.observe_sync(data,now_ns=self.clock_ns())

    async def run(self, stream, source, **kwargs):
        if version('pyatv')!='0.17.0':
            raise TimingError('reference_pyatv_version_unsupported')
        if self.used:
            raise TimingError('reference_tap_single_use')
        self.used=True;self.owner=asyncio.current_task()
        self.manager=stream.playback_manager
        if self.manager._is_acquired or self.manager.stream_client is not None:
            raise TimingError('reference_manager_busy')
        original_setup=self.manager.setup

        async def setup(service):
            if asyncio.current_task() is not self.owner or not self.manager._is_acquired:
                raise TimingError('reference_setup_owner_changed')
            client,context=await original_setup(service)
            self.client=client
            self.owned()
            if context is not self.manager.context or client.context is not context:
                raise TimingError('reference_setup_identity_changed')
            protocol=client._protocol;original_send=protocol.send_audio_packet
            original_initialize=client.initialize

            async def initialize(properties):
                self.owned()
                result=await original_initialize(properties)
                self.owned()
                if (context.sample_rate,context.channels,context.bytes_per_channel)!=(44100,2,2):
                    raise TimingError('unsupported_reference_format')
                control=client.control_client
                if control is None or control.transport is None:
                    raise TimingError('reference_sync_transport_missing')
                self.bind(control,'transport',_SyncTransport(control.transport,self.sync))
                return result

            async def send(transport, header, pcm):
                self.owned();self.validate_context()
                if self.timeline is None:
                    raise TimingError('reference_sync_missing')
                self.timeline.check_wall(*self.pair())
                packet=self.timeline.packet(bytes(header),bytes(pcm),now_ns=self.clock_ns())
                ticket=self.queue.reserve(packet)
                try:
                    result=await original_send(transport,header,pcm)
                    self.owned()
                    if not isinstance(result,tuple) or len(result)!=2 or result[0]!=packet.sequence:
                        raise TimingError('reference_send_identity_changed')
                    self.queue.commit(ticket)
                    return result
                except BaseException:
                    self.send_outcome_unknown=True
                    self.queue.close('reference_send_failed_or_cancelled')
                    raise

            self.bind(client,'initialize',initialize)
            self.bind(protocol,'send_audio_packet',send)
            return client,context

        self.bind(self.manager,'setup',setup)
        try:
            # Native stream_file acquires synchronously before its first await.
            # No yield is introduced between the instance hook and that call.
            result=await stream.stream_file(source,**kwargs)
            if self.timeline is None or self.timeline.frames==0:
                raise TimingError('reference_stream_empty')
            self.queue.finish()
            return result
        except BaseException as exc:
            self.error=type(exc).__name__
            self.queue.close('reference_session_failed_or_cancelled')
            raise
        finally:
            for obj,name,wrapper,old,had in reversed(self.restore):
                if getattr(obj,name,None) is wrapper:
                    if had:setattr(obj,name,old)
                    else:delattr(obj,name)
            self.restore.clear()

    def snapshot(self):
        return {'sender':self.timeline.snapshot() if self.timeline else None,
                'queue':self.queue.snapshot(),'error':self.error,
                'send_outcome_unknown':self.send_outcome_unknown,
                'receiver_timing_verified':False,'microphone_opened':False}

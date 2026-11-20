"""Timed Sendspin PCM writer and explicit physical-endpoint stop handshake.

The caller owns a dedicated paired Sendspin server/client and supplies that
server's Clock. This module never discovers devices, opens a microphone, or
claims HomePod receiver timing. The writer is not bound to production playback.
"""
import asyncio
import re

if __package__:
    from .reference_timing import TimedPCM, TimingError
else:
    from reference_timing import TimedPCM, TimingError


def pcm_little_endian(data):
    # Swap wire bytes irrespective of this host's endianness.
    result = bytearray(len(data))
    result[::2], result[1::2] = data[1::2], data[::2]
    return bytes(result)


class ReferenceWriter:
    def __init__(self, queue, push, role, clock, generation, owned, *, audio_format=None):
        if not isinstance(generation, str) or not re.fullmatch(r'[a-f0-9]{32}', generation):
            raise TimingError('invalid_reference_generation')
        if audio_format is None:
            from aiosendspin.audio.format import AudioFormat
            audio_format = AudioFormat(sample_rate=44100, bit_depth=16, channels=2, sample_type='int')
        self.queue=queue;self.push=push;self.role=role;self.clock=clock
        self.generation=generation;self.owned=owned;self.format=audio_format
        self.frames=0;self.sequence=None;self.first_pts=None;self.last_end_ns=None
        self.used=False

    def check(self, packet):
        if not self.owned() or self.push.is_stopped:
            raise TimingError('reference_owner_changed')
        if not isinstance(packet, TimedPCM) or packet.generation != self.generation:
            raise TimingError('reference_generation_changed')
        if ((packet.sample_rate,packet.channels)!=(44100,2) or
                not isinstance(packet.pcm_s16be,bytes) or len(packet.pcm_s16be)!=1408):
            raise TimingError('reference_format_changed')
        if (packet.start_frame!=self.frames or type(packet.sequence) is not int or
                not 0<=packet.sequence<65536 or self.sequence is not None and
                packet.sequence!=(self.sequence+1)%65536):
            raise TimingError('reference_continuity_lost')
        if (type(packet.uncertainty_ns) is not int or
                not 0<=packet.uncertainty_ns<=10_000_000):
            raise TimingError('reference_clock_uncertainty')
        if type(packet.presentation_ns) is not int or packet.presentation_ns<=0:
            raise TimingError('reference_invalid_deadline')
        now_ns=self.clock.now_us()*1000
        # 25ms codec accumulation, resampling and at most200ms commit work,
        # plus client-declared startup/buffer allowance and uncertainty.
        required=max(self.role.get_required_lead_time_us() if not self.frames else 0,
                     self.role.get_min_buffer_us())+250000
        if self.role.get_output_delay_us()!=0:
            raise TimingError('reference_output_delay_changed')
        if packet.presentation_ns-now_ns < required*1000+packet.uncertainty_ns:
            raise TimingError('reference_insufficient_lead')
        if packet.presentation_ns-now_ns>2_000_000_000:
            raise TimingError('reference_deadline_too_far')
        if self.last_end_ns is not None:
            expected=self.last_end_ns
            # Wall/RAW refresh can change the future estimate within its stated
            # uncertainty; a sample-epoch jump outside it is not continuous.
            if abs(packet.presentation_ns-expected)>packet.uncertainty_ns+1_000_000:
                raise TimingError('reference_deadline_discontinuity')

    async def run(self):
        if self.used: raise TimingError('reference_writer_single_use')
        self.used=True
        while (packet:=await self.queue.get()) is not None:
            self.check(packet)
            self.push.prepare_audio(pcm_little_endian(packet.pcm_s16be),self.format)
            async with asyncio.timeout(.2):
                await self.push.commit_audio(play_start_us=packet.presentation_ns//1000)
            if not self.owned() or self.push.is_stopped:
                raise TimingError('reference_owner_changed')
            if self.first_pts is None:self.first_pts=packet.presentation_ns
            self.frames+=352;self.sequence=packet.sequence
            self.last_end_ns=packet.presentation_ns+(352*1_000_000_000+44099)//44100
        if self.queue.error:raise TimingError(self.queue.error)
        if not self.owned() or self.push.is_stopped:raise TimingError('reference_owner_changed')
        async with asyncio.timeout(.2): await self.push.flush_audio()
        # Caller preserves scheduled tail before stop; this is not a DMA ACK.
        return {'frames':self.frames,'last_deadline_ns':self.last_end_ns,
                'receiver_timing_verified':False,'acoustic_verified':False}


def stop_identity(status, generation, boot_id):
    if (not isinstance(status,dict) or status.get('schema')!=1 or
            status.get('generation')!=generation or status.get('boot_id')!=boot_id):
        raise TimingError('reference_endpoint_identity_changed')
    return (status.get('state')==0 and status.get('physical_stopped') is True and
            status.get('buffer_empty') is True and status.get('stream_open') is False)


async def stop_reference(push, group, endpoint, *, generation, boot_id, owned, timeout=3):
    """Stop this lease and await actual endpoint generation/stopped/empty evidence.

    Local Sendspin writer drainage is deliberately not accepted as physical ACK.
    Once ownership changes, no stop or clear is sent to a replacement stream.
    """
    if not owned():raise TimingError('reference_owner_changed')
    async with asyncio.timeout(timeout):
        try:
            initial=await endpoint.status()
            stop_identity(initial,generation,boot_id)
            hardware_stopped=(initial.get('state')==0 and initial.get('physical_stopped') is True
                              and initial.get('buffer_empty') is True)
            if not hardware_stopped:
                result=await endpoint.cancel(generation)
                if not isinstance(result,dict) or result.get('accepted') is not True:
                    raise TimingError('reference_endpoint_cancel_not_accepted')
        finally:
            if not owned():raise TimingError('reference_owner_changed')
            push.clear()
            async with asyncio.timeout(1):await group.stop()
        while True:
            status=await endpoint.status()
            if stop_identity(status,generation,boot_id):return status
            await asyncio.sleep(.02)

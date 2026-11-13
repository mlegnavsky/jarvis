"""Integer reference timing. A sender deadline is never receiver render proof."""
from dataclasses import dataclass
import re
import struct

SECOND = 1_000_000_000
NTP_EPOCH_NS = 2_208_988_800 * SECOND


class TimingError(ValueError):
    pass


def integer(value):
    return type(value) is int and 0 <= value < 2**63


def ceil_div(value, divisor):
    return -(-value // divisor)


def signed_rtp(value):
    return ((value + 2**31) % 2**32) - 2**31


class ClockBounds:
    """Independent endpoint clock bound; full RTT, quantization and drift included."""
    def __init__(self):
        self.boot_id = None
        self.interval = None
        self.observed_ns = None
        self.invalid = False

    def fail(self, reason):
        self.invalid = True
        raise TimingError(reason)

    def observe(self, boot_id, sent_ns, device_us, received_ns):
        if (self.invalid or not isinstance(boot_id, str)
                or not re.fullmatch(r'[a-zA-Z0-9_-]{1,64}', boot_id)
                or not all(integer(x) for x in (sent_ns, device_us, received_ns))
                or received_ns < sent_ns or received_ns-sent_ns > 20_000_000):
            self.fail('invalid_clock_exchange')
        low = device_us*1000 - received_ns
        high = device_us*1000 + 999 - sent_ns
        if self.boot_id is not None:
            if self.boot_id != boot_id:
                self.fail('endpoint_restarted')
            if sent_ns < self.observed_ns:
                self.fail('clock_exchange_reordered')
            drift = ceil_div((received_ns-self.observed_ns)*200, 1_000_000)
            low = max(low, self.interval[0]-drift)
            high = min(high, self.interval[1]+drift)
            if low > high:
                self.fail('endpoint_clock_discontinuity')
        self.boot_id = boot_id
        self.interval = (low, high)
        self.observed_ns = received_ns

    def to_device_us(self, host_ns, *, now_ns):
        if (self.invalid or self.interval is None
                or not all(integer(x) for x in (host_ns, now_ns))
                or not self.observed_ns <= now_ns <= self.observed_ns+2*SECOND
                or not now_ns <= host_ns <= now_ns+2*SECOND):
            self.fail('endpoint_clock_unavailable')
        drift = ceil_div((host_ns-self.observed_ns)*200, 1_000_000)
        low, high = self.interval[0]-drift, self.interval[1]+drift
        if high-low > 20_000_000:
            self.fail('endpoint_clock_uncertain')
        return {'earliest_us': (host_ns+low)//1000,
                'latest_us': ceil_div(host_ns+high, 1000),
                'receiver_timing_verified': False}


@dataclass(frozen=True)
class TimedPCM:
    generation: str
    sequence: int
    start_frame: int
    presentation_ns: int
    uncertainty_ns: int
    pcm_s16be: bytes
    sample_rate: int = 44100
    channels: int = 2
    receiver_timing_verified: bool = False


class RaopTimeline:
    """Pinned RAOP0.17/S16-stereo/44100 timeline from emitted sync packets.

    The caller supplies one clock domain (e.g. Sendspin's MONOTONIC_RAW), not
    an assumed interchangeable time.monotonic clock. Wall observations use
    that same clock. No PCM is persisted or retained by the timeline itself.
    """
    def __init__(self, generation, before_ns, wall_ns, after_ns):
        self.invalid = False
        self.anchor = None
        self.last_packet = None
        self.frames = 0
        self.sync_count = 0
        if not isinstance(generation, str) or not re.fullmatch(r'[a-f0-9]{32}', generation):
            self.fail('invalid_reference_generation')
        self.generation = generation
        self.offset_ns, self.uncertainty_ns = self.wall_pair(before_ns, wall_ns, after_ns)
        self.wall_checked_ns = after_ns

    def fail(self, reason):
        self.invalid = True
        raise TimingError(reason)

    def wall_pair(self, before_ns, wall_ns, after_ns):
        if (not all(integer(x) for x in (before_ns, wall_ns, after_ns))
                or not 0 <= after_ns-before_ns <= 20_000_000):
            self.fail('wall_clock_pair_uncertain')
        return (before_ns+after_ns)//2-wall_ns, ceil_div(after_ns-before_ns, 2)+50_000

    def check_wall(self, before_ns, wall_ns, after_ns):
        if self.invalid:
            self.fail('reference_epoch_invalid')
        offset, uncertainty = self.wall_pair(before_ns, wall_ns, after_ns)
        elapsed = after_ns-self.wall_checked_ns
        if not 0 <= elapsed <= 2*SECOND:
            self.fail('wall_clock_mapping_expired')
        drift = ceil_div(elapsed*200, 1_000_000)
        if abs(offset-self.offset_ns) > uncertainty+self.uncertainty_ns+drift:
            self.fail('wall_clock_discontinuity')
        self.offset_ns, self.uncertainty_ns = offset, uncertainty
        self.wall_checked_ns = after_ns

    def observe_sync(self, data, *, now_ns):
        if self.invalid or not integer(now_ns) or not isinstance(data, bytes) or len(data) != 20:
            self.fail('invalid_raop_sync')
        proto, kind, flags, rtp, sec, frac, now = struct.unpack('!BBHIIII', data)
        if proto not in (0x80, 0x90) or kind != 0xd4 or flags != 7 or sec < 2_208_988_800:
            self.fail('unsupported_raop_sync')
        latency = (now-rtp) & 0xffffffff
        if not 0 < latency <= 441000:
            self.fail('unsupported_raop_latency')
        stamp = sec*SECOND + (frac*SECOND)//2**32 - NTP_EPOCH_NS
        if self.anchor is not None:
            old_rtp, old_stamp, old_observed, old_latency = self.anchor
            delta = signed_rtp(rtp-old_rtp)
            if delta < 0 or now_ns < old_observed or latency != old_latency:
                self.fail('raop_sync_epoch_changed')
            predicted = old_stamp + delta*SECOND//44100
            if abs(stamp-predicted) > 2_000_000:
                self.fail('raop_sync_clock_discontinuity')
        self.anchor = (rtp, stamp, now_ns, latency)
        self.sync_count += 1

    def packet(self, header, pcm, *, now_ns):
        if (self.invalid or self.anchor is None or not integer(now_ns)
                or not isinstance(header, bytes) or len(header) != 12
                or not isinstance(pcm, bytes) or len(pcm) != 1408):
            self.fail('invalid_reference_packet')
        proto, kind, seq, rtp, ssrc = struct.unpack('!BBHII', header)
        if proto != 0x80 or kind not in (0x60, 0xe0):
            self.fail('unsupported_reference_packet')
        if self.last_packet is not None:
            old_seq, old_rtp, old_ssrc = self.last_packet
            if seq != (old_seq+1)&0xffff or rtp != (old_rtp+352)&0xffffffff or ssrc != old_ssrc:
                self.fail('reference_packet_discontinuity')
        anchor_rtp, stamp, observed, _latency = self.anchor
        if not 0 <= now_ns-observed <= 2*SECOND:
            self.fail('raop_sync_expired')
        delta = signed_rtp(rtp-anchor_rtp)
        if not 0 <= delta <= 441000:
            self.fail('reference_packet_outside_epoch')
        if not 0 <= now_ns-self.wall_checked_ns <= 2*SECOND:
            self.fail('wall_clock_mapping_expired')
        deadline = stamp + delta*SECOND//44100 + self.offset_ns
        uncertainty = self.uncertainty_ns+ceil_div(abs(deadline-self.wall_checked_ns)*200, 1_000_000)
        if not 20_000_000+uncertainty <= deadline-now_ns <= 10*SECOND:
            self.fail('reference_packet_late_or_unbounded')
        result = TimedPCM(self.generation, seq, self.frames, deadline,
                          uncertainty, pcm)
        self.last_packet = (seq, rtp, ssrc)
        self.frames += 352
        return result

    def snapshot(self):
        return {'generation': self.generation, 'invalid': self.invalid,
                'frames': self.frames, 'sync_packets': self.sync_count,
                'sender_timing': 'emitted_raop_sync',
                'receiver_timing_verified': False,
                'receiver_uncertainty_ns': None}

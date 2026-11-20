import importlib
import struct
import unittest

try:
    timing = importlib.import_module('reference_timing')
except ModuleNotFoundError:
    timing = None

NTP_EPOCH = 2208988800


def sync(rtp=0, sec=100, frac=0, latency=66150):
    return struct.pack('!BBHIIII', 0x90, 0xd4, 7, rtp,
                       NTP_EPOCH + sec, frac, (rtp + latency) & 0xffffffff)


def audio(seq=65535, rtp=66150, ssrc=15):
    return struct.pack('!BBHII', 0x80, 0x60, seq, rtp, ssrc)


class TimingTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(timing, 'timestamped reference module is missing')

    def test_clock_interval_contains_asymmetric_network_delay(self):
        clock = timing.ClockBounds()
        clock.observe('boot1', 1_000_000_000, 1_005_000, 1_008_000_000)
        estimate = clock.to_device_us(1_100_000_000, now_ns=1_008_000_000)
        self.assertEqual(estimate['earliest_us'], 1_096_981)
        self.assertEqual(estimate['latest_us'], 1_105_020)
        self.assertFalse(estimate['receiver_timing_verified'])

    def test_clock_rejects_stale_unbounded_reboot_and_inconsistent_samples(self):
        for mutation in ('stale', 'rtt', 'reboot', 'jump'):
            with self.subTest(mutation=mutation):
                c = timing.ClockBounds()
                c.observe('boot1', 1_000_000_000, 1_005_000, 1_008_000_000)
                with self.assertRaises(timing.TimingError):
                    if mutation == 'stale':
                        c.to_device_us(4_000_000_000, now_ns=4_000_000_000)
                    elif mutation == 'rtt':
                        timing.ClockBounds().observe('boot1', 0, 25000, 50_000_000)
                    elif mutation == 'reboot':
                        c.observe('boot2', 1_010_000_000, 2000, 1_012_000_000)
                    else:
                        c.observe('boot1', 1_010_000_000, 2_000_000, 1_012_000_000)

    def test_clock_error_invalidates_old_estimate(self):
        c = timing.ClockBounds()
        c.observe('boot1', 0, 1000, 2_000_000)
        with self.assertRaises(timing.TimingError):
            c.observe('boot1', 3_000_000, 900000, 4_000_000)
        with self.assertRaises(timing.TimingError):
            c.to_device_us(10_000_000, now_ns=4_000_000)

    def timeline(self):
        # Wall100s maps to monotonic10s; bracket uncertainty1ms.
        t = timing.RaopTimeline('a'*32, 9_999_000_000, 100_000_000_000,
                                10_001_000_000)
        t.observe_sync(sync(), now_ns=10_001_000_000)
        return t

    def test_actual_wire_pcm_and_rtp_have_literal_deadline(self):
        t = self.timeline()
        pcm = struct.pack('!hh', 1234, -321) * 352
        p = t.packet(audio(), pcm, now_ns=10_100_000_000)
        self.assertEqual(p.presentation_ns, 11_500_000_000)
        self.assertEqual(p.uncertainty_ns, 1_349_800)
        self.assertEqual(p.start_frame, 0)
        self.assertEqual(p.pcm_s16be, pcm)
        self.assertFalse(p.receiver_timing_verified)
        p2 = t.packet(audio(0, 66502), b'\0'*1408, now_ns=10_110_000_000)
        self.assertEqual(p2.start_frame, 352)
        self.assertEqual(p2.presentation_ns, 11_507_981_859)

    def test_rtp_wrap_keeps_sample_timeline(self):
        t = timing.RaopTimeline('a'*32, 10_000_000_000, 100_000_000_000, 10_000_000_000)
        t.observe_sync(sync(rtp=0xfffefc9a), now_ns=10_000_000_000)
        first = 0xffffff00
        p = t.packet(audio(rtp=first), b'\0'*1408, now_ns=10_000_000_000)
        self.assertEqual(p.presentation_ns, 11_500_000_000)
        self.assertEqual(t.packet(audio(0, (first+352)&0xffffffff), b'\0'*1408,
                                 now_ns=10_010_000_000).start_frame, 352)

    def test_missing_anchor_late_packet_and_discontinuity_fail_closed(self):
        for bad in ('anchor', 'late', 'sequence', 'rtp', 'ssrc', 'pcm', 'expired'):
            with self.subTest(bad=bad):
                t = self.timeline()
                if bad != 'anchor':
                    t.packet(audio(), b'\0'*1408, now_ns=10_100_000_000)
                else:
                    t = timing.RaopTimeline('a'*32, 10_000_000_000, 100_000_000_000, 10_000_000_000)
                with self.assertRaises(timing.TimingError):
                    t.packet(audio(2 if bad=='sequence' else 0,
                                   67000 if bad=='rtp' else 66502,
                                   16 if bad=='ssrc' else 15),
                             b'\0'*(100 if bad=='pcm' else 1408),
                             now_ns=12_500_000_000 if bad=='expired' else
                             11_500_000_000 if bad=='late' else 10_110_000_000)
                self.assertTrue(t.snapshot()['invalid'])

    def test_ntp_clock_step_cannot_silently_retime_previous_packets(self):
        t = self.timeline()
        t.packet(audio(), b'\0'*1408, now_ns=10_100_000_000)
        with self.assertRaises(timing.TimingError):
            t.observe_sync(sync(rtp=44100, sec=102), now_ns=11_000_000_000)

    def test_regular_sync_updates_anchor_without_rounding_accumulation(self):
        t = self.timeline()
        for second in range(240):
            t.observe_sync(sync(rtp=second*44100, sec=100+second),
                           now_ns=(10+second)*1_000_000_000+1_000_000)
        self.assertFalse(t.snapshot()['invalid'])
        self.assertFalse(t.snapshot()['receiver_timing_verified'])

    def test_wall_jump_or_inaccurate_bracket_invalidates_mapping(self):
        t = self.timeline()
        with self.assertRaises(timing.TimingError):
            t.check_wall(11_000_000_000, 102_000_000_000, 11_001_000_000)
        with self.assertRaises(timing.TimingError):
            timing.RaopTimeline('a'*32, 0, 100_000_000_000, 30_000_000)

    def test_four_minute_clock_drift_refreshes_only_future_mapping(self):
        t = timing.RaopTimeline('a'*32, 10_000_000_000, 100_000_000_000, 10_000_000_000)
        for second in range(241):
            # Independent clock runs200ppm faster, with no accumulated float.
            device = 10_000_000_000 + second*1_000_200_000
            t.check_wall(device, (100+second)*1_000_000_000, device)
            t.observe_sync(sync(rtp=second*44100, sec=100+second), now_ns=device)
        p = t.packet(audio(rtp=10_650_150), b'\0'*1408, now_ns=250_048_000_000)
        self.assertEqual(p.presentation_ns, 251_548_000_000)
        self.assertEqual(p.uncertainty_ns, 350_000)
        self.assertFalse(p.receiver_timing_verified)


if __name__ == '__main__':
    unittest.main()

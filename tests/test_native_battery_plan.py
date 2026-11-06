"""Pure TOU planning: stale clocks or unpriced tails never authorize a window."""
from datetime import datetime, timedelta, timezone
import json
import unittest
from zoneinfo import ZoneInfo

from native_plan import battery_window_plan

TZ = ZoneInfo('Europe/Prague')


class NativeBatteryPlanTests(unittest.TestCase):
    def setUp(self):
        self.clock = datetime(2026, 11, 5, 15, 40, tzinfo=TZ)
        first = datetime(2026, 11, 5, 15, 30, tzinfo=TZ).timestamp()
        self.quotes = [dict(start=first + i * 900, end=first + (i + 1) * 900, net=7)
                       for i in range(8)]

    def plan(self, **changes):
        values = dict(native_clock=self.clock, now=self.clock.timestamp(), power_w=9300,
                      duration_minutes=30, minimum_soc=60, battery_voltage=55,
                      bms_discharge_a=200, configured_discharge_a=175,
                      house_program_power=12000, quotes=self.quotes)
        values.update(changes)
        return battery_window_plan(**values)

    def test_future_window_has_today_mask_and_only_active_slot_can_discharge(self):
        p = self.plan()
        self.assertEqual(p['start'], datetime(2026, 11, 5, 15, 45, tzinfo=TZ).timestamp())
        self.assertEqual(p['end'] - p['start'], 1800)
        self.assertEqual(p['observer_deadline'], p['end'] + 60)
        self.assertEqual(p['arm_until'], p['start'] - 10)
        self.assertEqual(p['times_hhmm'], [0, 1545, 1615, 1620, 1625, 2355])
        self.assertEqual(p['socs'], [100, 60, 100, 100, 100, 100])
        self.assertEqual(p['flags'], [0] * 6)
        self.assertEqual(p['week_mask'], 17)  # enable bit0, Thursday bit4
        self.assertEqual(p['current_limit_a'], 175)
        self.assertEqual(p['battery_power_w'], 9625)
        self.assertEqual(p['powers'], [0,9625,0,0,0,0])
        self.assertIs(p['native_power_fence'], True)
        self.assertEqual(p['mode'], 'ExportFirst')
        self.assertEqual(p['mode_register'], 142)
        self.assertEqual(p['mode_value'], 0)
        self.assertEqual(p['enable_at'], p['start'])
        self.assertEqual(p['en_register'], 145)
        self.assertEqual(p['en_value'], 0)
        self.assertFalse(p['production_verified'])
        self.assertIn('7 days', p['notice'])
        self.assertIn('house', p['notice'])
        self.assertIn('not guaranteed', p['notice'])
        json.dumps(p, allow_nan=False)

    def test_late_seconds_before_boundary_skip_expired_configuration_buffer(self):
        clock=self.clock.replace(minute=44,second=52)
        p=self.plan(native_clock=clock,now=clock.timestamp())
        self.assertEqual(p['start'],clock.replace(minute=50,second=0).timestamp())
        self.assertGreaterEqual(p['start']-clock.timestamp(),60)

    def test_all_weekdays_use_enable_plus_actual_day_bit(self):
        for day, expected in [(2, 3), (3, 5), (4, 9), (5, 17), (6, 33), (7, 65), (8, 129)]:
            with self.subTest(day=day):
                clock = datetime(2026, 11, day, 15, 40, tzinfo=TZ)
                offset = clock.timestamp() - self.clock.timestamp()
                quotes = [{**q, 'start': q['start'] + offset, 'end': q['end'] + offset}
                          for q in self.quotes]
                self.assertEqual(self.plan(native_clock=clock, now=clock.timestamp(), quotes=quotes)['week_mask'], expected)

    def test_duration_rounds_down_and_never_exceeds_request(self):
        for requested, seconds in [(5, 300), (9.99, 300), (10, 600), (59.99, 3300), (60, 3600)]:
            with self.subTest(requested=requested):
                p = self.plan(duration_minutes=requested)
                self.assertEqual(p['end'] - p['start'], seconds)
                self.assertLessEqual(seconds, requested * 60)
        for requested in [0, 4.999, 60.01]:
            with self.subTest(requested=requested), self.assertRaises(ValueError):
                self.plan(duration_minutes=requested)

    def test_future_start_uses_next_five_minute_boundary(self):
        clock = self.clock.replace(minute=42, second=59)
        p = self.plan(native_clock=clock, now=clock.timestamp())
        self.assertEqual(p['times_hhmm'][1], 1545)
        self.assertGreater(p['start'] - clock.timestamp(), 120)

    def test_one_minute_production_buffer_keeps_selected_quarter_start(self):
        clock = self.clock.replace(minute=44)
        self.assertEqual(self.plan(native_clock=clock, now=clock.timestamp())['times_hhmm'][1], 1545)

    def test_business_block_end_clips_duration_before_five_minute_rounding(self):
        end = datetime(2026, 11, 5, 16, 2, tzinfo=TZ).timestamp()
        p = self.plan(duration_minutes=60, window_end=end)
        self.assertEqual(p['times_hhmm'][2], 1600)
        self.assertEqual(p['duration_minutes'], 15)
        self.assertLessEqual(p['end'], end)
        self.assertEqual(p['observer_deadline'], p['end'] + 60)
        for bad in [self.clock.timestamp(), p['start'] + 299, True, float('nan')]:
            with self.subTest(end=bad), self.assertRaises(ValueError):
                self.plan(window_end=bad)

    def test_soc_rounds_up_and_cannot_lower_sixty_percent_reserve(self):
        for requested, expected in [(0, 60), (59.1, 60), (60.1, 61), (97.01, 98)]:
            with self.subTest(requested=requested):
                self.assertEqual(self.plan(minimum_soc=requested)['minimum_soc'], expected)
        for requested in [-1, 98.01, 100]:
            with self.subTest(requested=requested), self.assertRaises(ValueError):
                self.plan(minimum_soc=requested)

    def test_battery_dc_limit_honors_low_bms_and_low_voltage(self):
        p = self.plan(battery_voltage=44.8, bms_discharge_a=80.9)
        self.assertEqual(p['current_limit_a'], 80)
        self.assertEqual(p['battery_power_w'], 3584)
        self.assertEqual(p['power_w'], 9300)

    def test_battery_current_honors_configuration_and_ten_kw_ceiling(self):
        p = self.plan(battery_voltage=57.6, configured_discharge_a=350)
        self.assertEqual(p['current_limit_a'], 173)
        self.assertEqual(p['battery_power_w'], 9964)
        self.assertEqual(self.plan(configured_discharge_a=17.9)['current_limit_a'], 17)
        self.assertEqual(self.plan(house_program_power=999)['battery_power_w'], 999)
        self.assertEqual(self.plan(bms_discharge_a=1, house_program_power=10)['battery_power_w'], 10)

    def test_grid_export_cap_is_independent_and_clamped_at_9300(self):
        self.assertEqual(self.plan(power_w=9500)['power_w'], 9300)
        self.assertEqual(self.plan(power_w=100.9)['power_w'], 100)
        with self.assertRaises(ValueError):
            self.plan(power_w=99.9)

    def test_parameter_ranges_cannot_exceed_installation_limits(self):
        for changes in [dict(battery_voltage=44.79), dict(battery_voltage=57.61),
                        dict(bms_discharge_a=0.9), dict(bms_discharge_a=200.1),
                        dict(configured_discharge_a=0.9), dict(configured_discharge_a=350.1),
                        dict(house_program_power=0), dict(house_program_power=65536)]:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.plan(**changes)

    def test_bounded_measured_clock_lag_keeps_a_future_native_window(self):
        host=self.clock.replace(minute=41)
        for lag in (0,5.01,11,20):
            result=self.plan(native_clock=host-timedelta(seconds=lag),now=host.timestamp())
            self.assertGreater(result['start'],host.timestamp())
        for delta in (-20.01,5.01):
            with self.assertRaisesRegex(ValueError,'clock'):
                self.plan(native_clock=host+timedelta(seconds=delta),now=host.timestamp())

    def test_stale_or_naive_inverter_clock_is_rejected(self):
        for clock in [self.clock.replace(tzinfo=None), self.clock + timedelta(seconds=5.01),
                      self.clock - timedelta(seconds=20.01)]:
            with self.subTest(clock=clock), self.assertRaises(ValueError):
                self.plan(native_clock=clock)
        # Keep a future arming boundary: a clock just behind15:40 would select
        #15:40 itself under the one-minute preparation rule and safely refuse.
        clock = self.clock.replace(minute=41)
        self.plan(native_clock=clock + timedelta(seconds=5), now=clock.timestamp())
        self.plan(native_clock=clock - timedelta(seconds=5), now=clock.timestamp())

    def test_aware_utc_clock_is_normalized_to_prague(self):
        self.assertEqual(self.plan(native_clock=self.clock.astimezone(timezone.utc))['times_hhmm'][1], 1545)

    def test_nonexistent_and_ambiguous_wall_clocks_cannot_arm(self):
        for clock in [datetime(2026, 3, 29, 2, 10, tzinfo=TZ),
                      datetime(2026, 10, 25, 2, 10, tzinfo=TZ, fold=0),
                      datetime(2026, 10, 25, 2, 10, tzinfo=TZ, fold=1),
                      datetime(2026, 3, 29, 1, 55, tzinfo=TZ),
                      datetime(2026, 10, 25, 1, 55, tzinfo=TZ)]:
            with self.subTest(clock=clock), self.assertRaises(ValueError):
                self.plan(native_clock=clock, now=clock.timestamp())

    def test_end_and_recovery_slots_cannot_cross_midnight_or_touch_last_slot(self):
        for hour, minute, duration in [(23, 35, 5), (23, 0, 60), (23, 59, 5)]:
            clock = self.clock.replace(hour=hour, minute=minute)
            with self.subTest(clock=clock), self.assertRaises(ValueError):
                self.plan(native_clock=clock, now=clock.timestamp(), duration_minutes=duration)
        clock = self.clock.replace(hour=23, minute=30)
        first = self.quotes[0]['start'] + 8 * 3600
        quotes = [dict(start=first + i * 900, end=first + (i + 1) * 900, net=7) for i in range(2)]
        p = self.plan(native_clock=clock, now=clock.timestamp(), duration_minutes=5, quotes=quotes)
        self.assertEqual(p['times_hhmm'], [0, 2335, 2340, 2345, 2350, 2355])

    def test_expired_arming_deadline_is_rejected_and_live_deadline_is_bounded(self):
        for deadline in [self.clock.timestamp() - 1, self.clock.timestamp()]:
            with self.subTest(deadline=deadline), self.assertRaises(ValueError):
                self.plan(valid_until=deadline)
        deadline = self.clock.timestamp() + 90
        self.assertEqual(self.plan(valid_until=deadline)['arm_until'], deadline)
        self.assertEqual(self.plan(valid_until=self.clock.timestamp() + 10000)['arm_until'], self.clock.timestamp() + 290)

    def test_only_current_quote_cannot_be_carried_forward_into_future_window(self):
        with self.assertRaises(ValueError):
            self.plan(quotes=self.quotes[:1])

    def test_future_negative_quote_truncates_before_observer_buffer(self):
        quotes = [dict(q) for q in self.quotes]
        quotes[2]['net'] = -0.1  # 16:00; sale must end15:55 for a positive observer tail.
        p = self.plan(quotes=quotes)
        self.assertEqual(p['times_hhmm'][2], 1555)
        self.assertEqual(p['observer_deadline'] - p['start'], 660)

    def test_missing_future_quote_truncates_instead_of_guessing_price(self):
        p = self.plan(quotes=self.quotes[:2])
        self.assertEqual(p['times_hhmm'][2], 1555)

    def test_duplicates_or_nonpositive_prices_in_first_active_quarter_refuse(self):
        for quotes in [self.quotes + [self.quotes[1]],
                       [{**q, 'net': 0} for q in self.quotes],
                       [{**q, 'net': -1} for q in self.quotes]]:
            with self.subTest(quotes=quotes), self.assertRaises(ValueError):
                self.plan(quotes=quotes)

    def test_duplicate_future_quote_truncates_before_uncertain_quarter(self):
        p = self.plan(quotes=self.quotes + [self.quotes[2]])
        self.assertEqual(p['times_hhmm'][2], 1555)

    def test_cleanup_buffer_can_make_even_five_minute_sale_unpriced(self):
        clock = self.clock.replace(minute=47)  # start15:50; end15:55; observer15:56.
        p = self.plan(native_clock=clock, now=clock.timestamp(), duration_minutes=15, quotes=self.quotes[:2])
        self.assertEqual(p['times_hhmm'][2], 1555)
        clock = self.clock.replace(minute=52)  # start15:55, no positive observer after16:00.
        with self.assertRaises(ValueError):
            self.plan(native_clock=clock, now=clock.timestamp(), duration_minutes=5, quotes=self.quotes[:2])

    def test_quotes_must_be_real_epoch_quarters(self):
        for changed in [dict(start=self.quotes[1]['start'] + 1),
                        dict(end=self.quotes[1]['end'] + 1), dict(net=None)]:
            quotes = [dict(q) for q in self.quotes]
            quotes[1].update(changed)
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                self.plan(quotes=quotes)

    def test_nonfinite_and_boolean_numeric_parameters_are_rejected(self):
        for name in ['now', 'power_w', 'duration_minutes', 'minimum_soc', 'battery_voltage',
                     'bms_discharge_a', 'configured_discharge_a', 'house_program_power', 'valid_until']:
            for value in [True, False, float('nan'), float('inf'), -float('inf')]:
                with self.subTest(name=name, value=value), self.assertRaises(ValueError):
                    self.plan(**{name: value})
        for name in ['start', 'end', 'net']:
            for value in [True, float('nan'), float('inf')]:
                quotes = [dict(q) for q in self.quotes]
                quotes[1][name] = value
                with self.subTest(quote=name, value=value), self.assertRaises(ValueError):
                    self.plan(quotes=quotes)


if __name__ == '__main__':
    unittest.main()

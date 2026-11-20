"""A daily price block sizes export only from actual stored energy above60%."""
from datetime import datetime, timedelta
import math
import unittest
from zoneinfo import ZoneInfo

try:
    import simple_sales
except ImportError:
    simple_sales = None

LOCAL = ZoneInfo('Europe/Prague')


def local(value):
    return datetime.fromisoformat(value).replace(tzinfo=LOCAL).timestamp()


def block(start, count=8, net=1):
    return [{'start': start + i * 900, 'end': start + (i + 1) * 900, 'net': net} for i in range(count)]


class BlockTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(simple_sales, 'simple sales policy is missing')
        self.start = local('2026-11-06T00:00:00')

    def choose(self, rows, now=None, day='2026-11-06', **kwargs):
        return simple_sales.choose_daily_block(rows, day, self.start if now is None else now, **kwargs)

    def test_highest_average_two_hour_block_wins_over_one_price_spike(self):
        rows = block(self.start, 96)
        rows[36]['net'] = 10
        for row in rows[64:72]:
            row['net'] = 5
        result = self.choose(rows)
        self.assertEqual(result['start'], self.start + 16 * 3600)
        self.assertEqual(result['end'] - result['start'], 7200)
        self.assertEqual(result['average_net'], 5)

    def test_any_positive_net_is_eligible_without_six_crown_threshold(self):
        result = self.choose(block(self.start, net=.01))
        self.assertIsNotNone(result)
        self.assertAlmostEqual(result['average_net'], .01)

    def test_zero_negative_unknown_nonfinite_quarter_invalidates_window(self):
        for value in (0, -1, None, 'unknown', float('nan'), float('inf')):
            rows = block(self.start)
            rows[3]['net'] = value
            with self.subTest(value=value):
                self.assertIsNone(self.choose(rows))

    def test_missing_duplicate_naive_or_malformed_quarters_cannot_make_a_block(self):
        rows = block(self.start)
        missing = rows[:3] + rows[4:]
        duplicate = rows + [dict(rows[3])]
        naive = [dict(row) for row in rows]
        naive[3]['start'] = '2026-11-06T00:45:00'
        malformed = [dict(row) for row in rows]
        malformed[3]['end'] += 1
        for invalid in (missing, duplicate, naive, malformed):
            self.assertIsNone(self.choose(invalid))

    def test_missed_daily_best_selects_best_remaining_future_block(self):
        best_start = self.start + 16 * 3600
        later_start = self.start + 20 * 3600
        rows = block(best_start, net=5) + block(later_start, net=3)
        self.assertEqual(self.choose(rows, now=best_start + 60)['start'], later_start)
        self.assertIsNone(self.choose(rows, now=later_start + 1))

    def test_old_day_is_never_carried_into_next_day(self):
        self.assertIsNone(self.choose(block(self.start), now=self.start + 86400))

    def test_dst_uses_distinct_actual_quarters_inside_local_day(self):
        start = local('2026-10-25T00:00:00')
        end = local('2026-10-26T00:00:00')
        rows = block(start, int((end - start) / 900))
        for row in rows[8:16]:
            row['net'] = 5
        result = self.choose(rows, now=start, day='2026-10-25')
        self.assertEqual(result['start'], start + 7200)
        self.assertEqual(result['end'] - result['start'], 7200)
        self.assertEqual(len(rows), 100)
        self.assertLessEqual(result['end'], end)

    def test_block_duration_is_explicit_and_ties_choose_earliest(self):
        rows = block(self.start, 16, net=1)
        result = self.choose(rows, block_minutes=240)
        self.assertEqual(result['start'], self.start)
        self.assertEqual(result['end'] - result['start'], 14400)
        self.assertIsNone(self.choose(rows, block_minutes=17))


class SizeTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(simple_sales, 'simple sales policy is missing')
        self.start = local('2026-11-06T16:00:00')

    def size(self, soc=90, now=None, **options):
        values = dict(soc=soc, capacity_kwh=23.5, window_start=self.start,
                      window_end=self.start + 7200, now=self.start if now is None else now,
                      house_w=1000)
        values.update(options)
        return simple_sales.size_sale(**values)

    def test_actual_soc_energy_losses_and_house_load_determine_power(self):
        result = self.size()
        self.assertAlmostEqual(result['available_above_floor_kwh'], 7.05)
        self.assertAlmostEqual(result['expected_house_kwh'], 2)
        self.assertAlmostEqual(result['sale_budget_kwh'], 7.05 * math.sqrt(.9) - 2)
        self.assertEqual(result['power_w'], int(result['sale_budget_kwh'] / 2 * 1000))
        self.assertEqual(result['minimum_soc'], 60)

    def test_prestart_minute_uses_whole_selected_block(self):
        result = self.size(now=self.start - 60)
        self.assertEqual(result['timeleft_seconds'], 7200)
        self.assertAlmostEqual(result['expected_house_kwh'], 2)

    def test_recompute_uses_actual_soc_and_remaining_time(self):
        result = self.size(soc=70, now=self.start + 3600)
        self.assertEqual(result['timeleft_seconds'], 3600)
        self.assertAlmostEqual(result['available_above_floor_kwh'], 2.35)
        self.assertAlmostEqual(result['expected_house_kwh'], 1)
        self.assertLess(result['power_w'], self.size()['power_w'])

    def test_sixty_percent_shutdown_has_no_implicit_two_percent_margin(self):
        for soc in (0, 59, 60):
            result = self.size(soc=soc)
            self.assertEqual(result['power_w'], 0)
            self.assertEqual(result['minimum_soc'], 60)
        self.assertGreater(self.size(soc=61, house_w=0)['power_w'], 0)

    def test_current_pv_is_not_future_stored_energy(self):
        without = self.size(pv_w=0)
        sunny = self.size(pv_w=12000)
        self.assertEqual(without['sale_budget_kwh'], sunny['sale_budget_kwh'])
        self.assertEqual(sunny['assumptions']['pv_credit_kwh'], 0)

    def test_house_priority_can_reduce_export_to_zero(self):
        self.assertEqual(self.size(house_w=10000)['power_w'], 0)
        self.assertEqual(self.size(soc=60.1, house_w=0)['power_w'], 0)

    def test_export_is_capped_by_budget_and_operating_limit(self):
        self.assertEqual(self.size(soc=100, now=self.start + 7190, house_w=0)['power_w'], 9300)
        self.assertEqual(self.size(soc=100, now=self.start + 7190, house_w=0, max_export_w=500)['power_w'], 500)

    def test_invalid_inputs_or_finished_window_hold_with_finite_output(self):
        for options in ({'soc': None}, {'soc': float('nan')}, {'soc': 101},
                        {'capacity_kwh': 0}, {'house_w': None}, {'house_w': -1},
                        {'house_w': float('nan')}, {'eta': 0},
                        {'window_start': '2026-11-06T16:00:00'},
                        {'window_end': self.start}, {'now': self.start + 7200}):
            with self.subTest(options=options):
                result = self.size(**options)
                self.assertEqual(result['power_w'], 0)
                for key in ('available_above_floor_kwh', 'expected_house_kwh', 'sale_budget_kwh', 'timeleft_seconds'):
                    self.assertTrue(math.isfinite(result[key]))

    def test_explicit_higher_floor_is_respected_and_lower_floor_cannot_undercut_sixty(self):
        self.assertEqual(self.size(soc=80, minimum_soc=80)['power_w'], 0)
        self.assertEqual(self.size(minimum_soc=40)['minimum_soc'], 60)


if __name__ == '__main__':
    unittest.main()

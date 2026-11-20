"""Reserve must follow measured history, forecast provenance, and battery capacity."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
import math
import unittest
from zoneinfo import ZoneInfo

try:
    import planning
except ImportError:
    planning = None

LOCAL = ZoneInfo('Europe/Prague')
LOAD = 'sensor.jarvis_spotreba_domu'
PV = 'sensor.inverter_pv_power'
SOC = 'sensor.inverter_battery'
COUNTER = 'sensor.inverter_total_load_consumption'


def stamp(value):
    return datetime.fromtimestamp(value, timezone.utc).isoformat()


def weather(start, end, ghi=500, fetched_at=None):
    rows = []
    hour_end = (int(start) // 3600 + 1) * 3600
    while hour_end <= end + 3600:
        hour = datetime.fromtimestamp(hour_end - 1, LOCAL).hour
        rows.append({'time': stamp(hour_end), 'shortwave_radiation': ghi if 8 <= hour < 16 else 0})
        hour_end += 3600
    return {'rows': rows, 'fetched_at': stamp(start - 60 if fetched_at is None else fetched_at)}


def day(date, load=800, pv=3000, soc=70, step=10):
    start = datetime.fromisoformat(date).replace(tzinfo=LOCAL)
    end = start + timedelta(days=1)
    lo, hi = start.timestamp(), end.timestamp()
    samples = []
    for offset in range(0, int(hi - lo), step):
        t = lo + offset
        hour = datetime.fromtimestamp(t, LOCAL).hour
        values = {LOAD: load, PV: pv if 8 <= hour < 16 else 0, SOC: soc}
        samples.append({'t': t, 'values': {key: {'value': str(value), 'source_updated': stamp(t)} for key, value in values.items()}})
    return {'date': date, 'start': lo, 'end': hi, 'samples': samples, 'weather': weather(lo, hi)}


def gapped_counter_day(date, energy_kwh=12):
    result = day(date, load=100)
    for sample in result['samples']:
        elapsed = sample['t'] - result['start']
        sample['values'][COUNTER] = {
            'value': str(1000 + (datetime.fromisoformat(date) - datetime(2026, 11, 2)).days * energy_kwh
                         + energy_kwh * elapsed / (result['end'] - result['start'])),
            'source_updated': stamp(sample['t'])}
    result['samples'] = [sample for sample in result['samples']
                         if not 1800 <= (sample['t'] - result['start']) % 3600 < 2100]
    return result


class PlannerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.days = [day('2026-11-02'), day('2026-11-03')]
        cls.now = datetime(2026, 11, 4, tzinfo=LOCAL).timestamp()

    def setUp(self):
        self.assertIsNotNone(planning, 'pure house reserve planner is not implemented')

    def model(self):
        return planning.build_history(self.days)

    def reserve(self, model=None, forecast=None, now=None, charge_limit_kw=None):
        now = self.now if now is None else now
        options = {} if charge_limit_kw is None else {'charge_limit_kw': charge_limit_kw}
        return planning.reserve_for_home(self.model() if model is None else model,
                                        weather(now, now + 86400) if forecast is None else forecast, now, **options)

    def test_no_history_holds_all_battery_without_fabricated_pv(self):
        result = self.reserve(planning.build_history([]))
        self.assertEqual(result['required_soc'], 100)
        self.assertEqual(result['quality'], 'insufficient')
        self.assertEqual(result['credited_pv_kwh'], 0)

    def test_two_complete_days_produce_compact_conservative_profile(self):
        model = self.model()
        self.assertEqual(model['complete_days'], 2)
        self.assertAlmostEqual(model['house_kw'][12], 1.0)
        self.assertAlmostEqual(model['pv_ratio'][12], .003)
        self.assertLess(len(json.dumps(model)), 5000)
        result = self.reserve(model, charge_limit_kw=2)
        self.assertAlmostEqual(result['estimated_house_kwh'], 24, places=4)
        self.assertGreater(result['credited_pv_kwh'], 0)
        self.assertGreaterEqual(result['required_soc'], 60)
        self.assertLess(result['required_soc'], 100)

    def test_cloudy_forecast_retains_more_battery_than_calibrated_sun(self):
        sunny = self.reserve(charge_limit_kw=2)
        cloudy = self.reserve(forecast=weather(self.now, self.now + 86400, ghi=100), charge_limit_kw=2)
        self.assertGreater(cloudy['required_soc'], sunny['required_soc'])
        self.assertLess(cloudy['credited_pv_kwh'], sunny['credited_pv_kwh'])

    def test_missing_stale_or_unissued_weather_gives_zero_pv_credit(self):
        for forecast in ({}, weather(self.now, self.now + 86400, fetched_at=self.now - 7 * 3600),
                         weather(self.now, self.now + 86400, fetched_at=self.now + 60)):
            with self.subTest(forecast=forecast.get('fetched_at')):
                result = self.reserve(forecast=forecast)
                self.assertEqual(result['credited_pv_kwh'], 0)
                self.assertEqual(result['required_soc'], 100)
                self.assertFalse(result['pv_forecast_known'])

    def test_unseen_ghi_has_no_panel_power_conversion(self):
        days = deepcopy(self.days)
        for item in days:
            item['weather'] = {}
        result = self.reserve(planning.build_history(days))
        self.assertEqual(result['credited_pv_kwh'], 0)
        self.assertEqual(result['required_soc'], 100)

    def test_full_battery_history_cannot_calibrate_curtailed_pv(self):
        model = planning.build_history([day('2026-11-02', soc=98), day('2026-11-03', soc=98)])
        self.assertIsNone(model['pv_ratio'][12])
        self.assertEqual(self.reserve(model)['credited_pv_kwh'], 0)

    def test_history_requires_two_days_and_never_integrates_long_gaps(self):
        sparse = [day('2026-11-02', step=60), day('2026-11-03', step=60)]
        for days in (self.days[:1], sparse):
            model = planning.build_history(days)
            self.assertEqual(self.reserve(model)['required_soc'], 100)
            self.assertEqual(model['quality'], 'insufficient')

    def test_repeated_five_minute_gaps_cannot_erase_possible_house_peaks(self):
        days = [day('2026-11-02', load=100), day('2026-11-03', load=100)]
        for item in days:
            item['samples'] = [sample for sample in item['samples']
                               if (sample['t'] - item['start']) % 3600 >= 300]
        model = planning.build_history(days)
        self.assertEqual(model['complete_days'], 0)
        result = self.reserve(model)
        self.assertEqual(result['required_soc'], 100)
        self.assertEqual(result['quality'], 'insufficient')

    def test_missing_one_minute_cannot_be_normalized_into_a_complete_day(self):
        days = deepcopy(self.days)
        for item in days:
            item['samples'] = [sample for sample in item['samples']
                               if not 3600 <= sample['t'] - item['start'] < 3660]
        self.assertEqual(planning.build_history(days)['complete_days'], 0)

    def test_counter_fallback_preserves_whole_day_energy_without_timing_pv(self):
        days = [gapped_counter_day('2026-11-02'), gapped_counter_day('2026-11-03')]
        model = planning.build_history(days)
        result = self.reserve(model, charge_limit_kw=12)
        self.assertEqual(model['mode'], 'energy_only')
        self.assertEqual(result['quality'], 'energy_only')
        self.assertGreaterEqual(result['daily_house_kwh_upper'], 12)
        self.assertGreaterEqual(result['required_soc'], 98)
        self.assertEqual(result['credited_pv_kwh'], 0)
        self.assertEqual(result['direct_pv_kwh'], 0)
        self.assertEqual(result['battery_charge_kwh'], 0)
        self.assertEqual(result['sources'], [COUNTER])

    def test_counter_reset_bad_edges_or_implausible_increment_reject_fallback(self):
        for fault in ('reset', 'edge', 'spike', 'stale', 'negative', 'nonfinite'):
            days = [gapped_counter_day('2026-11-02'), gapped_counter_day('2026-11-03')]
            for item in days:
                middle = len(item['samples']) // 2
                if fault == 'reset':
                    item['samples'][middle]['values'][COUNTER]['value'] = '1'
                elif fault == 'edge':
                    item['samples'] = item['samples'][4:]
                elif fault == 'spike':
                    item['samples'][middle]['values'][COUNTER]['value'] = '2000'
                elif fault == 'negative':
                    item['samples'][middle]['values'][COUNTER]['value'] = '-1'
                elif fault == 'nonfinite':
                    item['samples'][middle]['values'][COUNTER]['value'] = 'nan'
                else:
                    item['samples'][0]['values'][COUNTER]['source_updated'] = stamp(item['start'] - 60)
                    item['samples'] = item['samples'][:1] + item['samples'][4:]
            with self.subTest(fault=fault):
                result = self.reserve(planning.build_history(days))
                self.assertEqual(result['quality'], 'insufficient')
                self.assertEqual(result['required_soc'], 100)

    def test_invalid_energy_only_model_is_rejected_and_hourly_model_preferred(self):
        days = [gapped_counter_day('2026-11-02'), gapped_counter_day('2026-11-03')]
        model = planning.build_history(days)
        for invalid in (-1, float('nan'), 10000):
            bad = deepcopy(model)
            bad['daily_house_kwh_upper'] = invalid
            self.assertEqual(self.reserve(bad)['quality'], 'insufficient')
        self.assertEqual(self.model()['mode'], 'hourly')

    def test_rolling_counter_envelope_includes_evening_and_next_morning(self):
        days = [gapped_counter_day('2026-11-02', energy_kwh=5),
                gapped_counter_day('2026-11-03', energy_kwh=5)]
        for index, item in enumerate(days):
            for sample in item['samples']:
                hour = (sample['t'] - item['start']) / 3600
                if index == 0:
                    consumed = min(5, max(0, hour - 18) * 5)
                else:
                    consumed = min(5, max(0, hour - 6) * 5)
                sample['values'][COUNTER]['value'] = str(1000 + index * 5 + consumed)
        model = planning.build_history(days)
        result = self.reserve(model)
        self.assertEqual(result['quality'], 'energy_only')
        self.assertGreaterEqual(model['house_energy_kwh_24h_upper'], 10.2)
        self.assertGreaterEqual(result['estimated_house_kwh'], 12.75)
        self.assertGreaterEqual(result['required_soc'], 88)

    def test_counter_reset_between_days_and_old_daily_cache_are_rejected(self):
        days = [gapped_counter_day('2026-11-02'), gapped_counter_day('2026-11-03')]
        model = planning.build_history(days)
        model.pop('energy_bound_method', None)
        self.assertEqual(self.reserve(model)['quality'], 'insufficient')
        for sample in days[1]['samples']:
            sample['values'][COUNTER]['value'] = str(float(sample['values'][COUNTER]['value']) - 1000)
        self.assertEqual(self.reserve(planning.build_history(days))['quality'], 'insufficient')

    def test_rolling_envelope_covers_a_window_ending_inside_counter_gaps(self):
        days = [gapped_counter_day('2026-11-02', energy_kwh=1),
                gapped_counter_day('2026-11-03', energy_kwh=1)]
        for index, item in enumerate(days):
            # Both 1kWh increments occur inside missing06:30–06:35 samples.
            # DayA06:34→dayB06:31 fits24h, but windows ending at observed
            # timestamps can exclude one increment. Bracket both boundaries.
            threshold = (6 * 60 + (34 if index == 0 else 31)) * 60
            for sample in item['samples']:
                consumed = int(sample['t'] - item['start'] >= threshold)
                sample['values'][COUNTER]['value'] = str(1000 + index + consumed)
        model = planning.build_history(days)
        self.assertEqual(model['mode'], 'energy_only')
        self.assertGreaterEqual(model['house_energy_kwh_24h_upper'], 2.2)

    def test_stale_source_reports_and_incomplete_days_are_not_profiles(self):
        days = deepcopy(self.days)
        for item in days:
            for sample in item['samples']:
                sample['values'][LOAD]['source_updated'] = stamp(sample['t'] - 300)
        self.assertEqual(self.reserve(planning.build_history(days))['quality'], 'insufficient')
        incomplete = deepcopy(self.days)
        for item in incomplete:
            item['samples'] = item['samples'][:len(item['samples']) // 2]
        self.assertEqual(self.reserve(planning.build_history(incomplete))['required_soc'], 100)

    def test_stale_model_is_insufficient(self):
        result = self.reserve(now=self.now + 8 * 86400)
        self.assertEqual(result['quality'], 'insufficient')
        self.assertEqual(result['required_soc'], 100)

    def test_future_history_and_bad_persisted_models_are_insufficient(self):
        future = self.model()
        future['as_of'] = self.now + 60
        self.assertEqual(self.reserve(future)['quality'], 'insufficient')
        for count in ('broken', None, '2'):
            model = self.model()
            model['complete_days'] = count
            result = self.reserve(model)
            self.assertEqual(result['required_soc'], 100)
        result = self.reserve(forecast={}, now=1e30)
        self.assertEqual(result['required_soc'], 100)

    def test_old_days_cannot_be_refreshed_by_one_recent_day(self):
        old = day('2026-10-01')
        model = planning.build_history([old, self.days[-1]])
        self.assertEqual(model['complete_days'], 1)
        self.assertEqual(self.reserve(model)['quality'], 'insufficient')

    def test_invalid_duplicate_and_naive_weather_are_unknown(self):
        base = weather(self.now, self.now + 86400)
        duplicate = deepcopy(base)
        duplicate['rows'].append(deepcopy(duplicate['rows'][8]))
        naive = deepcopy(base)
        naive['rows'][8]['time'] = '2026-11-04T08:00:00'
        invalid = deepcopy(base)
        invalid['rows'][8]['shortwave_radiation'] = float('nan')
        for forecast in (duplicate, naive, invalid):
            self.assertEqual(self.reserve(forecast=forecast)['credited_pv_kwh'], 0)

    def test_duplicate_samples_and_invalid_power_do_not_create_history(self):
        duplicate = deepcopy(self.days)
        for item in duplicate:
            item['samples'].append(deepcopy(item['samples'][10]))
        self.assertEqual(planning.build_history(duplicate)['complete_days'], 0)
        invalid = deepcopy(self.days)
        for item in invalid:
            for sample in item['samples']:
                sample['values'][LOAD]['value'] = '-10'
        self.assertEqual(planning.build_history(invalid)['complete_days'], 0)

    def test_historical_forecast_issued_after_daylight_is_not_calibration(self):
        days = deepcopy(self.days)
        for item in days:
            item['weather']['fetched_at'] = stamp(item['end'])
        self.assertEqual(self.reserve(planning.build_history(days))['credited_pv_kwh'], 0)

    def test_early_pv_cannot_fill_more_than_capacity_for_late_house_load(self):
        model = self.model()
        model['house_kw'] = [2] * 24
        model['pv_ratio'] = [.1] * 24
        model['pv_calibration_days'] = [2] * 24
        forecast = weather(self.now, self.now + 86400)
        for index, row in enumerate(forecast['rows']):
            row['shortwave_radiation'] = 1400 if index < 3 else 0
        result = self.reserve(model, forecast)
        self.assertEqual(result['required_soc'], 100)
        self.assertFalse(result['feasible'])
        self.assertEqual(result['quality'], 'insufficient')
        self.assertLessEqual(result['credited_pv_kwh'], 36)

    def test_terminal_floor_and_fractional_hour_budget(self):
        model = self.model()
        model['house_kw'] = [.5] * 24
        result = self.reserve(model, {}, now=self.now + 1234)
        self.assertAlmostEqual(result['estimated_house_kwh'], 12)
        self.assertAlmostEqual(result['needed_start_kwh'], 23.5 * .3 + 12 / math.sqrt(.90))
        self.assertEqual(result['required_soc'], 84)
        self.assertAlmostEqual(result['assumptions']['discharge_efficiency'], math.sqrt(.90))
        self.assertEqual(result['horizon_end'] - result['horizon_start'], 86400)

    def test_unknown_charge_limit_credits_direct_pv_but_no_stored_surplus(self):
        model = self.model()
        model['house_kw'] = [.5] * 24
        model['pv_ratio'] = [.003] * 24
        model['pv_calibration_days'] = [2] * 24
        result = self.reserve(model)
        self.assertAlmostEqual(result['direct_pv_kwh'], 4)
        self.assertAlmostEqual(result['credited_pv_kwh'], 4)
        self.assertEqual(result['battery_charge_kwh'], 0)
        self.assertEqual(result['assumptions']['charge_limit_kw'], 0)
        self.assertFalse(result['assumptions']['charge_limit_known'])
        self.assertAlmostEqual(result['needed_start_kwh'], 23.5 * .3 + 8 / math.sqrt(.90))
        self.assertEqual(result['required_soc'], 66)

    def test_storage_charge_limit_and_efficiency_bound_forecast_recharge(self):
        model = self.model()
        model['house_kw'] = [.5] * 24
        model['pv_ratio'] = [.003] * 24
        model['pv_calibration_days'] = [2] * 24
        unknown = self.reserve(model)
        slow = self.reserve(model, charge_limit_kw=.1)
        fast = self.reserve(model, charge_limit_kw=2)
        self.assertAlmostEqual(slow['battery_charge_kwh'], .8)
        self.assertAlmostEqual(fast['potential_battery_charge_kwh'], 8 * math.sqrt(.90))
        self.assertAlmostEqual(fast['battery_charge_kwh'], 4 / math.sqrt(.90))
        self.assertGreater(unknown['required_soc'], slow['required_soc'])
        self.assertGreater(slow['required_soc'], fast['required_soc'])
        self.assertTrue(fast['assumptions']['charge_limit_known'])

    def test_unused_surplus_is_forecast_potential_without_house_credit(self):
        model = self.model()
        model['house_kw'] = [0] * 24
        result = self.reserve(model, charge_limit_kw=2)
        self.assertGreater(result['forecast_pv_kwh'], 0)
        self.assertEqual(result['credited_pv_kwh'], 0)
        self.assertEqual(result['battery_charge_kwh'], 0)

    def test_invalid_charge_limits_are_zero_and_large_limit_is_inverter_bounded(self):
        for limit in (-1, float('nan'), 'unknown', True):
            result = self.reserve(charge_limit_kw=limit)
            self.assertEqual(result['battery_charge_kwh'], 0)
            self.assertEqual(result['assumptions']['charge_limit_kw'], 0)
        self.assertEqual(self.reserve(charge_limit_kw=100)['assumptions']['charge_limit_kw'], 12)

    def test_autumn_dst_day_is_25_actual_hours_and_24_hour_forecast(self):
        model = planning.build_history([day('2026-10-24'), day('2026-10-25')])
        self.assertEqual(model['complete_days'], 2)
        self.assertEqual(model['as_of'], datetime(2026, 10, 26, tzinfo=LOCAL).timestamp())
        model = planning.build_history([day('2026-10-23'), day('2026-10-24')])
        now = datetime(2026, 10, 25, 1, 30, tzinfo=LOCAL).timestamp()
        result = self.reserve(model, weather(now, now + 86400), now)
        self.assertEqual(result['horizon_end'] - result['horizon_start'], 86400)
        self.assertAlmostEqual(result['estimated_house_kwh'], 24)


if __name__ == '__main__':
    unittest.main()

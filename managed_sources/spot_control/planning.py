"""Pure, conservative 24-hour house reserve; GHI alone is never panel power.

Archive power is W. Weather timestamps END the preceding hourly mean.
All integration uses actual UTC seconds; profiles use Europe/Prague civil hours.
The JSON model contains summaries only, so it can be persisted by the adapter.
"""
from datetime import datetime, timedelta
from bisect import bisect_right
import math
from zoneinfo import ZoneInfo

LOCAL = ZoneInfo('Europe/Prague')
LOAD = 'sensor.jarvis_spotreba_domu'
PV = 'sensor.inverter_pv_power'
SOC = 'sensor.inverter_battery'
HOUSE_COUNTER = 'sensor.inverter_total_load_consumption'
MAX_GAP = 30
MODEL_MAX_AGE = 7 * 86400
WEATHER_MAX_AGE = 6 * 3600
INVERTER_KW = 12
MODEL_VERSION = 3
STORAGE_EFFICIENCY = math.sqrt(.90)  # Policy assumption, separate from load uncertainty.
DAY_MISSING_SECONDS = 30
HOUR_MISSING_SECONDS = 10
COUNTER_MAX_KW = 25
COUNTER_QUANTIZATION_KWH = .2
ENERGY_BOUND_METHOD = 'rolling_24h_counter_envelope_v1'


def _number(value):
    if isinstance(value, bool):
        return None
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (ValueError, TypeError, OverflowError):
        return None


def _iso(value):
    try:
        date = datetime.fromisoformat(value) if isinstance(value, str) else value
        if not isinstance(date, datetime) or date.tzinfo is None or date.utcoffset() is None:
            return None
        return date.timestamp()
    except (ValueError, TypeError, OverflowError, OSError):
        return None


def _time(value):
    return _iso(value) if isinstance(value, (str, datetime)) else _number(value)


def _weather(value):
    """Reject ambiguous/corrupt publications rather than infer missing zeroes."""
    if not isinstance(value, dict) or not isinstance(value.get('rows'), list):
        return None
    issued = _iso(value.get('fetched_at'))
    if issued is None:
        return None
    rows = {}
    for row in value['rows']:
        if not isinstance(row, dict):
            return None
        end = _iso(row.get('time'))
        ghi = _number(row.get('shortwave_radiation'))
        if end is None or end % 3600 or end in rows or ghi is None or not 0 <= ghi <= 1400:
            return None
        rows[end] = ghi
    return {'issued': issued, 'rows': rows}


def _value(sample, entity, maximum):
    values = sample.get('values')
    value = values.get(entity) if isinstance(values, dict) else None
    if not isinstance(value, dict):
        return None
    number = _number(value.get('value'))
    updated = _iso(value.get('source_updated'))
    if number is None or not 0 <= number <= maximum or updated is None:
        return None
    return number if -5 <= sample['t'] - updated <= MAX_GAP else None


def _bounds(value):
    if not isinstance(value, dict) or not isinstance(value.get('samples'), list):
        return None
    try:
        midnight = datetime.fromisoformat(value['date'])
        if midnight.tzinfo is not None or midnight.time() != datetime.min.time():
            return None
        midnight = midnight.replace(tzinfo=LOCAL)
        start, end = _time(value.get('start')), _time(value.get('end'))
        if start != midnight.timestamp() or end != (midnight + timedelta(days=1)).timestamp():
            return None
    except (KeyError, TypeError, ValueError, OverflowError):
        return None
    return start, end


def _counter_day(value):
    bounds = _bounds(value)
    if bounds is None:
        return None
    start, end = bounds
    readings, previous_t = [], None
    for sample in value['samples']:
        if not isinstance(sample, dict):
            return None
        t = _number(sample.get('t'))
        if t is None or not start <= t <= end or previous_t is not None and t <= previous_t:
            return None
        previous_t = t
        values = sample.get('values')
        state = values.get(HOUSE_COUNTER) if isinstance(values, dict) else None
        if not isinstance(state, dict) or state.get('value') is None:
            continue
        number = _number(state.get('value'))
        if number is None or not 0 <= number <= 1e9:
            return None
        updated = _iso(state.get('source_updated'))
        if updated is None or not -5 <= t - updated <= MAX_GAP:
            continue
        if readings:
            dt, increment = t - readings[-1][0], number - readings[-1][1]
            if increment < 0 or increment > COUNTER_MAX_KW * dt / 3600 + .11:
                return None
        readings.append((t, number))
    if len(readings) < 2 or readings[0][0] - start > 30 or end - readings[-1][0] > 30:
        return None
    delta = readings[-1][1] - readings[0][1]
    observed = readings[-1][0] - readings[0][0]
    if delta > COUNTER_MAX_KW * observed / 3600 + .11:
        return None
    missing = end - start - observed
    upper = delta + COUNTER_QUANTIZATION_KWH + COUNTER_MAX_KW * missing / 3600
    return {'date': value['date'], 'start': start, 'end': end, 'upper': upper, 'readings': readings}


def _rolling_counter_upper(days):
    """Bound every 24h window, including ends hidden inside archive gaps.

    For a window ending between two readings, use its following counter and
    the counter preceding the window's start. This includes whole increments
    hidden in either boundary gap. The earliest possible end in each reading
    interval gives its largest upper bound, so checking those intervals covers
    every possible end, not just the sampled timestamps.
    """
    ordered = sorted(days, key=lambda item: item['start'])
    readings = []
    for day in ordered:
        for t, value in day['readings']:
            if readings:
                dt, delta = t - readings[-1][0], value - readings[-1][1]
                if dt == 0 and delta == 0:
                    continue
                if dt <= 0 or delta < 0 or delta > COUNTER_MAX_KW * dt / 3600 + .11:
                    return None
            readings.append((t, value))
    start, end = ordered[0]['start'], ordered[-1]['end']
    if end - start < 86400:
        return None
    first_t, first_value = readings[0]
    last_t, last_value = readings[-1]
    if first_t > start:
        readings.insert(0, (start, max(0, first_value - COUNTER_MAX_KW * (first_t - start) / 3600)))
    if last_t < end:
        readings.append((end, last_value + COUNTER_MAX_KW * (end - last_t) / 3600))
    times = [item[0] for item in readings]
    upper = None
    for index in range(1, len(readings)):
        earliest_end = max(start + 86400, readings[index - 1][0])
        if earliest_end > readings[index][0]:
            continue
        left = bisect_right(times, earliest_end - 86400) - 1
        if left < 0:
            return None
        delta = readings[index][1] - readings[left][1]
        upper = max(upper or 0, delta)
    if upper is None:
        return None
    return min(COUNTER_MAX_KW * 24 + COUNTER_QUANTIZATION_KWH, upper + COUNTER_QUANTIZATION_KWH)


def _day(value):
    bounds = _bounds(value)
    if bounds is None:
        return None
    start, end = bounds
    points = []
    for sample in value['samples']:
        if not isinstance(sample, dict):
            return None
        t = _number(sample.get('t'))
        if t is None or not start <= t <= end or points and t <= points[-1]['t']:
            return None
        sample = {**sample, 't': t}
        points.append({'t': t, 'house': _value(sample, LOAD, 30000),
                       'pv': _value(sample, PV, INVERTER_KW * 1000),
                       'soc': _value(sample, SOC, 100)})
    buckets = {}
    for first, last in zip(points, points[1:]):
        duration = last['t'] - first['t']
        if not 0 < duration <= MAX_GAP:
            continue
        lo = first['t']
        while lo < last['t']:
            hour = math.floor(lo / 3600) * 3600
            hi = min(last['t'], hour + 3600)
            bucket = buckets.setdefault(hour, {'house_s': 0, 'house_ws': 0, 'pv_s': 0, 'pv_ws': 0})
            for name in ('house', 'pv'):
                if first[name] is None or last[name] is None:
                    continue
                if name == 'pv' and (first['soc'] is None or last['soc'] is None or max(first['soc'], last['soc']) >= 95):
                    continue
                a = first[name] + (last[name] - first[name]) * (lo - first['t']) / duration
                b = first[name] + (last[name] - first[name]) * (hi - first['t']) / duration
                bucket[name + '_s'] += hi - lo
                bucket[name + '_ws'] += (a + b) / 2 * (hi - lo)
            lo = hi
    # A large missing interval may hide the day's load peaks. Do not normalize
    # a partly observed hour/day into a complete low-demand profile.
    if sum(b['house_s'] for b in buckets.values()) < end - start - DAY_MISSING_SECONDS:
        return None
    house, ratios = {}, {}
    forecast = _weather(value.get('weather'))
    for hour, bucket in buckets.items():
        local_hour = datetime.fromtimestamp(hour, LOCAL).hour
        if bucket['house_s'] >= 3600 - HOUR_MISSING_SECONDS:
            mean = bucket['house_ws'] / bucket['house_s'] / 1000
            house[local_hour] = max(house.get(local_hour, 0), mean)
        if (forecast and hour - 48 * 3600 <= forecast['issued'] <= hour
                and bucket['pv_s'] >= 3600 - HOUR_MISSING_SECONDS):
            ghi = forecast['rows'].get(hour + 3600)
            if ghi is not None and ghi >= 50:
                ratio = bucket['pv_ws'] / bucket['pv_s'] / 1000 / ghi
                # Repeated autumn hour counts once per day, at its lower ratio.
                ratios[local_hour] = min(ratios.get(local_hour, ratio), ratio)
    return {'date': value['date'], 'end': end, 'house': house, 'ratios': ratios}


def build_history(days):
    """Summarize >=2 complete real archive days; malformed days add no evidence.

    Each day is {date, start, end, samples, weather}; date is local YYYY-MM-DD,
    start/end are epoch seconds or timezone-aware ISO timestamps. Historical
    weather must have been issued before its calibrated hour, never afterwards.
    """
    days = days if isinstance(days, list) else []
    dates = [item.get('date') for item in days if isinstance(item, dict)]
    valid = []
    for item in days:
        result = _day(item)
        if result and dates.count(result['date']) == 1:
            valid.append(result)
    newest = max((item['end'] for item in valid), default=0)
    valid = [item for item in valid if newest - item['end'] <= MODEL_MAX_AGE]
    house, pv, counts = [], [], []
    for hour in range(24):
        loads = [item['house'][hour] for item in valid if hour in item['house']]
        ratios = [item['ratios'][hour] for item in valid if hour in item['ratios']]
        house.append(max(loads) * 1.25 if len(loads) >= 2 else None)
        pv.append(min(ratios) * .5 if len(ratios) >= 2 else None)
        counts.append(len(ratios))
    model = {'version': MODEL_VERSION, 'timezone': 'Europe/Prague', 'mode': 'hourly',
            'as_of': max((item['end'] for item in valid), default=None),
            'complete_days': len(valid), 'house_kw': house, 'pv_ratio': pv,
            'pv_calibration_days': counts, 'dates': sorted(item['date'] for item in valid),
            'sources': [LOAD, PV, SOC, 'prior_issued_shortwave_radiation'],
            'quality': 'calibrated' if len(valid) >= 2 and all(v is not None for v in house) else 'insufficient'}
    if model['quality'] != 'insufficient':
        return model
    counter_days = []
    for item in days:
        result = _counter_day(item)
        if result and dates.count(result['date']) == 1:
            counter_days.append(result)
    newest = max((item['end'] for item in counter_days), default=0)
    counter_days = [item for item in counter_days if newest - item['end'] <= MODEL_MAX_AGE]
    if len(counter_days) < 2:
        return model
    rolling_upper = _rolling_counter_upper(counter_days)
    if rolling_upper is None:
        return model
    return {'version': MODEL_VERSION, 'timezone': 'Europe/Prague', 'mode': 'energy_only',
            'quality': 'energy_only', 'complete_days': len(counter_days), 'as_of': newest,
            'energy_bound_method': ENERGY_BOUND_METHOD,
            'daily_house_kwh_upper': max(item['upper'] for item in counter_days),
            'house_energy_kwh_24h_upper': rolling_upper,
            'dates': sorted(item['date'] for item in counter_days), 'sources': [HOUSE_COUNTER]}


def reserve_for_home(model, weather, now, capacity_kwh=23.5, house_floor_soc=30, charge_limit_kw=0):
    """Reserve for the next 24 actual hours, ending at the ordinary house floor.

    Missing PV evidence means zero credited production, not measured zero PV.
    Reverse budgeting detects a future deficit that cannot fit in the battery,
    even when large earlier PV would otherwise make a total-energy sum pass.
    PV serves the house first. Unknown charging power permits no storage credit;
    a positive limit must come from the adapter's fresh configured/BMS bounds.
    Load and calibrated PV are treated as AC-side energy, storage as DC energy.
    """
    now, capacity, floor_soc = _time(now), _number(capacity_kwh), _number(house_floor_soc)
    charge_limit = _number(charge_limit_kw)
    charge_limit = min(INVERTER_KW, charge_limit) if charge_limit is not None and charge_limit > 0 else 0
    result = {'required_soc': 100, 'quality': 'insufficient',
              'reason': 'Chybí dostatečná čerstvá historie spotřeby domu.',
              'sources': [LOAD], 'estimated_house_kwh': None, 'credited_pv_kwh': 0,
              'forecast_pv_kwh': 0, 'direct_pv_kwh': 0,
              'battery_charge_kwh': 0, 'potential_battery_charge_kwh': 0, 'battery_discharge_kwh': None,
              'pv_forecast_known': False, 'feasible': False, 'needed_start_kwh': None,
              'horizon_start': now, 'horizon_end': now + 86400 if now is not None else None,
              'assumptions': {'house_profile_factor': 1.25, 'pv_calibration_factor': .5,
                              'discharge_efficiency': STORAGE_EFFICIENCY,
                              'charge_efficiency': STORAGE_EFFICIENCY,
                              'storage_efficiency_basis': 'policy_assumption',
                              'charge_limit_kw': charge_limit, 'charge_limit_known': charge_limit > 0,
                              'capacity_basis': 'configured_nominal'}}
    if now is None or capacity is None or capacity <= 0 or floor_soc is None or not 0 <= floor_soc <= 100:
        result['reason'] = 'Neplatný čas nebo kapacita baterie.'
        return result
    try:
        datetime.fromtimestamp(now + 86400, LOCAL)
    except (ValueError, OverflowError, OSError):
        result['reason'] = 'Neplatný čas.'
        return result
    model = model if isinstance(model, dict) else {}
    as_of = _time(model.get('as_of'))
    house = model.get('house_kw')
    complete = model.get('complete_days')
    if (model.get('version') != MODEL_VERSION or model.get('timezone') != 'Europe/Prague'
            or model.get('quality') == 'insufficient' or not isinstance(complete, int)
            or complete < 2 or as_of is None or not 0 <= now - as_of <= MODEL_MAX_AGE):
        return result
    if model.get('mode') == 'energy_only':
        daily = _number(model.get('daily_house_kwh_upper'))
        upper = _number(model.get('house_energy_kwh_24h_upper'))
        if (model.get('quality') != 'energy_only' or daily is None or upper is None
                or model.get('energy_bound_method') != ENERGY_BOUND_METHOD
                or not .2 <= daily <= 625.31 or not .2 <= upper <= 600.2
                or model.get('sources') != [HOUSE_COUNTER]):
            return result
        house_energy = upper * 1.25
        discharge = house_energy / STORAGE_EFFICIENCY
        needed = capacity * (floor_soc / 100) + discharge
        feasible = needed <= capacity + 1e-9
        result.update(required_soc=min(100, max(60, math.ceil(needed / capacity * 100 - 1e-9))),
                      quality='energy_only', sources=[HOUSE_COUNTER],
                      daily_house_kwh_upper=daily, house_energy_kwh_24h_upper=upper,
                      energy_bound_method=ENERGY_BOUND_METHOD, estimated_house_kwh=house_energy,
                      battery_discharge_kwh=discharge, needed_start_kwh=needed, feasible=feasible,
                      reason='Celodenní čítač chrání energii domu; průběh spotřeby není znám, PV se nezapočítává.',
                      caveat='house_load_shape_unknown_no_pv_credit')
        return result
    if (model.get('mode', 'hourly') != 'hourly' or not isinstance(house, list) or len(house) != 24
            or any(_number(v) is None or not 0 <= _number(v) <= 37.5 for v in house)):
        return result
    forecast = _weather(weather)
    if forecast and not 0 <= now - forecast['issued'] <= WEATHER_MAX_AGE:
        forecast = None
    ratios = model.get('pv_ratio', [])
    counts = model.get('pv_calibration_days', [])
    intervals, cursor, known = [], now, bool(forecast)
    while cursor < now + 86400:
        end = min(now + 86400, (math.floor(cursor / 3600) + 1) * 3600)
        hour = datetime.fromtimestamp(cursor, LOCAL).hour
        hours = (end - cursor) / 3600
        ghi = forecast['rows'].get((math.floor(cursor / 3600) + 1) * 3600) if forecast else None
        ratio = _number(ratios[hour]) if isinstance(ratios, list) and len(ratios) == 24 else None
        count = _number(counts[hour]) if isinstance(counts, list) and len(counts) == 24 else None
        calibrated = ratio is not None and 0 <= ratio <= .24 and count is not None and count >= 2
        # Known forecast darkness needs no PV calibration; daylight does.
        known = known and ghi is not None and (ghi == 0 or calibrated)
        pv = min(INVERTER_KW, ghi * ratio) * hours if ghi is not None and calibrated else 0
        load = float(house[hour]) * hours
        direct = min(load, pv)
        discharge = (load - direct) / STORAGE_EFFICIENCY
        charge = min((pv - direct) * STORAGE_EFFICIENCY, charge_limit * hours)
        intervals.append({'load': load, 'pv': pv, 'direct': direct, 'charge': charge, 'discharge': discharge})
        cursor = end
    floor = capacity * (floor_soc / 100)
    needed, feasible = floor, True
    for interval in reversed(intervals):
        # Only future household demand can use this surplus. Anything beyond
        # the terminal floor's need remains forecast potential, not a credit.
        interval['used_charge'] = min(interval['charge'], max(0, needed - floor))
        needed = max(floor, needed + interval['discharge'] - interval['used_charge'])
        if needed > capacity + 1e-9:
            feasible = False
    result.update(estimated_house_kwh=sum(row['load'] for row in intervals),
                  credited_pv_kwh=sum(row['direct'] + row['used_charge'] / STORAGE_EFFICIENCY for row in intervals),
                  forecast_pv_kwh=sum(row['pv'] for row in intervals),
                  direct_pv_kwh=sum(row['direct'] for row in intervals),
                  battery_charge_kwh=sum(row['used_charge'] for row in intervals),
                  potential_battery_charge_kwh=sum(row['charge'] for row in intervals),
                  battery_discharge_kwh=sum(row['discharge'] for row in intervals),
                  needed_start_kwh=needed, feasible=feasible, pv_forecast_known=known,
                  required_soc=min(100, max(60, math.ceil(needed / capacity * 100 - 1e-9))) if feasible else 100,
                  sources=[LOAD] + ([PV, SOC, 'prior_issued_shortwave_radiation', 'current_shortwave_radiation']
                                   if any(row['pv'] > 0 for row in intervals) else []),
                  quality=('calibrated' if known and charge_limit > 0 else 'conservative') if feasible else 'insufficient',
                  reason=('Rezerva pokrývá spotřebu domu, ztráty a kalibrovanou předpověď.' if known and charge_limit > 0 else
                          'Rezerva domu a přímé PV; neověřené nabíjení se nezapočítává.' if known else
                          'Rezerva domu; neznámá výroba se nezapočítává.') if feasible else
                         'Budoucí potřeba domu přesahuje kapacitu baterie; prodej baterie blokován.')
    return result

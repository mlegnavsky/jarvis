"""Daily positive-price block and actual-SOC export budget; no forecast gate."""
from datetime import date, datetime, time, timedelta
import math
from zoneinfo import ZoneInfo

LOCAL = ZoneInfo('Europe/Prague')
EXPORT_LIMIT_W = 9300


def _number(value):
    if isinstance(value, bool):
        return None
    try:
        value = float(value)
        return value if math.isfinite(value) else None
    except (TypeError, ValueError, OverflowError):
        return None


def _timestamp(value):
    if not isinstance(value, (str, datetime)):
        return _number(value)
    try:
        value = datetime.fromisoformat(value) if isinstance(value, str) else value
        if value.tzinfo is None or value.utcoffset() is None:
            return None
        return _number(value.timestamp())
    except (ValueError, TypeError, OverflowError, OSError):
        return None


def choose_daily_block(quotes, day, now, block_minutes=120):
    """Choose the best complete future block within one Prague calendar day.

    Each quote is {start, end, net}, already converted after the selling fee.
    A selected running block must be kept by the caller; this function chooses
    only blocks whose start has not passed, never a stale earlier selection.
    """
    now, minutes = _timestamp(now), _number(block_minutes)
    if now is None or minutes is None or not 0 < minutes <= 1500 or minutes % 15:
        return None
    if not isinstance(quotes, (list, tuple)):
        return None
    try:
        civil_day = date.fromisoformat(day)
        start = datetime.combine(civil_day, time(), LOCAL).timestamp()
        end = datetime.combine(civil_day + timedelta(days=1), time(), LOCAL).timestamp()
    except (TypeError, ValueError, OverflowError, OSError):
        return None
    if now >= end:
        return None
    quarters = int(minutes / 15)
    by_start = {}
    for quote in quotes:
        if not isinstance(quote, dict):
            continue
        lo = _timestamp(quote.get('start'))
        if lo is None or lo % 900 or not start <= lo < end:
            continue
        hi, net = _timestamp(quote.get('end')), _number(quote.get('net'))
        valid = hi == lo + 900 and hi <= end and net is not None and net > 0
        by_start.setdefault(lo, []).append(net if valid else None)
    best = None
    for lo in sorted(by_start):
        if lo < now or lo + minutes * 60 > end:
            continue
        values = []
        for index in range(quarters):
            matches = by_start.get(lo + index * 900, [])
            if len(matches) != 1 or matches[0] is None:
                break
            values.append(matches[0])
        if len(values) != quarters:
            continue
        average = sum(value / quarters for value in values)
        if not math.isfinite(average):
            continue
        if best is None or average > best['average_net']:
            best = {'start': lo, 'end': lo + minutes * 60, 'average_net': average,
                    'net': average, 'quarters': quarters, 'day': day,
                    'block_minutes': int(minutes),
                    'reason': 'Nejvýhodnější zbývající souvislý blok s kladným výkupem.',
                    'assumptions': {'timezone': 'Europe/Prague', 'all_quarters_positive': True}}
    return best


def size_sale(soc, capacity_kwh, window_start, window_end, now, house_w, pv_w=0,
              max_export_w=9300, minimum_soc=60, eta=math.sqrt(.9)):
    """Bound AC grid export by actual DC stored energy above the sale floor.

    The fresh instantaneous house power is held constant over the remaining
    window as an explicit estimate. Current PV receives no future energy credit.
    Before the selected start (including T−1 minute), size its whole duration.
    Device current, battery power and BMS limits remain the caller's responsibility.
    """
    soc, capacity, house = _number(soc), _number(capacity_kwh), _number(house_w)
    start, end, now = _timestamp(window_start), _timestamp(window_end), _timestamp(now)
    floor, efficiency, export_cap = _number(minimum_soc), _number(eta), _number(max_export_w)
    pv = _number(pv_w)
    valid_floor = floor is not None and 0 <= floor <= 100
    floor = max(60, floor) if valid_floor else 60
    result = {'available_above_floor_kwh': 0, 'expected_house_kwh': 0,
              'sale_budget_kwh': 0, 'power_w': 0, 'minimum_soc': floor,
              'timeleft_seconds': 0, 'timeleft': 0, 'mode': 'hold',
              'reason': 'Čekám na platný stav baterie, spotřeby a prodejního okna.',
              'assumptions': {'pv_credit_kwh': 0,
                              'house_estimate': 'fresh_instantaneous_power_constant_over_remaining_window',
                              'discharge_efficiency': efficiency if efficiency is not None and 0 < efficiency <= 1 else None,
                              'capacity_basis': 'configured_capacity_times_actual_soc',
                              'device_current_and_power_limits': 'enforced_by_caller'}}
    if (soc is None or not 0 <= soc <= 100 or capacity is None or capacity <= 0
            or house is None or house < 0 or pv is None or pv < 0 or not valid_floor
            or efficiency is None or not 0 < efficiency <= 1
            or export_cap is None or export_cap < 0 or start is None or end is None or now is None
            or not 0 < end - start <= 90000):
        return result
    seconds = max(0, end - max(start, now))
    if seconds <= 0:
        result['reason'] = 'Vybrané prodejní okno již skončilo.'
        return result
    hours = seconds / 3600
    available = capacity * max(0, soc - floor) / 100
    expected_house = house / 1000 * hours
    budget = max(0, available * efficiency - expected_house)
    target = min(EXPORT_LIMIT_W, export_cap, budget / hours * 1000)
    if not all(math.isfinite(value) for value in (available, expected_house, budget, target)):
        return result
    result.update(available_above_floor_kwh=available, expected_house_kwh=expected_house,
                  sale_budget_kwh=budget, timeleft_seconds=seconds, timeleft=seconds)
    if soc <= floor:
        result['reason'] = 'Baterie dosáhla prodejní rezervy; prodej zastaven.'
    elif target < 100:
        result['reason'] = 'Energie nad rezervou pokryje dům; pro prodej nezbývá alespoň100 W.'
    else:
        result.update(power_w=int(target), mode='battery',
                      reason='Prodej z aktuální energie nad rezervou po odečtení ztrát a spotřeby domu.')
    return result

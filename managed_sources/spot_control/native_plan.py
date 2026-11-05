"""Pure, bounded register values for a future native ExportFirst TOU window.

This module performs no device I/O and supplies no commissioning approval. The
controller must separately verify fresh health/electrical data, arm before the
deadline, enable register 142 only at start, observe expiry, and restore the
ordinary house schedule. The native weekday mask is weekly, never one-shot.
"""
from collections.abc import Mapping
from datetime import datetime, timedelta
import math
from zoneinfo import ZoneInfo

TZ = ZoneInfo('Europe/Prague')


def _finite(name, value):
    if isinstance(value, bool):
        raise ValueError(f'{name} must be a finite number, not a boolean')
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f'{name} must be a finite number') from exc
    if not math.isfinite(number):
        raise ValueError(f'{name} must be a finite number')
    return number


def _unambiguous(local):
    """Reject both gaps and repeated Prague wall times, including either fold."""
    wall = local.replace(tzinfo=None)
    first = wall.replace(tzinfo=TZ, fold=0)
    second = wall.replace(tzinfo=TZ, fold=1)
    if (first.utcoffset() != second.utcoffset()
            or datetime.fromtimestamp(first.timestamp(), TZ).replace(tzinfo=None) != wall):
        raise ValueError('Native window contains an ambiguous or nonexistent Prague clock time')


def _quarter_prices(quotes):
    """Retain duplicates: uncertainty must never silently become a valid price."""
    prices = {}
    try:
        rows = iter(quotes)
    except TypeError as exc:
        raise ValueError('quotes must contain dated market quarters') from exc
    for row in rows:
        if not isinstance(row, Mapping):
            raise ValueError('Each quote must be a dated market quarter')
        start = _finite('quote.start', row.get('start'))
        end = _finite('quote.end', row.get('end'))
        net = _finite('quote.net', row.get('net'))
        if start % 900 or end - start != 900:
            raise ValueError('Quotes must be aligned 900-second epoch quarters')
        prices.setdefault(start, []).append(net)
    return prices


def _positive_coverage(prices, start, observer_deadline):
    quarter = math.floor(start / 900) * 900
    while quarter <= observer_deadline:
        values = prices.get(quarter, ())
        if len(values) != 1 or values[0] <= 0:
            return False
        quarter += 900
    return True


def battery_window_plan(native_clock, now, power_w, duration_minutes, minimum_soc,
                        battery_voltage, bms_discharge_a, configured_discharge_a,
                        house_program_power, quotes, valid_until=None, window_end=None):
    """Return JSON-safe values; reject invalid inputs with ``ValueError``.

    ``native_clock`` is an aware datetime, normalized to Europe/Prague; ``now``
    and quote boundaries are epoch seconds. ``times_hhmm`` contains six native
    integer HHMM values. Duration is 5..60 minutes and rounds down to 5 minutes;
    missing, duplicate or nonpositive future quarters shorten it further while
    preserving 60 seconds of positively priced observer/cleanup coverage.

    ``power_w`` is the grid-export register 143 cap, bounded to 9300 W. TOU powers
    are total battery DC power including the house, independently bounded by
    the existing house-program power, BMS/configured current and the 10 kW pack.
    No result guarantees grid export or authorizes production operation.
    """
    now = _finite('now', now)
    power_w = _finite('power_w', power_w)
    duration_minutes = _finite('duration_minutes', duration_minutes)
    minimum_soc = _finite('minimum_soc', minimum_soc)
    battery_voltage = _finite('battery_voltage', battery_voltage)
    bms_discharge_a = _finite('bms_discharge_a', bms_discharge_a)
    configured_discharge_a = _finite('configured_discharge_a', configured_discharge_a)
    house_program_power = _finite('house_program_power', house_program_power)
    if valid_until is not None:
        valid_until = _finite('valid_until', valid_until)
        if valid_until <= now:
            raise ValueError('Native arming command has expired')
    if window_end is not None:
        window_end = _finite('window_end', window_end)
        if window_end <= now:
            raise ValueError('Selected business block has ended')

    if not 5 <= duration_minutes <= 60:
        raise ValueError('Native window duration must be 5..60 minutes')
    if not 0 <= minimum_soc <= 98:
        raise ValueError('Native minimum SOC must be 0..98 percent')
    if power_w < 100:
        raise ValueError('Grid export cap must be at least 100 W')
    if not 44.8 <= battery_voltage <= 57.6:
        raise ValueError('Battery voltage must be 44.8..57.6 V')
    if not 1 <= bms_discharge_a <= 200:
        raise ValueError('BMS discharge limit must be 1..200 A')
    if not 1 <= configured_discharge_a <= 350:
        raise ValueError('Configured discharge limit must be 1..350 A')
    if not 1 <= house_program_power <= 65535:
        raise ValueError('Existing house-program power must be 1..65535 W')
    if (not isinstance(native_clock, datetime) or native_clock.tzinfo is None
            or native_clock.utcoffset() is None):
        raise ValueError('Native inverter clock must be timezone aware')
    local = native_clock.astimezone(TZ)
    _unambiguous(local)
    if abs(native_clock.timestamp() - now) > 5:
        raise ValueError('Native inverter clock differs from now by more than 5 seconds')

    minute = math.ceil((local.hour * 60 + local.minute + 1) / 5) * 5
    day = local.replace(hour=0, minute=0, second=0, microsecond=0, fold=0)
    start = day + timedelta(minutes=minute)
    requested_minutes = math.floor(duration_minutes / 5) * 5
    if window_end is not None:
        requested_minutes = min(requested_minutes,
                                math.floor((window_end - start.timestamp()) / 300) * 5)
        if requested_minutes < 5:
            raise ValueError('Selected business block has no five-minute native segment left')
    end = start + timedelta(minutes=requested_minutes)
    # Refuse an unsafe requested time range; price truncation is not a way to
    # salvage a request whose full native boundaries cross midnight or DST.
    if (start.date() != local.date() or end.date() != local.date()
            or minute + requested_minutes + 10 >= 1435):
        raise ValueError('No same-day window with strictly ordered recovery slots is available')
    for boundary in (start, end, end + timedelta(minutes=5), end + timedelta(minutes=10)):
        _unambiguous(boundary)
    if end.timestamp() - start.timestamp() != requested_minutes * 60:
        raise ValueError('Native window crosses a daylight-saving clock transition')

    start_epoch = start.timestamp()
    arm_until = min(start_epoch - 10, valid_until if valid_until is not None else start_epoch - 10)
    if arm_until <= now:
        raise ValueError('Native configuration buffer has expired')
    prices = _quarter_prices(quotes)
    minutes = requested_minutes
    while minutes >= 5:
        end = start + timedelta(minutes=minutes)
        if _positive_coverage(prices, start_epoch, end.timestamp() + 60):
            break
        minutes -= 5
    if minutes < 5:
        raise ValueError('No five-minute native window has unique positive prices through cleanup')

    current_limit_a = math.floor(min(175, configured_discharge_a, bms_discharge_a,
                                     math.floor(10000 / battery_voltage)))
    battery_power_w = math.floor(min(10000, house_program_power, current_limit_a * battery_voltage))
    minimum_soc = max(60, math.ceil(minimum_soc))
    slots = (0, minute, minute + minutes, minute + minutes + 5, minute + minutes + 10, 1435)
    return {
        'start': start_epoch,
        'end': end.timestamp(),
        'observer_deadline': end.timestamp() + 60,
        'arm_until': arm_until,
        'duration_minutes': minutes,
        'times_hhmm': [(m // 60) * 100 + m % 60 for m in slots],
        'socs': [100, minimum_soc, 100, 100, 100, 100],
        'powers': [battery_power_w] * 6,
        'flags': [0] * 6,
        'week_mask': 1 | (1 << (local.weekday() + 1)),
        'current_limit_a': current_limit_a,
        'battery_power_w': battery_power_w,
        'power_w': min(9300, math.floor(power_w)),
        'minimum_soc': minimum_soc,
        'mode': 'ExportFirst',
        'mode_register': 142,
        'mode_value': 0,
        'enable_at': start_epoch,
        'en_register': 145,
        'en_value': 0,
        'production_verified': False,
        'notice': ('This is not a one-shot program: the weekday can recur after 7 days if HA is offline. '
                   'Outside-window SOC 100 blocks ordinary house battery use; the grid supplies a shortfall '
                   'until restoration. TOU power includes house demand; actual grid export also depends on '
                   'PV and house load and is not guaranteed. The controller must enable ExportFirst only '
                   'at start after fresh electrical/health checks; production verification is separate.'),
    }

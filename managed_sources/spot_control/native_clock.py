"""Fixed Deye RTC registers only; callers must first prove the inverter idle."""
import asyncio
from datetime import datetime, timezone
import math
import time
from zoneinfo import ZoneInfo

LOCAL = ZoneInfo('Europe/Prague')


def _now(clock):
    value = clock()
    if isinstance(value, bool):
        raise ValueError('Invalid host timestamp')
    value = float(value)
    if not math.isfinite(value):
        raise ValueError('Nonfinite host timestamp')
    dt = datetime.fromtimestamp(value, timezone.utc).astimezone(LOCAL)
    if not 2000 <= dt.year <= 2255:
        raise ValueError('RTC year outside2000–2255')
    return value, dt


def _decode(raw, reference):
    if (not isinstance(raw, (list, tuple)) or len(raw) != 3
            or any(type(value) is not int or not 0 <= value <= 65535 for value in raw)):
        raise ValueError('Malformed RTC register read')
    parts = (2000 + (raw[0] >> 8), raw[0] & 255,
             raw[1] >> 8, raw[1] & 255, raw[2] >> 8, raw[2] & 255)
    candidates = []
    for fold in (0, 1):
        dt = datetime(*parts, tzinfo=LOCAL, fold=fold)
        # A nonexistent spring wall-clock hour must never look verified.
        back = dt.astimezone(timezone.utc).astimezone(LOCAL)
        if (back.year, back.month, back.day, back.hour, back.minute, back.second) == parts:
            candidates.append(dt)
    if not candidates:
        raise ValueError('Nonexistent RTC wall-clock time')
    return min(candidates, key=lambda dt: abs(dt.timestamp() - reference))


async def sync_native_clock(device, now=time.time, sleep=asyncio.sleep, admit=None):
    """Write62–64 after acquiring the native transport lock, then prove ticks.

    The entire operation has a15s deadline. No fallback queues a timestamp via
    device.execute: the write uses the supported transport under its semaphore.
    Final verification goes independently through device.execute after release.
    This helper changes no mode/export settings and does not authorize its use
    during an active program; idle-state admission belongs to the caller.
    """
    result = {'supported': False, 'verified': False, 'clock': None, 'raw': None,
              'error_seconds': None, 'before_timestamp': None, 'after_timestamp': None,
              'immediate_clock': None, 'immediate_raw': None, 'immediate_timestamp': None,
              'progress_seconds': None, 'error': None}
    modbus = getattr(device, 'modbus', None)
    semaphore = getattr(modbus, '_semaphore', None)
    get_response = getattr(modbus, 'get_response', None)
    execute = getattr(device, 'execute', None)
    if (semaphore is None or not callable(get_response) or not callable(execute)
            or not callable(getattr(semaphore, '__aenter__', None))
            or not callable(getattr(semaphore, '__aexit__', None))):
        result['error'] = 'Unsupported native RTC transport'
        return result
    result['supported'] = True
    try:
        async with asyncio.timeout(15):
            async with semaphore:
                if admit is not None and await admit(get_response) is not True:
                    raise ValueError('Native RTC admission was not confirmed')
                # Computing the time before this lock would write queue delay.
                written_at, dt = _now(now)
                result['before_timestamp'] = written_at
                data = [((dt.year - 2000) << 8) | dt.month,
                        (dt.day << 8) | dt.hour, (dt.minute << 8) | dt.second]
                await get_response(16, 62, data=data)
                await sleep(1)
                immediate_raw = await get_response(3, 62, count=3)
                immediate_at, _ = _now(now)
                immediate = _decode(immediate_raw, immediate_at)
                result.update(immediate_raw=list(immediate_raw), immediate_clock=immediate.isoformat(),
                              immediate_timestamp=immediate_at)
            await sleep(3)
            raw = await execute(3, 62, count=3)
            after, _ = _now(now)
            dt = _decode(raw, after)
            error = dt.timestamp() - after
            progress = dt.timestamp() - immediate.timestamp()
            verified = abs(error) <= 5 and progress >= 2 and after - immediate_at >= 2
            result.update(raw=list(raw), clock=dt.isoformat(), after_timestamp=after,
                          error_seconds=error, progress_seconds=progress, verified=verified,
                          error=None if verified else 'RTC offset or independent clock progress not verified')
    except TimeoutError:
        result['error'] = 'Native RTC synchronization timed out'
    except Exception as exc:
        result['error'] = f'{type(exc).__name__}: {exc}'
    return result

"""Read-only health evidence. Recovery is allowed only for proven data loss."""
import math
from copy import deepcopy

MEASUREMENTS = ('sensor.inverter_battery', 'sensor.inverter_pv_power',
                'sensor.inverter_battery_power', 'sensor.inverter_grid_power',
                'sensor.inverter_battery_temperature')
STATUS = {'sensor.inverter_device_state':'Normal', 'sensor.inverter_device_alarm':'OK',
          'sensor.inverter_device_fault':'OK', 'binary_sensor.inverter_battery_alarm':'off',
          'binary_sensor.inverter_battery_fault':'off'}
TRANSIENT_CODES = frozenset(('missing', 'unavailable', 'stale'))


def finite(value):
    if isinstance(value, bool):
        return None
    try:
        value = float(value)
        return value if math.isfinite(value) else None
    except (TypeError, ValueError, OverflowError):
        return None


def evaluate_health(states, now, charging=False):
    """Consume {entity: {state, reported_at}}; never invoke a device service."""
    issues = []

    def add(code, entity_id, value, age, expected):
        issues.append(dict(code=code, entity_id=entity_id, value=value,
                           age_seconds=age, expected=expected))

    if charging:
        add('charging_active', None, True, None, False)
    for entity in (*MEASUREMENTS, *STATUS):
        sample = states.get(entity)
        maximum_age = 30 if entity in MEASUREMENTS else 60
        if sample is None:
            add('missing', entity, None, None, 'fresh measurement')
            continue
        value = sample.get('state')
        stamp = finite(sample.get('reported_at'))
        age = now-stamp if stamp is not None else None
        if age is None or age < 0:
            add('timestamp', entity, value, age, 'valid timestamp at or before now')
        elif (age >= maximum_age if entity in MEASUREMENTS else age > maximum_age):
            add('stale', entity, value, age, 'age < '+str(maximum_age)+'s')
        if value in (None, 'unknown', 'unavailable'):
            add('unavailable', entity, value, age, 'available value')
            continue
        if entity in STATUS:
            if value != STATUS[entity]:
                add('device_fault', entity, value, age, STATUS[entity])
        elif finite(value) is None:
            add('invalid', entity, value, age, 'finite number')
        elif entity.endswith('battery_temperature') and not 0 <= float(value) < 45:
            add('temperature', entity, value, age, '0 <= temperature < 45 C')
    return dict(healthy=not issues, checked_at=now, issues=issues,
                transient_only=bool(issues) and all(i['code'] in TRANSIENT_CODES for i in issues))


def recoverable_battery_stop(proof):
    if (proof.get('purpose') != 'automatic' or proof.get('stop_verified') is not True
            or proof.get('conflicts') or proof.get('reason') not in ('health','stale','measurement','electrical_stale')):
        return False
    health = (proof.get('failure_context') or {}).get('health') or {}
    issues = health.get('issues') or []
    return transient_health(health)


def transient_health(health):
    issues = health.get('issues') or []
    return (health.get('healthy') is False and health.get('transient_only') is True
            and bool(issues) and all(isinstance(i,dict) and i.get('code') in TRANSIENT_CODES for i in issues))


def control_transport_failure(health,now,error):
    """Exact failed native read evidence, never an invented healthy/measurement ACK."""
    report=deepcopy(health)
    issues=list(report.get('issues') or [])
    issues.append({'code':'unavailable','entity_id':'native_controls','value':None,
                   'age_seconds':None,'expected':'fresh physical control-register read',
                   'source':'refresh_sale_controls','error':type(error).__name__+': '+str(error)[:160]})
    report.update(healthy=False,checked_at=now,issues=issues,
                  transient_only=all(isinstance(i,dict) and i.get('code') in TRANSIENT_CODES for i in issues))
    return report

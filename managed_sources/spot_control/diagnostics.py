"""Versioned read-only diagnostic projection; private history stays in its journal."""
from copy import deepcopy
from datetime import datetime
from zoneinfo import ZoneInfo
import re


SECRET_KEYS = ('password','secret','token','authorization','credential','cookie','api_key')


def redact(value):
    if isinstance(value, dict):
        return {key:('[redacted]' if any(word in str(key).lower() for word in SECRET_KEYS)
                     else redact(item)) for key,item in value.items()}
    if isinstance(value, (list, tuple)):
        return [redact(item) for item in value]
    if isinstance(value,str):
        return re.sub(r'(https?://)[^/\s@]+@',r'\1[redacted]@',value)
    return value


def diagnostic_snapshot(body, now):
    health=body.get('health') or {}
    if body.get('active') and body.get('phase')=='stopping':stage='stopping'
    elif not body.get('ready'):stage='starting'
    elif not body.get('healthy'):
        stage='measurement_unavailable' if health.get('transient_only') else 'safety_block'
    elif body.get('profile_issues'):stage='configuration_mismatch'
    elif (body.get('settings') or {}).get('inhibited'):stage='paused'
    elif body.get('active') and body.get('observed'):stage='export_confirmed'
    elif body.get('active'):stage='waiting_for_export'
    elif not body.get('automatic_requested',(body.get('settings') or {}).get('requested_automatic')):stage='off'
    elif (body.get('completed_battery_plan') or {}).get('day')==datetime.fromtimestamp(now,ZoneInfo('Europe/Prague')).date().isoformat():stage='plan_complete'
    else:stage='waiting'
    measurements={}
    for entity,sample in (body.get('telemetry') or {}).items():
        try:
            stamp=datetime.fromisoformat(sample['source_reported']).timestamp()
            age=now-stamp
        except (KeyError,ValueError,TypeError,OverflowError):
            age=None
        measurements[entity]={'value':sample.get('state'),'source_reported':sample.get('source_reported'),
                              'age_seconds':age,'fresh':age is not None and 0<=age<30}
    result={'schema_version':1,'captured_at':now,'runtime_version':body.get('version'),
            'stage':stage,'phase':body.get('phase'),'mode':body.get('mode'),
            'owner_requested':bool(body.get('automatic_requested',(body.get('settings') or {}).get('requested_automatic'))),
            'operational_automatic':bool((body.get('settings') or {}).get('automatic')),
            'reason':body.get('reason'),'error':body.get('error'),'health':deepcopy(health),
            'profile_issues':deepcopy(body.get('profile_issues') or []),'measurements':measurements,
            'selected_block':deepcopy(body.get('selected_block')),
            'completed_battery_plan':deepcopy(body.get('completed_battery_plan')),
            'recovery':deepcopy(body.get('measurement_recovery') or {}),
            'last_stop':deepcopy(body.get('diagnostic_stop') or body.get('last_stop')),
            'history':{'retention':'permanent','archive_error':body.get('history_error') or '',
                       'report_error':body.get('report_error') or ''}}
    return redact(result)

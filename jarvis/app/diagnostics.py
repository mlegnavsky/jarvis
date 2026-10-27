"""Read-only, bounded diagnostics over fixed internal HA/Supervisor paths."""
import asyncio
import re
import time
import aiohttp
from .ha import now

SUSPECT = re.compile(r'password|passwd|secret|token|credential|authorization|bearer|cookie|session|api.?key|access.?key|private.?key|[A-Za-z0-9_+/=-]{40,}|https?://[^\s/]*@|eyJ[A-Za-z0-9_-]+\.', re.I)


def bounded_logs(text, max_lines=100, max_chars=16000):
    lines = text.splitlines()
    selected = lines[-max_lines:]
    redacted = 0
    output = []
    remaining = max_chars
    for line in selected:
        line = re.sub(r'\x1b\[[0-9;]*[A-Za-z]', '', line)
        line = ''.join(c for c in line if c.isprintable() or c == '\t')
        if SUSPECT.search(line):
            line = '<redacted suspect log line>'
            redacted += 1
        if len(line) > remaining:
            break
        output.append(line)
        remaining -= len(line) + 1
    return {'lines': output, 'omitted_lines': len(lines) - len(output), 'redacted_lines': redacted}


async def logs(sup, path):
    """Only callers construct path from fixed routes and validated addon slugs."""
    session = await sup._session()
    async with session.get(sup.base + path, headers={'Authorization': 'Bearer ' + sup.token},
            timeout=aiohttp.ClientTimeout(total=sup.timeout), allow_redirects=False) as response:
        if response.status != 200:
            raise ValueError('logs_unavailable')
        # StreamReader.read(n) may yield a single short network chunk before EOF.
        # Read until EOF or one byte beyond the cap, without buffering an unbounded body.
        data = bytearray()
        while len(data) < 65537:
            chunk = await response.content.read(65537 - len(data))
            if not chunk:
                break
            data.extend(chunk)
        value = bounded_logs(data[:65536].decode('utf-8', errors='replace'))
        value['source_truncated'] = len(data) > 65536
        return value


async def websocket_query(sup, command, arguments=None):
    ws = None
    try:
        async with asyncio.timeout(sup.timeout):
            ws = await sup._websocket()
            await ws.send_json({**(arguments or {}), 'id': 1, 'type': command})
            value = await ws.receive_json()
            if value.get('id') != 1 or value.get('success') is not True:
                raise ValueError('diagnostic_unavailable')
            return value.get('result')
    finally:
        if ws:
            await ws.close()


def select(value, fields):
    return {key: value[key] for key in fields if key in value}


async def stage(call, sanitize):
    started = time.monotonic()
    try:
        value = sanitize(await call())
        return {'status': 'available', 'duration_ms': round((time.monotonic()-started)*1000), 'data': value}
    except Exception:
        return {'status': 'unavailable', 'duration_ms': round((time.monotonic()-started)*1000),
                'error': 'diagnostic_stage_unavailable'}


async def diagnose(sup):
    fields = {
        'system': ('/info', 'version healthy supported state disk_total disk_used disk_free'),
        'core': ('/core/info', 'version version_latest state arch machine'),
        'core_resources': ('/core/stats', 'cpu_percent memory_usage memory_limit memory_percent blk_read blk_write net_rx net_tx'),
        'supervisor': ('/supervisor/info', 'version version_latest healthy supported channel arch'),
        'supervisor_resources': ('/supervisor/stats', 'cpu_percent memory_usage memory_limit memory_percent'),
        'host': ('/host/info', 'operating_system kernel deployment disk_total disk_used disk_free boot_timestamp'),
        'host_resources': ('/host/stats', 'cpu_percent memory_usage memory_limit memory_percent disk_total disk_used disk_free'),
        'resolution': ('/resolution/info', 'unhealthy unsupported'),
    }
    jobs = {name: stage(lambda p=path: sup.request('GET', p),
                        lambda v, f=names: select(v, f.split())) for name, (path, names) in fields.items()}
    # Error and repair descriptions may contain user configuration; expose identifiers/status only.
    jobs['repairs'] = stage(lambda: websocket_query(sup, 'repairs/list_issues'),
        lambda v: {'issues': [select(i, ('domain', 'issue_id', 'severity', 'is_fixable'))
                             for i in v.get('issues', [])[:200]],
                   'total': len(v.get('issues', []))})
    jobs['integrations'] = stage(lambda: websocket_query(sup, 'config_entries/get'),
        lambda v: {'errors': [select(i, ('domain', 'state', 'disabled_by')) for i in v
                              if i.get('state') not in ('loaded', 'not_loaded')][:200],
                   'total': len(v)})
    values = await asyncio.gather(*jobs.values())
    return {'captured_at': now(), 'partial': any(v['status'] == 'unavailable' for v in values),
            'stages': dict(zip(jobs, values))}


async def permission_map(sup, options):
    async def collect():
        states, entities, devices, areas = await asyncio.gather(
            sup.request('GET', '/core/api/states'), sup.registry('entity'), sup.registry('device'), sup.registry('area'))
        by_id = {i['entity_id']: i for i in entities}
        state_by_id = {i['entity_id']: i for i in states}
        device_by_id = {i['id']: i for i in devices}
        identifiers = list(dict.fromkeys([*state_by_id, *by_id]))
        allow = options.get('allowed_entities', [])
        mapped = []
        for identifier in identifiers[:2000]:
            registered = by_id.get(identifier, {})
            state = state_by_id.get(identifier)
            device = device_by_id.get(registered.get('device_id'), {})
            mapped.append({**select(registered, ('device_id', 'area_id', 'disabled_by')),
                'entity_id': identifier,
                'effective_area_id': registered.get('area_id') or device.get('area_id'),
                'state_available': None if state is None else state.get('state') not in ('unavailable', 'unknown'),
                'state_status': 'missing' if state is None else (
                    state.get('state') if state.get('state') in ('unavailable', 'unknown') else 'available'),
                'registered': identifier in by_id, 'allowed': identifier in allow})
        return {'entities': mapped,
                'devices': [select(i, ('id', 'area_id', 'manufacturer', 'model', 'disabled_by')) for i in devices[:1000]],
                'areas': [select(i, ('area_id', 'name')) for i in areas[:200]],
                'entity_total': len(identifiers),
                'truncated': len(identifiers)>2000 or len(devices)>1000 or len(areas)>200}
    value = await stage(collect, lambda x: x)
    return {'captured_at': now(), 'map': value, 'policy': {
        'allowed_entities': options.get('allowed_entities', []), 'allowed_services': options.get('allowed_services', []),
        'writes_enabled': options.get('writes_enabled') is True,
        'empty_entity_allowlist': 'no_entities', 'empty_service_allowlist': 'no_services'},
        'physical_effects_performed': False,
        'scope': 'Jarvis configured policy; Home Assistant user permissions are not inferred'}

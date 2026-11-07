"""Pure production decisions. No HA services, device I/O or mutable inputs."""
from copy import deepcopy
import json

try:
    from .telemetry_health import finite
except ImportError:
    from telemetry_health import finite

NATIVE_RESERVE_SOC = 30


def house_profile_issues(states):
    """Native protection stays fixed even when an HA stop threshold changes."""
    issues = []
    for slot in range(1, 7):
        expected = {f'number.inverter_program_{slot}_soc': NATIVE_RESERVE_SOC,
                    f'select.inverter_program_{slot}_charging': 'Disabled'}
        for entity, value in expected.items():
            actual = states.get(entity)
            matches = finite(actual) == value if isinstance(value, int) else actual == value
            if not matches:
                issues.append(dict(entity_id=entity, expected=value, actual=actual))
        entity = f'number.inverter_program_{slot}_power'
        power = finite(states.get(entity))
        if power is None or power < 500:
            issues.append(dict(entity_id=entity, expected='>=500 W', actual=states.get(entity)))
    return issues


def choose_operation(*, block, price, soc, pv_w, house_w, now, policy, settings, states):
    def decision(mode, power, floor, code, reason):
        return dict(mode=mode, power_w=power, minimum_soc=floor, code=code, reason=reason)

    sale_floor = policy['sale_soc']
    hold = lambda code, reason: decision('hold', 0, sale_floor, code, reason)
    soc = finite(soc)
    if soc is None or not 0 <= soc <= 100:
        return hold('soc_missing', 'Chybí platný stav baterie.')
    if house_profile_issues(states):
        return hold('native_profile', 'Domácí program měniče neodpovídá pevným ochranám; nastavení se nepřepisuje.')
    if not isinstance(price, dict):
        return hold('price_missing', 'Čekám na aktuální výkupní cenu.')
    start, end, net = (finite(price.get(k)) for k in ('start', 'end', 'net'))
    if start is None or end is None or net is None or not start <= now < end:
        return hold('price_missing', 'Čekám na aktuální výkupní cenu.')
    completed = settings.get('completed_battery_plan') or {}
    block_ok = isinstance(block, dict) and not (completed.get('day') and completed.get('day') == block.get('day'))
    if block_ok:
        for key,proof in (settings.get('completed_blocks') or {}).items():
            try:identity=json.loads(key)
            except (TypeError,ValueError):continue
            if (isinstance(identity,list) and len(identity)==3 and identity[0]==block.get('day')
                    and finite(identity[1]) is not None and finite(identity[2]) is not None and identity[1]<identity[2]
                    and isinstance(proof,dict) and proof.get('reason') in ('reserve','deadline') and proof.get('sale_id')):
                block_ok=False;break
    if net > 0 and soc > sale_floor and block_ok:
        start, end = finite(block.get('start')), finite(block.get('end'))
        if start is not None and end is not None and start <= now < end - 10:
            return decision('battery', policy['max_w'], sale_floor, 'scheduled',
                            f'Prodej podle plánu · baterie nad {sale_floor:g} %.')
    pv, house = finite(pv_w), finite(house_w)
    if (net > 0 and settings.get('pv_verified') and soc >= policy['pv_soc']
            and pv is not None and house is not None and house >= 0 and pv > house + 30
            and now >= float(settings.get('cooldown_until', 0))):
        return decision('pv', policy['max_w'], sale_floor, 'surplus', 'Baterie je téměř plná · dostupné přebytky.')
    if (settings.get('bias_enabled', True)
            and soc >= policy['resume_soc']):
        return decision('bias', policy['bias_w'], policy['home_soc'], 'bias',
                        f"Malý trvalý přetok · cíl {policy['bias_w']:g} W, rezerva {policy['home_soc']:g} %.")
    return hold('waiting', 'Čekám na cenový blok, přebytky nebo podmínky malého přetoku.')


def complete_battery_plan(settings, proof, now):
    """Copy-on-write completion; retain unrelated history/settings verbatim."""
    result = dict(settings)
    block = proof.get('business_block') or settings.get('selected_block') or {}
    if (proof.get('purpose') != 'automatic' or proof.get('stop_verified') is not True
            or proof.get('conflicts') or not proof.get('id') or not block.get('day')):
        return result
    start, end = finite(proof.get('start')), finite(proof.get('end'))
    first, last = finite(block.get('start')), finite(block.get('end'))
    if any(v is None for v in (start, end, first, last)) or not first <= start < end <= last:
        return result
    done = proof.get('reason') == 'reserve' or proof.get('reason') == 'deadline' and end >= last and now >= last
    if done:
        result['completed_battery_plan'] = {**deepcopy(block), 'sale_id':proof['id'],
                                            'reason':proof['reason'], 'completed_at':now}
    return result

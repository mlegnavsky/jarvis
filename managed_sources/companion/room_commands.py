"""Exact Czech light commands, scoped to exposed lights and actual HA areas.

This is an intent handler after activation, never a wake-word model. A missing
or unknown room never falls back to another room or the entire household.
"""
import re
import unicodedata


def normalized(text):
    return ' '.join(''.join(c for c in unicodedata.normalize('NFKD', str(text).casefold())
                            if not unicodedata.combining(c)).split()).strip(' .!?')

# Known Czech locative forms, applied only to exact registered room names/aliases.
FORMS = {
    'obyvak': {'obyvaku'}, 'obyvaci pokoj': {'obyvacim pokoji'},
    'koupelna': {'koupelne'}, 'chodba': {'chodbe'},
    'vstupni chodba': {'vstupni chodbe', 'chodbicka', 'chodbicce', 'chodba', 'chodbe'}, 'chodbicka': {'chodbicce'},
    'kuchyne': {'kuchyni'}, 'loznice': {'loznici'},
    'detsky pokoj': {'detskem pokoji'}, 'jidelna': {'jidelne'},
    'technicka mistnost': {'technicke mistnosti'}, 'sklep': {'sklepe'},
    'terasa': {'terase'}, 'zahrada': {'zahrade'}, 'zachod': {'zachode'},
    'toaleta': {'toalete'},
}


def resolve(text, source_area, areas, exposed):
    match = re.fullmatch(r'(rozsvit|zhasni)(?: (?:to|svetlo|svetla))?(?: (?:v|ve) (.+))?', normalized(text))
    if not match:
        return None
    verb, explicit = match.groups()
    # Multi-action or parameterized requests belong to the normal agent.
    if explicit and re.search(r'\b(a|pak|potom|na|za|ale|az|kdyz)\b|[,;]', explicit):
        return None
    result = {'service': 'turn_on' if verb == 'rozsvit' else 'turn_off',
              'entity_ids': [], 'area_id': None, 'area_name': None, 'error': None}
    if explicit:
        candidates = []
        for area in areas:
            names = {normalized(area['name']), *(normalized(a) for a in area.get('aliases', []))}
            forms = names | {form for name in names for form in FORMS.get(name, set())}
            if explicit in forms:
                candidates.append(area)
        if len(candidates) != 1:
            result['error'] = 'room_ambiguous' if candidates else 'room_not_found'
            return result
        selected = candidates[0]
    else:
        selected = next((a for a in areas if a['id'] == source_area), None)
        if selected is None:
            result['error'] = 'source_room_missing'
            return result
    result.update(area_id=selected['id'], area_name=selected['name'])
    result['entity_ids'] = sorted({e['entity_id'] for e in exposed
        if e['entity_id'].startswith('light.') and e.get('area_id') == selected['id']})
    if not result['entity_ids']:
        result['error'] = 'no_exposed_lights'
    return result


async def execute(hass, request, context):
    errors = {
        'source_room_missing': 'Nevím, ve které místnosti je tento mikrofon. Řekni prosím název místnosti.',
        'room_not_found': 'Tuto místnost neznám. Řekni prosím její název z Home Assistantu.',
        'room_ambiguous': 'Tento název má více místností. Upřesni prosím, kterou myslíš.',
        'no_exposed_lights': 'V této místnosti nemám žádná světla povolená pro hlasové ovládání.',
    }
    if request['error']:
        return errors[request['error']]
    try:
        await hass.services.async_call('light', request['service'],
            {'entity_id': request['entity_ids']}, blocking=True, context=context)
    except Exception:
        return 'Provedení příkazu ke světlům se nepodařilo potvrdit.'
    desired = 'on' if request['service'] == 'turn_on' else 'off'
    verified = all((state := hass.states.get(entity)) is not None and state.state == desired
                   for entity in request['entity_ids'])
    if verified:
        return ('Rozsvítila' if desired == 'on' else 'Zhasla') + ' jsem světla. Místnost: ' + request['area_name'] + '.'
    return 'Povel pro světla jsem odeslala. Místnost: ' + request['area_name'] + '. Změnu stavu zatím nemám potvrzenou.'


def resolve_input(hass, user, exposed):
    # Avoid registry access at all for unrelated conversation turns.
    if not re.match(r'^(rozsvit|zhasni)(?:\s|$)', normalized(user.text)):
        return None
    from homeassistant.helpers import area_registry as ar, device_registry as dr, entity_registry as er
    areas_registry, devices, entities = ar.async_get(hass), dr.async_get(hass), er.async_get(hass)
    areas = [{'id': a.id, 'name': a.name, 'aliases': list(a.aliases)} for a in areas_registry.async_list_areas()]
    device = devices.async_get(user.device_id) if user.device_id else None
    if device is None and getattr(user, 'satellite_id', None):
        satellite = entities.async_get(user.satellite_id)
        if satellite and satellite.device_id:
            device = devices.async_get(satellite.device_id)
    targets = []
    for item in exposed:
        if not item['entity_id'].startswith('light.'):
            continue
        entity = entities.async_get(item['entity_id'])
        entity_device = devices.async_get(entity.device_id) if entity and entity.device_id else None
        area = entity.area_id if entity and entity.area_id else entity_device.area_id if entity_device else None
        targets.append({**item, 'area_id': area})
    request = resolve(user.text, device.area_id if device else None, areas, targets)
    if request is None:
        return None
    return request


async def async_handle_room_command(hass, user, exposed):
    request = resolve_input(hass, user, exposed)
    if request is None:
        return None
    return await execute(hass, request, user.context)


def native_resolution_probe(hass):
    """Inspect real source/target registries without calling any services."""
    from types import SimpleNamespace
    from homeassistant.components.homeassistant.exposed_entities import async_should_expose
    exposed = [{'entity_id': state.entity_id, 'state': state.state}
               for state in hass.states.async_all()
               if state.entity_id.startswith('light.') and async_should_expose(hass, 'conversation', state.entity_id)]
    cases = []
    for text in ('Rozsviť', 'Zhasni', 'Rozsviť v koupelně', 'Zhasni v chodbičce'):
        user = SimpleNamespace(text=text, device_id=None,
            satellite_id='assist_satellite.home_assistant_voice_0a8bde_assist_satellite')
        request = resolve_input(hass, user, exposed)
        cases.append({'text': text, **(request or {'error': 'not_handled'})})
    return {'status': 'passed' if all(c.get('entity_ids') and not c.get('error') for c in cases) else 'needs_configuration',
            'scope': 'real exposed entities and area registries; resolution only; no service calls',
            'wake_phrase': 'Hey Jarvis', 'new_acoustic_wake_models_installed': False, 'cases': cases}



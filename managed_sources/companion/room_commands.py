"""Exact Czech light commands, scoped to exposed lights and actual HA areas.

This is an intent handler after activation, never a wake-word model. A missing
or unknown room never falls back to another room or the entire household.
"""

import time


if __package__:
    from custom_components.jarvis_voice_common import normalized,parse_command
else:
    from managed_sources.voice_common import normalized,parse_command

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
    parsed=parse_command(text)
    if parsed is None:return None
    if parsed.domain=='lock':
        target='lock.vstup_zamek_vchod'
        return {'domain':'lock','service':parsed.service,
                'entity_ids':[target] if any(e['entity_id']==target for e in exposed) else [],
                'area_id':'vstup','area_name':'Hlavní vchod',
                'error':None if any(e['entity_id']==target for e in exposed) else 'lock_not_exposed'}
    explicit=parsed.room
    result={'service':parsed.service,'entity_ids':[],'area_id':None,'area_name':None,'error':None}
    if parsed.scope=='all':
        result.update(area_id='all',area_name='Celý dům',entity_ids=sorted({e['entity_id'] for e in exposed if e['entity_id'].startswith('light.')}))
        if not result['entity_ids']:result['error']='no_exposed_lights'
        return result
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


async def execute(hass, request, context, *, user=None, token=None):
    errors = {
        'source_room_missing': 'Nevím, ve které místnosti je tento mikrofon. Řekni prosím název místnosti.',
        'room_not_found': 'Tuto místnost neznám. Řekni prosím její název z Home Assistantu.',
        'room_ambiguous': 'Tento název má více místností. Upřesni prosím, kterou myslíš.',
        'no_exposed_lights': 'V této místnosti nemám žádná světla povolená pro hlasové ovládání.',
        'lock_not_exposed':'Zámek hlavního vchodu není povolený pro toto ovládání.',
    }
    if request['error']:
        return errors[request['error']]
    domain=request.get('domain','light')
    if domain=='lock' and (request['entity_ids']!=['lock.vstup_zamek_vchod'] or request['service'] not in ('lock','unlock') or request['area_id']!='vstup'):
        return 'Tento hlasový povel smí ovládat pouze zámek hlavního vchodu.'
    speaker=getattr(hass,'data',{}).get('jarvis_speaker_identity')
    voice=bool(user and (getattr(user,'device_id',None) or getattr(user,'satellite_id',None)))
    if voice and (speaker is None or not getattr(speaker,'enforce',False)):
        return 'Povel neprovedu, ověřování hlasu není dostupné.'
    if speaker and getattr(speaker,'enforce',False) and user is None:
        return 'Povel neprovedu, chybí ověřený zdroj požadavku.'
    if speaker and getattr(speaker,'enforce',False) and user and (getattr(user,'device_id',None) or getattr(user,'satellite_id',None)):
        if not speaker.gate.consume(token,speaker.device(user),user.text,(domain,request['service']),(tuple(request['entity_ids']),request['area_id'])):
            return 'Povel neprovedu, chybí platné jednorázové ověření hlasu.'
    elif domain=='lock':
        # This new lock route is only for voice-authorized local control.
        return 'Zámek vyžaduje ověřený hlasový povel.'
    try:
        await hass.services.async_call(domain, request['service'],
            {'entity_id': request['entity_ids']}, blocking=True, context=context)
    except Exception:
        return 'Provedení příkazu se nepodařilo potvrdit.'
    desired = ('locked' if request['service']=='lock' else 'unlocked') if domain=='lock' else ('on' if request['service'] == 'turn_on' else 'off')
    verified = all((state := hass.states.get(entity)) is not None and state.state == desired
                   for entity in request['entity_ids'])
    if domain=='light':
        # Device reports commonly arrive after the service response. Acceptance
        # is silent; the observation is never promoted to a spoken success claim.
        data=getattr(hass,'data',None)
        if isinstance(data,dict):
            observations=data.setdefault('jarvis_light_command_observations',[])
            observations.append({'at':time.monotonic(),'area_id':request['area_id'],
                'entity_ids':list(request['entity_ids']),'desired':desired,
                'status':'confirmed' if verified else 'accepted_pending_state'})
            del observations[:-20]
        return ''
    if verified:
        return ''
    return 'Povel jsem odeslala. Místo: ' + request['area_name'] + '. Změnu stavu zatím nemám potvrzenou.'


def resolve_input(hass, user, exposed):
    # Avoid registry access at all for unrelated conversation turns.
    if parse_command(user.text) is None:
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
        if not item['entity_id'].startswith(('light.','lock.')):
            continue
        entity = entities.async_get(item['entity_id'])
        entity_device = devices.async_get(entity.device_id) if entity and entity.device_id else None
        area = entity.area_id if entity and entity.area_id else entity_device.area_id if entity_device else None
        targets.append({**item, 'area_id': area})
    request = resolve(user.text, device.area_id if device else None, areas, targets)
    if request is None:
        return None
    return request


async def async_handle_room_command(hass, user, exposed, token=None, effective_text=None):
    if effective_text:
        from copy import copy
        user=copy(user);user.text=effective_text
    request = resolve_input(hass, user, exposed)
    if request is None:
        return None
    speaker=getattr(hass,'data',{}).get('jarvis_speaker_identity')
    if speaker and getattr(speaker,'enforce',False) and (user.device_id or getattr(user,'satellite_id',None)) and not request['error']:
        if not speaker.gate.bind(token,speaker.device(user),user.text,(request.get('domain','light'),request['service']),(tuple(request['entity_ids']),request['area_id'])):
            return 'Povel neprovedu, ověření hlasu neodpovídá cíli.'
    return await execute(hass, request, user.context,user=user,token=token)


def native_resolution_probe(hass):
    """Inspect real source/target registries without calling any services."""
    from types import SimpleNamespace
    from homeassistant.components.homeassistant.exposed_entities import async_should_expose
    exposed = [{'entity_id': state.entity_id, 'state': state.state}
               for state in hass.states.async_all()
               if state.entity_id.startswith('light.') and async_should_expose(hass, 'conversation', state.entity_id)]
    cases = []
    for text in ('Rozsviť', 'Zhasni', 'Rozsvítit světlo v obýváku.', 'Zhasnout světlo', 'Zhasni v dětském pokoji', 'Můžeš prosím zhasnout v dětském pokoji?', 'Rozsviť v koupelně', 'Zhasni v chodbičce'):
        user = SimpleNamespace(text=text, device_id=None,
            satellite_id='assist_satellite.home_assistant_voice_0a8bde_assist_satellite')
        request = resolve_input(hass, user, exposed)
        cases.append({'text': text, **(request or {'error': 'not_handled'})})
    return {'status': 'passed' if all(c.get('entity_ids') and not c.get('error') for c in cases) else 'needs_configuration',
            'scope': 'real exposed entities and area registries; resolution only; no service calls',
            'wake_phrase': 'Hey Jarvis', 'new_acoustic_wake_models_installed': False, 'cases': cases}



"""Explicit, narrow service schemas; no arbitrary HA service proxy."""
import math
import re


class APIError(Exception):
    def __init__(self, status, code):
        self.status, self.code = status, code


def validate_action(body, options):
    if options.get('writes_enabled') is not True:
        raise APIError(403, 'writes_disabled')
    if not isinstance(body, dict) or set(body) != {'entity_id', 'service', 'data'}:
        raise APIError(400, 'invalid_action')
    entity, service, data = body['entity_id'], body['service'], body['data']
    if not isinstance(entity, str) or not re.fullmatch(r'[a-z][a-z0-9_]*\.[a-z0-9_]+', entity):
        raise APIError(400, 'invalid_entity')
    if not isinstance(service, str) or not isinstance(data, dict):
        raise APIError(400, 'invalid_action')
    required_services = {'light.turn_on', 'light.turn_off'} if service == 'light.toggle' else {service}
    if entity not in options.get('allowed_entities', []) or not required_services <= set(options.get('allowed_services', [])):
        raise APIError(403, 'action_not_allowed')
    if service.split('.')[0] != entity.split('.')[0]:
        raise APIError(403, 'domain_mismatch')
    no_data = {'light.toggle', 'light.turn_off', 'switch.turn_on', 'switch.turn_off', 'automation.turn_on', 'lock.lock'}
    if service in no_data:
        valid = not data
    elif service == 'light.turn_on':
        valid = set(data) <= {'brightness'} and ('brightness' not in data or type(data['brightness']) is int and 0 <= data['brightness'] <= 255)
    elif service == 'climate.set_temperature':
        temp = data.get('temperature')
        valid = set(data) == {'temperature'} and type(temp) in (int, float) and math.isfinite(temp)
    elif service == 'climate.set_hvac_mode':
        valid = set(data) == {'hvac_mode'} and isinstance(data['hvac_mode'], str)
    else:
        raise APIError(403, 'unsupported_service')
    if not valid:
        raise APIError(400, 'invalid_service_data')
    return entity, service, data


def validate_current_state(service, data, state):
    if not isinstance(state, dict) or state.get('state') in ('unavailable', 'unknown', None):
        raise APIError(409, 'entity_unavailable')
    attrs = state.get('attributes', {})
    if service == 'climate.set_temperature':
        lower, upper = attrs.get('min_temp'), attrs.get('max_temp')
        if type(lower) not in (int, float) or type(upper) not in (int, float) or not lower <= data['temperature'] <= upper:
            raise APIError(400, 'temperature_out_of_range')
    if service == 'climate.set_hvac_mode' and data['hvac_mode'] not in attrs.get('hvac_modes', []):
        raise APIError(400, 'invalid_hvac_mode')


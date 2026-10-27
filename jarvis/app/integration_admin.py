"""Native integration options forms; no raw config-entry credentials or arbitrary URLs."""
import re
from . import diagnostics
from .policy import APIError

ENTRY_FIELDS = ('entry_id', 'domain', 'title', 'state', 'source', 'disabled_by', 'supports_options',
                'supports_unload', 'supports_remove_device', 'pref_disable_polling', 'pref_disable_new_entities')


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', value):
        raise APIError(400, 'invalid_integration_identifier')
    return value


async def entries(admin):
    from .admin import revision
    values = await diagnostics.websocket_query(admin.sup, 'config_entries/get')
    items = []
    for value in values[:500]:
        item = diagnostics.select(value, ENTRY_FIELDS)
        item['revision'] = revision(item)
        items.append(item)
    return {'items': items, 'total': len(values), 'truncated': len(values) > 500}


async def entry(admin, entry_id):
    identifier(entry_id)
    item = next((i for i in (await entries(admin))['items'] if i['entry_id'] == entry_id), None)
    if item is None:
        raise APIError(404, 'integration_not_found')
    return item


async def subentries(admin, entry_id):
    from .admin import revision
    current = await entry(admin, entry_id)
    values = await diagnostics.websocket_query(admin.sup, 'config_entries/subentries/list', {'entry_id': entry_id})
    items = []
    for value in values[:100]:
        item = diagnostics.select(value, ('subentry_id', 'subentry_type', 'title'))
        item['revision'] = revision([current, item])
        items.append(item)
    return {'items': items, 'total': len(values), 'truncated': len(values) > 100}


def public_form(value):
    from .admin import revision, redact
    # Context/data/result and supplied credentials are never exposed.
    form = diagnostics.select(value, ('type', 'flow_id', 'step_id', 'handler', 'errors', 'reason', 'menu_options'))
    def without_defaults(item):
        if isinstance(item, dict):
            return {k: without_defaults(v) for k, v in item.items() if k not in ('default', 'suggested_value')}
        if isinstance(item, list):
            return [without_defaults(v) for v in item]
        return item
    # Nested expandable/selector schemas can also hold private defaults.
    form['data_schema'] = without_defaults(value.get('data_schema', []))
    form = redact(form)
    form['revision'] = revision(value)
    return form


async def get_form(admin, flow_id):
    identifier(flow_id)
    with admin.db() as db:
        row = db.execute('SELECT entry_id,closed,kind FROM integration_flows WHERE flow_id=?', (flow_id,)).fetchone()
    if not row or row[1]:
        raise APIError(404, 'integration_flow_not_owned_or_closed')
    kind = 'subentries' if row[2] == 'subentries' else 'options'
    return await admin.sup.request('GET', '/core/api/config/config_entries/'+kind+'/flow/'+flow_id)


async def change(admin, key, operation, args):
    from .admin import revision
    if operation in ('integration_reload', 'integration_options_start', 'integration_subentry_options_start'):
        current = await entry(admin, args['entry_id'])
        subentry = None
        if operation == 'integration_subentry_options_start':
            subentry = next((s for s in (await subentries(admin, args['entry_id']))['items'] if s['subentry_id'] == args['subentry_id']), None)
            if subentry is None:
                raise APIError(404, 'integration_subentry_not_found')
        if (subentry or current)['revision'] != args['expected_revision']:
            raise APIError(409, 'integration_revision_changed')
        admin.remember(key, current)
        if operation == 'integration_options_start' and not current.get('supports_options'):
            raise APIError(409, 'integration_options_not_supported')
        # A native flow can finish during its first step; back up before starting it.
        await admin.backup(key)
        if operation == 'integration_reload':
            response = await admin.sup.request('POST', '/core/api/config/config_entries/entry/'+args['entry_id']+'/reload', {})
            after = await entry(admin, args['entry_id'])
            return {'verified': after.get('state') == 'loaded' and response.get('require_restart') is False,
                    'integration': after, 'require_restart': response.get('require_restart')}
        kind = 'subentries' if subentry else 'options'
        body = {'handler': [args['entry_id'], subentry['subentry_type']], 'subentry_id': args['subentry_id']} if subentry else {'handler': args['entry_id']}
        value = await admin.sup.request('POST', '/core/api/config/config_entries/'+kind+'/flow', {**body, 'show_advanced_options': True})
        flow_id = value.get('flow_id')
        if flow_id:
            identifier(flow_id)
            with admin.db() as db:
                db.execute('INSERT INTO integration_flows (flow_id,entry_id,closed,kind) VALUES (?,?,?,?)', (flow_id, args['entry_id'], 0, kind))
    else:
        current = await get_form(admin, args['flow_id'])
        if revision(current) != args['expected_revision']:
            raise APIError(409, 'integration_form_changed')
        if current.get('type') not in ('form', 'menu'):
            raise APIError(409, 'integration_step_not_interactive')
        allowed = {f['name'] for f in current.get('data_schema', [])}
        if current['type'] == 'menu':
            allowed = {'next_step_id'}
        if set(args['user_input']) - allowed:
            raise APIError(400, 'integration_input_not_in_form')
        admin.remember(key, {'form': public_form(current)})
        with admin.db() as db:
            kind = db.execute('SELECT kind FROM integration_flows WHERE flow_id=?', (args['flow_id'],)).fetchone()[0]
        kind = 'subentries' if kind == 'subentries' else 'options'
        value = await admin.sup.request('POST', '/core/api/config/config_entries/'+kind+'/flow/'+args['flow_id'], args['user_input'])
        if value.get('type') in ('create_entry', 'abort'):
            with admin.db() as db:
                db.execute('UPDATE integration_flows SET closed=1 WHERE flow_id=?', (args['flow_id'],))
    kind = value.get('type')
    return {'verified': kind in ('form', 'menu', 'create_entry'), 'form': public_form(value),
            'configuration_saved': kind == 'create_entry', 'settings_readback_verified': False,
            'interaction_required': kind in ('form', 'menu', 'external', 'external_done', 'progress')}

"""Journaled workspace operations, staged uploads and local app rebuilds."""
import base64
import hashlib
import json
import re
import yaml
from .policy import APIError
from .ha import UpstreamError
from .workspace_files import ASSETS
from pathlib import PurePosixPath

FIELDS = {
    'workspace_write': {'workspace', 'path', 'content', 'expected_revision'},
    'workspace_delete': {'workspace', 'path', 'expected_revision'},
    'workspace_move': {'workspace', 'path', 'destination', 'expected_revision', 'destination_revision'},
    'workspace_restore': {'backup_id', 'expected_revision'},
    'workspace_move_restore': {'backup_id', 'expected_revision', 'destination_revision'},
    'upload_begin': {'upload_id', 'workspace', 'path', 'expected_revision', 'size', 'sha256'},
    'upload_chunk': {'upload_id', 'offset', 'data_base64'},
    'upload_finish': {'upload_id'}, 'upload_abort': {'upload_id'},
    'local_addon_rebuild': {'slug', 'project', 'expected_version', 'expected_revision'},
}


def workspace(admin, name):
    if not isinstance(name, str) or name not in admin.workspaces:
        raise APIError(400, 'unknown_workspace')
    return admin.workspaces[name]


def snapshot(files, path):
    data, mode = files.raw(path)
    return {'path': path, 'data_base64': None if data is None else base64.b64encode(data).decode(),
            'mode': mode, 'revision': 'missing' if data is None else hashlib.sha256(data).hexdigest()}


def project(admin, name):
    from .admin import revision
    if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9_-]+(?:/[A-Za-z0-9_-]+)?', name):
        raise APIError(400, 'invalid_source_project')
    files = workspace(admin, 'addons')
    manifest = files.read(name+'/config.yaml')
    if manifest['content'] is None:
        manifest = files.read(name+'/config.json')
    if manifest['content'] is None:
        raise APIError(404, 'source_manifest_not_found')
    config = yaml.safe_load(manifest['content'])
    inventory = files.inventory()
    if inventory['truncated']:
        raise APIError(409, 'source_inventory_truncated')
    entries = []
    for item in sorted(inventory['items'], key=lambda x: x['path']):
        if item['path'].startswith(name+'/'):
            data, mode = files.raw(item['path'])
            entries.append({'path': item['path'], 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data), 'mode': mode})
    return {'project': name, 'slug': config.get('slug'), 'version': str(config.get('version')), 'files': entries,
            'revision': revision(entries), 'scope': 'managed_source_files_only'}


def validate(admin, operation, args):
    if 'workspace' in args:
        files = workspace(admin, args['workspace'])
        files.parts(args['path'])
        if 'destination' in args:
            files.parts(args['destination'])
            if args['destination'] == args['path']:
                raise APIError(400, 'same_workspace_path')
        if operation == 'workspace_write':
            if not isinstance(args['content'], str):
                raise APIError(400, 'invalid_workspace_content')
            files.validate(args['path'], args['content'])
        if operation == 'upload_begin' and (args['workspace'] == 'addons' or PurePosixPath(args['path']).suffix.lower() not in ASSETS):
            raise APIError(403, 'upload_target_not_allowed')
    if 'upload_id' in args:
        admin.uploads.paths(args['upload_id'])
    if 'destination_revision' in args and not re.fullmatch(r'missing|[a-f0-9]{64}', str(args['destination_revision'])):
        raise APIError(400, 'invalid_destination_revision')


async def perform(admin, key, operation, args):
    if operation == 'upload_begin':
        return admin.uploads.begin(args)
    if operation == 'upload_chunk':
        return admin.uploads.chunk(args['upload_id'], args['offset'], args['data_base64'])
    if operation == 'upload_abort':
        for path in admin.uploads.paths(args['upload_id']):
            path.unlink(missing_ok=True)
        return {'verified': True}
    if operation == 'local_addon_rebuild':
        return await rebuild(admin, key, args)
    if operation in ('workspace_restore', 'workspace_move_restore'):
        with admin.db() as db:
            row = db.execute('SELECT before_data FROM jobs WHERE key=?', (args['backup_id'],)).fetchone()
        saved = json.loads(row[0]) if row and row[0] else {}
        if 'workspace' not in saved or 'file' not in saved or ('destination' in saved) != (operation == 'workspace_move_restore'):
            raise APIError(404, 'workspace_single_file_backup_not_found')
        files = workspace(admin, saved['workspace'])
        before = saved['file']
        if operation == 'workspace_move_restore':
            destination = saved['destination']
            current_source = snapshot(files, before['path'])
            current_destination = snapshot(files, destination['path'])
            if current_source['revision'] != args['expected_revision'] or current_destination['revision'] != args['destination_revision']:
                raise APIError(409, 'workspace_revision_conflict')
            admin.remember(key, {'workspace': saved['workspace'], 'file': current_source, 'destination': current_destination})
            first = files.write_raw(before['path'], None if before['data_base64'] is None else base64.b64decode(before['data_base64'], validate=True), args['expected_revision'], before['mode'])
            try:
                second = files.write_raw(destination['path'], None if destination['data_base64'] is None else base64.b64decode(destination['data_base64'], validate=True), args['destination_revision'], destination['mode'])
            except APIError:
                raise UpstreamError('workspace_restore_partial_do_not_replay') from None
            return {'verified': first['verified'] and second['verified'], 'source': first, 'destination': second}
        admin.remember(key, {'workspace': saved['workspace'], 'file': snapshot(files, before['path'])})
        data = None if before['data_base64'] is None else base64.b64decode(before['data_base64'], validate=True)
        return files.write_raw(before['path'], data, args['expected_revision'], before['mode'])
    if operation == 'upload_finish':
        meta, _ = admin.uploads.info(args['upload_id'])
        files = workspace(admin, meta['workspace'])
        admin.remember(key, {'workspace': meta['workspace'], 'file': snapshot(files, meta['path'])})
        return admin.uploads.finish(args['upload_id'], files)
    files = workspace(admin, args['workspace'])
    before = snapshot(files, args['path'])
    if before['revision'] != args['expected_revision']:
        raise APIError(409, 'workspace_revision_conflict')
    saved = {'workspace': args['workspace'], 'file': before}
    if operation == 'workspace_move':
        destination = snapshot(files, args['destination'])
        if destination['revision'] != args['destination_revision'] or before['data_base64'] is None:
            raise APIError(409, 'workspace_move_conflict')
        saved['destination'] = destination
        admin.remember(key, saved)
        data = base64.b64decode(before['data_base64'], validate=True)
        if PurePosixPath(args['destination']).suffix.lower() not in ASSETS:
            try:
                files.validate(args['destination'], data.decode('utf-8'))
            except UnicodeError:
                raise APIError(400, 'workspace_text_not_utf8') from None
        target = files.write_raw(args['destination'], data, args['destination_revision'], before['mode'])
        try:
            removed = files.write_raw(args['path'], None, args['expected_revision'])
        except APIError:
            raise UpstreamError('workspace_move_partial_do_not_replay') from None
        return {'verified': target['verified'] and removed['verified'], 'destination': target, 'source': removed, 'backup_id': key}
    admin.remember(key, saved)
    result = files.write(args['path'], args.get('content'), args['expected_revision'])
    return {**result, 'backup_id': key, 'activation_performed': False}


async def rebuild(admin, key, args):
    own = (await admin.sup.request('GET', '/addons/self/info'))['slug']
    if args['slug'] in (own, own.rsplit('_jarvis', 1)[0]+'_jarvis_updater'):
        raise APIError(409, 'use_independent_updater_for_self')
    before = project(admin, args['project'])
    if before['revision'] != args['expected_revision'] or args['slug'] != 'local_'+str(before['slug']) or before['version'] != args['expected_version']:
        raise APIError(409, 'local_source_or_version_changed')
    info = await admin.sup.request('GET', '/addons/'+args['slug']+'/info')
    if info.get('repository') != 'local' or info.get('version') != args['expected_version']:
        raise APIError(409, 'rebuild_requires_matching_installed_local_addon')
    if re.search(r'jarvis_updater|cloudflar|tunnel|tailscale|wireguard|zerotier|nginx|proxy', args['slug']+' '+str(info.get('name', '')), re.I):
        raise APIError(409, 'connectivity_rebuild_protected')
    admin.remember(key, {'source': before, 'addon': info})
    await admin.backup(key, args['slug'])
    if project(admin, args['project'])['revision'] != args['expected_revision']:
        raise APIError(409, 'local_source_changed_during_backup')
    await admin.sup.request('POST', '/addons/'+args['slug']+'/rebuild', {})
    after = await admin.sup.request('GET', '/addons/'+args['slug']+'/info')
    return {'verified': after.get('version') == args['expected_version'] and after.get('state') == info.get('state'),
            'version': after.get('version'), 'state': after.get('state'), 'source_revision': args['expected_revision'],
            'application_functionality_verified': False}

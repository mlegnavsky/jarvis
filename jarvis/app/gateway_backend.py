"""Internal gateway contract and a surviving, durable port-handover rollback."""
import asyncio
import base64
import json
import os
import re
import time
from pathlib import Path

import aiohttp
from aiohttp import web
from .policy import APIError
from .ha import UpstreamError
from .oauth import ALL_SCOPES
from .mcp import catalog, validate, BRIDGE_SERVICES, GATEWAY_INVOKE, MCP_OAUTH


def persist(path, value):
    temporary = path.with_suffix('.tmp')
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w') as stream:
        json.dump(value, stream)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


class MigrationWatchdog:
    def __init__(self, ha, options, directory, audit):
        self.ha, self.options, self.audit = ha, options, audit
        self.path = Path(directory)/'gateway-migration.pause'
        self.task = None
        self.lock = asyncio.Lock()
        self.heartbeat = None

    def marker(self):
        return json.loads(self.path.read_text()) if self.path.exists() else None

    def status(self):
        value = self.marker() or {}
        return {'armed': value.get('phase') == 'armed' and self.task is not None and not self.task.done(),
                'phase': value.get('phase', 'inactive'), 'deadline': value.get('deadline'), 'heartbeat': self.heartbeat}

    async def snapshot(self, oauth):
        if self.options.get('maintenance_enabled') is not True:
            raise APIError(403, 'maintenance_disabled')
        own = await self.ha.request('GET', '/addons/self/info')
        match = re.fullmatch(r'([a-z0-9]+)_jarvis', own.get('slug', ''))
        if not match:
            raise APIError(409, 'unexpected_app_identity')
        sibling = match[1]+'_jarvis_updater'
        updater = await self.ha.request('GET', '/addons/'+sibling+'/info')
        async with self.lock:
            marker = self.marker()
            if marker and marker.get('phase') == 'active':
                raise APIError(409, 'gateway_authority_already_committed')
            async with oauth.mutation_lock:
                if not marker:
                    marker = {'phase': 'armed', 'deadline': time.time()+180, 'main': own['slug'], 'updater': sibling,
                              'main_network': own.get('network', {'8099/tcp': 8099}),
                              'updater_network': updater.get('network', {'8100/tcp': None})}
                    persist(self.path, marker)
                if marker.get('phase') != 'armed':
                    raise APIError(409, 'gateway_handover_not_armed')
                with oauth.db() as connection:
                    raw = connection.serialize()
                if len(raw) > 32*1024*1024:
                    raise APIError(503, 'oauth_snapshot_too_large')
                self.audit.write('gateway_migration', 'snapshot')
                return {'oauth_database': base64.b64encode(raw).decode(), 'watchdog_deadline': marker['deadline']}

    async def commit(self):
        async with self.lock:
            marker = self.marker()
            if not marker or marker.get('phase') not in ('armed', 'active'):
                raise APIError(409, 'gateway_handover_not_armed')
            marker['phase'] = 'active'
            persist(self.path, marker)
            self.audit.write('gateway_migration', 'authority_committed')
        return {'committed': True}

    async def unpause(self):
        async with self.lock:
            marker = self.marker()
            if marker and marker.get('phase') == 'active':
                raise APIError(409, 'gateway_authority_already_committed')
            self.path.unlink(missing_ok=True)
            self.audit.write('gateway_migration', 'unpaused')
        return {'unpaused': True}

    async def updater_status(self, marker):
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=3)) as session:
            async with session.get('http://'+marker['updater'].replace('_', '-')+':8100/v1/gateway/status',
                    headers={'Authorization': 'Bearer '+self.options.get('maintenance_token', '')}, allow_redirects=False) as response:
                if response.status != 200:
                    raise UpstreamError('gateway_status_unavailable')
                return await response.json()

    async def tick(self):
        self.heartbeat = time.time()
        marker = self.marker()
        if marker and marker.get('phase') == 'rollback_ready':
            # A lost/rejected restart request must not leave an unpublished
            # old process waiting forever; startup clears this obligation.
            await self.ha.request('POST', '/addons/'+marker['main']+'/restart', {})
            return
        if not marker or marker.get('phase') not in ('armed', 'rolling_back') or time.time() < marker['deadline']:
            return
        try:
            remote = await self.updater_status(marker)
        except (aiohttp.ClientError, TimeoutError, ValueError, UpstreamError):
            remote = None
        async with self.lock:
            # The authority commit and rollback cannot cross an await race.
            marker = self.marker()
            if not marker or marker.get('phase') not in ('armed', 'rolling_back'):
                return
            if remote and remote.get('phase') == 'active':
                marker['phase'] = 'active'
                persist(self.path, marker)
                return
            if (marker.get('phase') == 'armed' and remote
                    and remote.get('phase') in ('commit_pending', 'rollback_release')
                    and time.time() < marker['deadline'] + 30):
                return
            marker['phase'] = 'rolling_back'
            persist(self.path, marker)
            self.audit.write('gateway_migration', 'watchdog_rollback')
            # Stop the current port owner before restoring the old owner. This
            # executor lives in Jarvis, so it survives a broken Updater startup.
            await self.ha.request('POST', '/addons/'+marker['updater']+'/stop', {})
            await self.ha.request('POST', '/addons/'+marker['updater']+'/options', {'network': marker['updater_network']})
            await self.ha.request('POST', '/addons/'+marker['main']+'/options', {'network': marker['main_network']})
            marker['phase'] = 'rollback_ready'
            persist(self.path, marker)
            try:
                await self.ha.request('POST', '/addons/'+marker['updater']+'/start', {})
            except Exception:
                # The original public route must not depend on a broken gateway
                # image starting successfully: that is why this executor survives.
                self.audit.write('gateway_migration', 'updater_start_deferred')
            await self.ha.request('POST', '/addons/'+marker['main']+'/restart', {})

    async def start(self):
        marker = self.marker()
        if marker and marker.get('phase') == 'rollback_ready':
            # Supervisor has started this container with the restored mapping.
            self.path.unlink(missing_ok=True)
        async def loop():
            while True:
                try:
                    await self.tick()
                except (aiohttp.ClientError, UpstreamError, APIError, OSError, ValueError, TimeoutError):
                    self.audit.write('gateway_migration', 'watchdog_retry_required')
                await asyncio.sleep(2)
        self.task = asyncio.create_task(loop())

    async def close(self):
        if self.task:
            self.task.cancel()
            await asyncio.gather(self.task, return_exceptions=True)


def install_backend(app, ha, options, directory, audit):
    watchdog = MigrationWatchdog(ha, options, directory, audit)
    oauth = app[MCP_OAUTH]

    async def definitions(request):
        oauth.ready()
        return web.json_response({'tools': catalog(options)})

    async def invoke(request):
        oauth.ready()
        body = await request.json()
        if (not isinstance(body, dict) or set(body) != {'name', 'arguments', 'scopes'}
                or not isinstance(body['scopes'], list) or not all(isinstance(s, str) for s in body['scopes'])
                or not set(body['scopes']) <= ALL_SCOPES):
            raise APIError(400, 'invalid_gateway_invocation')
        definition = next((t for t in catalog(options) if t['name'] == body['name']), None)
        args = body['arguments']
        if not definition or not validate(args, definition['inputSchema']):
            raise APIError(400, 'invalid_gateway_arguments')
        scope = definition['securitySchemes'][0]['scopes'][0]
        required = {scope}
        if body['name'] == 'jarvis_action' and args.get('service', '').startswith(('jarvis.', 'jarvis_voice_diagnostics.')):
            required.add('jarvis:maintain')
        if not required <= set(body['scopes']) or not set(body['scopes']) <= oauth.scopes():
            raise APIError(403, 'insufficient_scope')
        return web.json_response(await app[GATEWAY_INVOKE](body['name'], args))

    async def bootstrap(request):
        oauth.ready()
        return web.json_response(await watchdog.snapshot(oauth))

    async def commit(request):
        return web.json_response(await watchdog.commit())

    async def unpause(request):
        return web.json_response(await watchdog.unpause())

    async def status(request):
        return web.json_response(watchdog.status())

    app.router.add_get('/v1/gateway/catalog', definitions)
    app.router.add_post('/v1/gateway/invoke', invoke)
    app.router.add_post('/v1/gateway/bootstrap', bootstrap)
    app.router.add_post('/v1/gateway/commit', commit)
    app.router.add_post('/v1/gateway/unpause', unpause)
    app.router.add_get('/v1/gateway/watchdog', status)
    async def lifecycle(application):
        await watchdog.start()
        yield
        await watchdog.close()
    app.cleanup_ctx.append(lifecycle)
    return watchdog

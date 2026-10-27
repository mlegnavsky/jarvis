"""Supervisor-only sibling updater; never accepts an arbitrary update target."""
import asyncio
import contextlib
import hmac
import json
import os
import re
import secrets
import logging
import uuid
from pathlib import Path

import aiohttp
from aiohttp import web


try:
    from .gateway.policy import APIError
    from .gateway import Gateway
except ImportError:  # Add-on entrypoint runs as a script.
    from gateway.policy import APIError
    from gateway import Gateway


class Supervisor:
    def __init__(self, token, base='http://supervisor'):
        self.token, self.base, self.session = token, base, None

    async def request(self, method, path, body=None):
        if self.session is None:
            self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=1200))
        try:
            async with self.session.request(method, self.base + path, json=body,
                    headers={'Authorization': 'Bearer ' + self.token}, allow_redirects=False) as response:
                value = await response.json()
                if response.status != 200 or value.get('result') != 'ok':
                    raise APIError(502, 'supervisor_unavailable')
                return value['data']
        except (aiohttp.ClientError, TimeoutError, ValueError, KeyError):
            raise APIError(502, 'supervisor_unavailable') from None

    async def close(self):
        if self.session:
            await self.session.close()


class Maintenance:
    def __init__(self, supervisor, directory, health, attempts=60, interval=5):
        self.sup, self.health = supervisor, health
        self.attempts, self.interval = attempts, interval
        directory.mkdir(parents=True, exist_ok=True)
        self.path = directory / 'jobs.json'
        self.jobs = json.loads(self.path.read_text()) if self.path.exists() else {}
        self.lock, self.tasks = asyncio.Lock(), set()

    def save(self):
        temporary = self.path.with_suffix('.tmp')
        with open(temporary, 'w', encoding='utf-8') as file:
            os.chmod(temporary, 0o600)
            json.dump(self.jobs, file)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary, self.path)
        descriptor = os.open(self.path.parent, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)

    def launch(self, coroutine):
        task = asyncio.create_task(coroutine)
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)

    def get_job(self, identifier):
        if identifier not in self.jobs:
            raise APIError(404, 'job_not_found')
        return dict(self.jobs[identifier])

    async def target(self):
        info = await self.sup.request('GET', '/addons/self/info')
        match = re.fullmatch(r'([a-z0-9]+)_jarvis_updater', info.get('slug', ''))
        if not match:
            raise APIError(409, 'unexpected_updater_identity')
        return match[1] + '_jarvis'

    async def check(self):
        target = await self.target()
        await self.sup.request('POST', '/store/reload', {})
        info = await self.sup.request('GET', '/addons/' + target + '/info')
        return {'target': target, 'version': info['version'], 'version_latest': info['version_latest']}

    async def start(self, body, key):
        if not isinstance(body, dict) or set(body) != {'version'} or not isinstance(body['version'], str):
            raise APIError(400, 'invalid_update')
        if not isinstance(key, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', key):
            raise APIError(400, 'idempotency_key_required')
        async with self.lock:
            for job in self.jobs.values():
                if job['key'] == key:
                    if job['version'] != body['version']:
                        raise APIError(409, 'idempotency_conflict')
                    return dict(job)
            if any(j['state'] not in ('verified', 'failed') for j in self.jobs.values()):
                raise APIError(409, 'update_in_progress')
            if len(self.jobs) >= 100:
                raise APIError(503, 'journal_full')
            offered = await self.check()
            if body['version'] != offered['version_latest'] or body['version'] == offered['version']:
                raise APIError(409, 'offered_version_mismatch')
            job = {'id': uuid.uuid4().hex, 'key': key, 'version': body['version'],
                   'target': offered['target'], 'state': 'queued', 'backup_slug': None, 'error': None}
            self.jobs[job['id']] = job
            self.save()
            self.launch(self.run(job))
            return dict(job)

    async def verify(self, job):
        job['state'] = 'verifying'
        self.save()
        for _ in range(self.attempts):
            try:
                info = await self.sup.request('GET', '/addons/' + job['target'] + '/info')
                if info.get('version') == job['version'] and info.get('state') == 'started' and await self.health(job['target'], job['version']):
                    job['state'] = 'verified'
                    self.save()
                    return
            except APIError:
                pass
            await asyncio.sleep(self.interval)
        job.update(state='failed', error='post_update_verification_failed')
        self.save()

    async def run(self, job):
        try:
            job['state'] = 'backing_up'
            self.save()
            backup = await self.sup.request('POST', '/backups/new/partial', {
                'name': 'Jarvis before ' + job['version'], 'addons': [job['target']],
                'homeassistant': False, 'background': False})
            if not isinstance(backup.get('slug'), str) or not backup['slug']:
                raise APIError(502, 'backup_not_confirmed')
            job['backup_slug'] = backup['slug']
            self.save()
            info = await self.sup.request('GET', '/addons/' + job['target'] + '/info')
            if info.get('version_latest') != job['version']:
                raise APIError(409, 'offered_version_changed')
            job['state'] = 'updating'
            self.save()
            try:
                await self.sup.request('POST', '/store/addons/' + job['target'] + '/update', {})
            except APIError:
                pass  # A timeout can mean the update succeeded. Verify; never repeat it.
            await self.verify(job)
        except APIError as error:
            job.update(state='failed', error=error.code)
            self.save()

    async def recover(self):
        target = await self.target()
        for job in self.jobs.values():
            if job['state'] in ('verified', 'failed'):
                continue
            if job['target'] != target:
                job.update(state='failed', error='unexpected_target')
            elif job['state'] in ('updating', 'verifying'):
                self.launch(self.verify(job))
            else:
                job.update(state='failed', error='interrupted_before_update')
        self.save()

    async def close(self):
        tasks = list(self.tasks)
        for task in tasks:
            task.cancel()
        for task in tasks:
            with contextlib.suppress(asyncio.CancelledError):
                await task


async def auto_pair(supervisor, directory, options):
    """Opt-in setup of this repository's sibling, without exposing credentials."""
    if options.get('auto_pairing') is not True:
        return
    if options.get('updates_enabled') is not True:
        raise APIError(403, 'pairing_permission_required')
    if options.get('api_token') or options.get('jarvis_api_token'):
        raise APIError(409, 'pairing_manual_tokens_present')
    own = await supervisor.request('GET', '/addons/self/info')
    match = re.fullmatch(r'([a-z0-9]+)_jarvis_updater', own.get('slug', ''))
    if not match:
        raise APIError(409, 'unexpected_updater_identity')
    target = match[1] + '_jarvis'
    info = await supervisor.request('GET', '/addons/' + target + '/info')
    current = info.get('options')
    if not isinstance(current, dict) or not isinstance(current.get('api_token'), str) or len(current['api_token']) < 32:
        raise APIError(503, 'pairing_jarvis_not_configured')
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / 'pairing.json'

    def persist(value):
        temporary = path.with_suffix('.tmp')
        with open(temporary, 'w', encoding='utf-8') as file:
            os.chmod(temporary, 0o600)
            json.dump(value, file)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary, path)
        descriptor = os.open(directory, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)

    if path.exists():
        try:
            pairing = json.loads(path.read_text())
        except (OSError, ValueError):
            raise APIError(503, 'pairing_storage_invalid') from None
        if (not isinstance(pairing, dict) or pairing.get('target') != target
                or not isinstance(pairing.get('token'), str) or len(pairing['token']) < 32):
            raise APIError(503, 'pairing_storage_invalid')
        os.chmod(path, 0o600)
    else:
        if current.get('maintenance_token'):
            raise APIError(409, 'pairing_existing_credentials')
        pairing = {'target': target, 'token': secrets.token_urlsafe(48), 'activated': False}
        persist(pairing)
    token = pairing['token']
    grant_started = pairing.get('grant_started') is True or pairing.get('activated') is True
    if grant_started and current.get('maintenance_token') != token:
        raise APIError(403, 'pairing_credentials_changed')
    if current.get('maintenance_token') not in ('', None, token):
        raise APIError(409, 'pairing_existing_credentials')
    if grant_started and current.get('maintenance_enabled') is not True:
        raise APIError(403, 'pairing_permission_revoked')
    changed = current.get('maintenance_token') != token or current.get('maintenance_enabled') is not True
    if changed:
        backup = await supervisor.request('POST', '/backups/new/partial', {
            'name': 'Jarvis before automatic pairing', 'addons': [target],
            'homeassistant': False, 'background': False})
        if not isinstance(backup.get('slug'), str) or not backup['slug']:
            raise APIError(502, 'backup_not_confirmed')
        # Re-read after backup: never overwrite concurrent changes with stale options.
        latest = await supervisor.request('GET', '/addons/' + target + '/info')
        if latest.get('options') != current:
            raise APIError(409, 'pairing_options_changed')
        # Record authorization history before the side effect, including timeouts.
        # An interrupted first write must fail closed rather than restore revocation.
        pairing['grant_started'] = True
        persist(pairing)
        await supervisor.request('POST', '/addons/' + target + '/options', {
            'options': {**current, 'maintenance_enabled': True, 'maintenance_token': token}})
        confirmed = await supervisor.request('GET', '/addons/' + target + '/info')
        actual = confirmed.get('options', {})
        if actual.get('maintenance_token') != token or actual.get('maintenance_enabled') is not True:
            raise APIError(502, 'pairing_options_not_confirmed')
    if changed or pairing.get('activated') is not True:
        await supervisor.request('POST', '/addons/' + target + '/restart', {})
        pairing['activated'] = True
        persist(pairing)
    # Runtime-only credentials: never put them in a response or log.
    options['api_token'] = token
    options['jarvis_api_token'] = current['api_token']


def create_updater(worker, options, gateway=None):
    @web.middleware
    async def guard(request, handler):
        try:
            if gateway and (request.path == '/mcp' or request.path.startswith('/oauth/') or request.path.startswith('/.well-known/oauth-')):
                return await handler(request)
            token = options.get('api_token', '')
            if not isinstance(token, str) or len(token) < 32:
                raise APIError(503, 'setup_required')
            if not hmac.compare_digest(request.headers.get('Authorization', '').encode(), ('Bearer ' + token).encode()):
                raise APIError(401, 'unauthorized')
            if request.headers.get('Origin'):
                raise APIError(403, 'browser_origin_forbidden')
            return await handler(request)
        except APIError as error:
            return web.json_response({'error': error.code}, status=error.status, headers={'Cache-Control': 'no-store'})
        except (ValueError, UnicodeError):
            return web.json_response({'error': 'invalid_json'}, status=400)
    app = web.Application(middlewares=[guard], client_max_size=512*1024)
    async def check(request):
        return web.json_response(await worker.check())
    async def job(request):
        return web.json_response(worker.get_job(request.match_info['id']))
    async def update(request):
        if options.get('updates_enabled') is not True:
            raise APIError(403, 'updates_disabled')
        return web.json_response(await worker.start(await request.json(), request.headers.get('Idempotency-Key')), status=202)
    app.router.add_get('/v1/check', check)
    app.router.add_get('/v1/jobs/{id}', job)
    app.router.add_post('/v1/update', update)
    if gateway:
        async def activate(request):
            return web.json_response(await gateway.activate(request.headers.get('Idempotency-Key')), status=202)
        async def gateway_status(request):
            gateway.enabled()
            return web.json_response(gateway.status())
        async def rescue(request):
            return web.json_response(await gateway.rescue(await request.json()), status=202)
        app.router.add_post('/v1/gateway/activate', activate)
        app.router.add_get('/v1/gateway/status', gateway_status)
        app.router.add_post('/v1/rescue', rescue)
        gateway.install(app)
    return app


async def main_app():
    directory = Path('/data')
    options = json.loads((directory / 'options.json').read_text())
    supervisor = Supervisor(os.environ['SUPERVISOR_TOKEN'])
    try:
        await auto_pair(supervisor, directory, options)
    except APIError as error:
        logging.error('Automatic pairing unavailable: %s', error.code)
    async def health(slug, version):
        token = options.get('jarvis_api_token', '')
        if len(token) < 32:
            return False
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                async with session.get('http://' + slug.replace('_', '-') + ':8099/v1/health',
                        headers={'Authorization': 'Bearer ' + token}, allow_redirects=False) as response:
                    value = await response.json()
                    return response.status == 200 and value.get('version') == version and value.get('stream_connected') is True
        except (aiohttp.ClientError, TimeoutError, ValueError):
            return False
    worker = Maintenance(supervisor, directory, health)
    gateway = Gateway(worker, options, directory)
    if gateway.state['phase'] == 'inactive':
        try:
            await gateway.prepare()
        except Exception:
            logging.error('Gateway preparation unavailable')
    app = create_updater(worker, options, gateway)
    async def lifecycle(application):
        await worker.recover()
        await gateway.recover()
        yield
        await gateway.close()
        await worker.close()
        await supervisor.close()
    app.cleanup_ctx.append(lifecycle)
    return app


if __name__ == '__main__':
    web.run_app(main_app(), host='0.0.0.0', port=8100, access_log=None, print=None)


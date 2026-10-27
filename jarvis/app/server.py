"""Authenticated REST interface. Does not imply a ChatGPT connector is installed."""
import asyncio
import hmac
import json
import os
from pathlib import Path
from aiohttp import web
from . import VERSION
from .actions import Actions
from .audit import Audit
from .ha import HAClient, UpstreamError
from .policy import APIError
from .maintenance import MaintenanceBridge
from .mcp import install_mcp
from .management import Management
from .admin import Admin


def create_app(ha, options, directory, watch=True):
    options = dict(options)
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    audit = Audit(directory)
    actions = Actions(ha, options, directory, audit)
    token = options.get('api_token', '')

    @web.middleware
    async def boundary(request, handler):
        try:
            if request.path != '/healthz' and request.path != '/mcp' and not request.path.startswith(('/oauth/', '/.well-known/oauth-')):
                if not isinstance(token, str) or len(token) < 32:
                    raise APIError(503, 'setup_required')
                supplied = request.headers.get('Authorization', '')
                if not hmac.compare_digest(supplied.encode(), ('Bearer '+token).encode()):
                    raise APIError(401, 'unauthorized')
                if request.headers.get('Origin'):
                    raise APIError(403, 'browser_origin_not_allowed')
            response = await handler(request)
        except APIError as exc:
            response = web.json_response({'error': exc.code}, status=exc.status)
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
            response = web.json_response({'error': 'invalid_json'}, status=400)
        except UpstreamError:
            response = web.json_response({'error': 'upstream_unavailable'}, status=502)
        except web.HTTPException as exc:
            response = web.json_response({'error': 'http_' + str(exc.status)}, status=exc.status)
        response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        return response

    app = web.Application(middlewares=[boundary], client_max_size=512*1024)

    async def alive(request):
        return web.json_response({'status': 'alive'})

    async def health(request):
        return web.json_response({'version': VERSION, 'stream_connected': ha.stream_connected,
                                  'writes_enabled': options.get('writes_enabled') is True})

    async def snapshot(request):
        result = await ha.snapshot()
        return web.json_response(result, status=200 if result['connected'] else 503)

    async def action(request):
        status, result = await actions.execute(await request.json(), request.headers.get('Idempotency-Key'))
        return web.json_response(result, status=status)

    bridge = MaintenanceBridge(ha, options)
    async def maintenance(request):
        path = request.path.replace('/v1/maintenance', '/v1', 1)
        body = await request.json() if request.method == 'POST' else None
        status, value = await bridge.request(request.method, path, body, request.headers.get('Idempotency-Key'))
        return web.json_response(value, status=status)
    management = Management(ha, options, directory, audit)
    admin_supervisor = HAClient(ha.token, ha.base, timeout=1200)
    admin = Admin(admin_supervisor, options, directory, audit)
    install_mcp(app, options, directory, ha, actions, bridge, audit, management, admin)
    async def administration(application):
        await admin.recover()
        yield
        await admin.close()
    app.cleanup_ctx.append(administration)
    app.router.add_get('/v1/maintenance/check', maintenance)
    app.router.add_get('/v1/maintenance/jobs/{id}', maintenance)
    app.router.add_post('/v1/maintenance/update', maintenance)
    app.router.add_get('/healthz', alive)
    app.router.add_get('/v1/health', health)
    app.router.add_get('/v1/snapshot', snapshot)
    app.router.add_post('/v1/actions', action)
    if watch:
        async def events(application):
            task = asyncio.create_task(ha.watch())
            yield
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        app.cleanup_ctx.append(events)
    return app


async def main_app():
    directory = Path(os.environ.get('JARVIS_DATA_DIR', '/data'))
    with (directory / 'options.json').open() as stream:
        options = json.load(stream)
    ha = HAClient(os.environ['SUPERVISOR_TOKEN'])
    app = create_app(ha, options, directory)
    async def close(application):
        await ha.close()
    app.on_cleanup.append(close)
    return app


if __name__ == '__main__':
    web.run_app(main_app(), host='0.0.0.0', port=8099, access_log=None, print=None)

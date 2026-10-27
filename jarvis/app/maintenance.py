import re
import aiohttp
from .policy import APIError


class MaintenanceBridge:
    def __init__(self, ha, options):
        self.ha, self.options = ha, options

    async def request(self, method, path, body=None, key=None):
        if self.options.get('maintenance_enabled') is not True:
            raise APIError(403, 'maintenance_disabled')
        token = self.options.get('maintenance_token', '')
        if not isinstance(token, str) or len(token) < 32:
            raise APIError(503, 'maintenance_setup_required')
        allowed = (method == 'GET' and (path in ('/v1/check', '/v1/gateway/status') or re.fullmatch(r'/v1/jobs/[a-f0-9]{32}', path))) or (method == 'POST' and path in ('/v1/update', '/v1/gateway/activate'))
        if not allowed:
            raise APIError(400, 'invalid_maintenance_path')
        own = await self.ha.request('GET', '/addons/self/info')
        match = re.fullmatch(r'([a-z0-9]+)_jarvis', own.get('slug', ''))
        if not match:
            raise APIError(409, 'unexpected_app_identity')
        host = match[1] + '-jarvis-updater'
        headers = {'Authorization': 'Bearer ' + token}
        if key:
            headers['Idempotency-Key'] = key
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=60)) as session:
                async with session.request(method, 'http://' + host + ':8100' + path,
                        json=body, headers=headers, allow_redirects=False) as response:
                    result = await response.json()
                    if response.status not in (200, 202):
                        raise APIError(response.status if 400 <= response.status < 600 else 502,
                                       'maintenance_request_rejected')
                    return response.status, result
        except (aiohttp.ClientError, TimeoutError, ValueError):
            raise APIError(502, 'maintenance_unavailable') from None

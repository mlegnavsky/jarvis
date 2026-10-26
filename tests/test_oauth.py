import base64
import hashlib
import re
import tempfile
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer
from app.oauth import OAuth

ORIGIN = 'https://jarvis-api.example.test'
CALLBACK = 'https://chatgpt.com/connector_platform_oauth_redirect'
OPTIONS = {'mcp_enabled': True, 'oauth_public_url': ORIGIN, 'oauth_client_secret': 'c'*40,
           'oauth_owner_secret': 'o'*40, 'oauth_redirect_uris': [CALLBACK]}
VERIFIER = 'v'*64
CHALLENGE = base64.urlsafe_b64encode(hashlib.sha256(VERIFIER.encode()).digest()).rstrip(b'=').decode()

class OAuthTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.oauth = OAuth(dict(OPTIONS), Path(self.tmp.name))
        self.app = web.Application()
        self.oauth.install(self.app)
        self.http = TestClient(TestServer(self.app))
        await self.http.start_server()

    async def asyncTearDown(self):
        await self.http.close()
        self.tmp.cleanup()

    def params(self, **changes):
        return {'client_id': 'jarvis-chatgpt', 'response_type': 'code', 'redirect_uri': CALLBACK,
                'resource': ORIGIN+'/mcp', 'scope': 'jarvis:read', 'state': 'state-123',
                'code_challenge_method': 'S256', 'code_challenge': CHALLENGE, **changes}

    async def authorize(self, **changes):
        response = await self.http.get('/oauth/authorize', params=self.params(**changes))
        self.assertEqual(response.status, 200)
        text = await response.text()
        transaction = re.search('name="transaction" value="([^"]+)"', text)[1]
        csrf = re.search('name="csrf" value="([^"]+)"', text)[1]
        cookie = response.cookies['jarvis_oauth'].value
        response = await self.http.post('/oauth/consent', data={'transaction': transaction,
            'csrf': csrf, 'owner_secret': OPTIONS['oauth_owner_secret'], 'approve': 'yes'},
            headers={'Cookie': 'jarvis_oauth='+cookie, 'Origin': ORIGIN}, allow_redirects=False)
        self.assertEqual(response.status, 303)
        values = parse_qs(urlsplit(response.headers['Location']).query)
        self.assertEqual(values['state'], ['state-123'])
        self.assertEqual(values['iss'], [ORIGIN])
        return values['code'][0]

    async def exchange(self, code, **changes):
        return await self.http.post('/oauth/token', data={
            'grant_type': 'authorization_code', 'client_id': 'jarvis-chatgpt',
            'client_secret': OPTIONS['oauth_client_secret'], 'redirect_uri': CALLBACK,
            'resource': ORIGIN+'/mcp', 'code': code, 'code_verifier': VERIFIER, **changes})

    async def test_discovery_and_full_grant(self):
        response = await self.http.get('/.well-known/oauth-protected-resource/mcp')
        self.assertEqual((await response.json())['resource'], ORIGIN+'/mcp')
        response = await self.http.get('/.well-known/oauth-authorization-server')
        self.assertEqual((await response.json())['code_challenge_methods_supported'], ['S256'])
        code = await self.authorize()
        response = await self.exchange(code)
        self.assertEqual(response.status, 200)
        tokens = await response.json()
        self.assertEqual(self.oauth.verify('Bearer '+tokens['access_token'], 'jarvis:read')['scopes'], ['jarvis:read'])
        self.assertEqual((await self.exchange(code)).status, 400)
        self.assertNotIn(tokens['access_token'].encode(), (Path(self.tmp.name)/'oauth.sqlite').read_bytes())

    async def test_redirect_resource_pkce_and_scope_are_exact(self):
        for changes in ({'redirect_uri': 'https://evil.test'}, {'resource': 'https://evil.test/mcp'},
                        {'code_challenge_method': 'plain'}, {'scope': 'jarvis:control'}):
            response = await self.http.get('/oauth/authorize', params=self.params(**changes))
            self.assertEqual(response.status, 400)
        code = await self.authorize()
        for changes in ({'code_verifier': 'w'*64}, {'resource': 'https://evil.test'},
                        {'redirect_uri': CALLBACK+'x'}, {'client_secret': 'wrong'}):
            response = await self.exchange(code, **changes)
            self.assertIn(response.status, (400, 401))

    async def test_consent_requires_browser_cookie_and_csrf(self):
        response = await self.http.get('/oauth/authorize', params=self.params())
        text = await response.text()
        transaction = re.search('name="transaction" value="([^"]+)"', text)[1]
        response = await self.http.post('/oauth/consent', data={'transaction': transaction,
            'csrf': 'wrong', 'owner_secret': OPTIONS['oauth_owner_secret'], 'approve': 'yes'},
            headers={'Origin': ORIGIN}, allow_redirects=False)
        self.assertEqual(response.status, 403)

    async def test_login_page_preserves_same_origin_form_submission(self):
        response = await self.http.get('/oauth/authorize', params=self.params())
        # Fetch §3.2: no-referrer turns a navigation POST Origin into null,
        # which the consent endpoint correctly rejects. Keep referrers local
        # while preserving the browser's Origin on the same-origin form POST.
        self.assertEqual(response.headers['Referrer-Policy'], 'same-origin')
        await self.authorize()

    async def test_consent_rejects_null_missing_and_foreign_origins(self):
        for origin in (None, 'null', 'https://evil.test'):
            headers = {} if origin is None else {'Origin': origin}
            response = await self.http.post('/oauth/consent', headers=headers,
                data={'owner_secret': OPTIONS['oauth_owner_secret']}, allow_redirects=False)
            self.assertEqual(response.status, 403)
            self.assertEqual((await response.json())['error'], 'invalid_origin')

    async def test_refresh_rotation_reuse_revokes_family_and_survives_restart(self):
        tokens = await (await self.exchange(await self.authorize())).json()
        self.oauth = OAuth(dict(OPTIONS), Path(self.tmp.name))
        self.assertTrue(self.oauth.verify('Bearer '+tokens['access_token'], 'jarvis:read'))
        data = {'grant_type': 'refresh_token', 'refresh_token': tokens['refresh_token'],
                'client_id': 'jarvis-chatgpt', 'client_secret': OPTIONS['oauth_client_secret'], 'resource': ORIGIN+'/mcp'}
        rotated = await (await self.http.post('/oauth/token', data=data)).json()
        response = await self.http.post('/oauth/token', data=data)
        self.assertEqual(response.status, 400)
        from app.policy import APIError
        with self.assertRaises(APIError):
            self.oauth.verify('Bearer '+rotated['access_token'], 'jarvis:read')

    async def test_changed_config_invalidates_old_grant(self):
        tokens = await (await self.exchange(await self.authorize())).json()
        changed = OAuth({**OPTIONS, 'oauth_owner_secret': 'n'*40}, Path(self.tmp.name))
        from app.policy import APIError
        with self.assertRaises(APIError):
            changed.verify('Bearer '+tokens['access_token'], 'jarvis:read')

    async def test_expired_and_revoked_tokens_fail_closed(self):
        tokens = await (await self.exchange(await self.authorize())).json()
        response = await self.http.post('/oauth/revoke', data={'client_id': 'jarvis-chatgpt',
            'client_secret': OPTIONS['oauth_client_secret'], 'token': tokens['refresh_token']})
        self.assertEqual(response.status, 200)
        from app.policy import APIError
        with self.assertRaises(APIError):
            self.oauth.verify('Bearer '+tokens['access_token'], 'jarvis:read')
        tokens = await (await self.exchange(await self.authorize())).json()
        with self.oauth.db() as db:
            db.execute("UPDATE artifacts SET expires=0 WHERE kind='access'")
        with self.assertRaises(APIError):
            self.oauth.verify('Bearer '+tokens['access_token'], 'jarvis:read')

    async def test_login_attempts_are_persistent_and_bounded(self):
        response = await self.http.get('/oauth/authorize', params=self.params())
        text = await response.text()
        transaction = re.search('name="transaction" value="([^"]+)"', text)[1]
        csrf = re.search('name="csrf" value="([^"]+)"', text)[1]
        cookie = response.cookies['jarvis_oauth'].value
        for attempt in range(11):
            response = await self.http.post('/oauth/consent', data={'transaction': transaction,
                'csrf': csrf, 'owner_secret': 'wrong', 'approve': 'yes'},
                headers={'Cookie': 'jarvis_oauth='+cookie, 'Origin': ORIGIN})
            self.assertEqual(response.status, 403 if attempt < 10 else 429)

    async def test_discovery_never_trusts_host_or_forwarded_headers(self):
        response = await self.http.get('/.well-known/oauth-protected-resource/mcp',
            headers={'Host': 'evil.test', 'X-Forwarded-Host': 'evil.test'})
        self.assertEqual((await response.json())['resource'], ORIGIN+'/mcp')

    async def test_basic_auth_form_decodes_punctuation_in_secret(self):
        from urllib.parse import quote_plus
        await self.http.close()
        secret = 'c'*32 + '+/=:% '
        self.oauth = OAuth({**OPTIONS, 'oauth_client_secret': secret}, Path(self.tmp.name))
        app = web.Application()
        self.oauth.install(app)
        self.http = TestClient(TestServer(app))
        await self.http.start_server()
        code = await self.authorize()
        basic = base64.b64encode(('jarvis-chatgpt:'+quote_plus(secret)).encode()).decode()
        response = await self.http.post('/oauth/token', headers={'Authorization': 'Basic '+basic}, data={
            'grant_type': 'authorization_code', 'code': code, 'code_verifier': VERIFIER,
            'redirect_uri': CALLBACK, 'resource': ORIGIN+'/mcp'})
        self.assertEqual(response.status, 200)
        tokens = await response.json()
        response = await self.http.post('/oauth/revoke', headers={'Authorization': 'Basic '+basic},
            data={'token': tokens['refresh_token']})
        self.assertEqual(response.status, 200)

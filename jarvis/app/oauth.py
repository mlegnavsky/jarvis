"""Single-owner, pre-registered OAuth client. Not a general identity provider."""
import base64
from contextlib import contextmanager
import hashlib
import hmac
import html
import json
import os
import re
import secrets
import sqlite3
import time
from urllib.parse import urlencode, urlsplit, unquote_plus

from aiohttp import web
from .policy import APIError

CLIENT = 'jarvis-chatgpt'
ALL_SCOPES = {'jarvis:read', 'jarvis:control', 'jarvis:maintain'}


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def equal(left, right):
    return isinstance(left, str) and isinstance(right, str) and hmac.compare_digest(digest(left), digest(right))


class OAuth:
    def __init__(self, options, directory):
        self.options = dict(options)
        self.origin = options.get('oauth_public_url', '')
        self.redirects = options.get('oauth_redirect_uris', [])
        self.secret = options.get('oauth_client_secret', '')
        self.owner = options.get('oauth_owner_secret', '')
        self.resource = self.origin + '/mcp'
        self.generation = digest(json.dumps([self.origin, self.redirects, self.secret, self.owner], sort_keys=True))
        self.path = directory / 'oauth.sqlite'
        with self.db() as db:
            db.execute('CREATE TABLE IF NOT EXISTS artifacts (hash TEXT PRIMARY KEY, kind TEXT, expires REAL, data TEXT)')
            db.execute('CREATE TABLE IF NOT EXISTS attempts (at REAL)')
        os.chmod(self.path, 0o600)

    @contextmanager
    def db(self):
        connection = sqlite3.connect(self.path)
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def ready(self):
        parsed = urlsplit(self.origin)
        if (self.options.get('mcp_enabled') is not True or parsed.scheme != 'https' or not parsed.hostname
                or parsed.username or parsed.password or parsed.path or parsed.query or parsed.fragment
                or not re.fullmatch(r'https://[a-zA-Z0-9.-]+(?::[0-9]+)?', self.origin)
                or len(self.secret) < 32 or len(self.owner) < 32
                or not isinstance(self.redirects, list) or not self.redirects):
            raise APIError(503, 'mcp_setup_required')
        for value in self.redirects:
            target = urlsplit(value)
            if (target.scheme != 'https' or not target.hostname or target.username or target.password
                    or target.fragment or target.query
                    or not re.fullmatch(r'[a-zA-Z0-9.-]+(?::[0-9]+)?', target.netloc)):
                raise APIError(503, 'mcp_setup_required')

    def scopes(self):
        result = {'jarvis:read'}
        if self.options.get('writes_enabled') is True:
            result.add('jarvis:control')
        if self.options.get('maintenance_enabled') is True:
            result.add('jarvis:maintain')
        return result

    def put(self, db, kind, value, data, expires):
        db.execute('DELETE FROM artifacts WHERE expires <= ?', (time.time(),))
        if db.execute('SELECT COUNT(*) FROM artifacts').fetchone()[0] >= 10000:
            raise APIError(503, 'oauth_journal_full')
        db.execute('INSERT INTO artifacts VALUES (?,?,?,?)', (digest(value), kind, expires,
            json.dumps({**data, 'generation': self.generation})))

    def load(self, db, kind, value):
        if not isinstance(value, str) or len(value) > 512:
            raise APIError(400, 'authorization_form_missing' if kind == 'flow' else 'invalid_grant')
        row = db.execute('SELECT kind,expires,data FROM artifacts WHERE hash=?', (digest(value),)).fetchone()
        if not row or row[0] != kind:
            raise APIError(400, 'authorization_not_found' if kind == 'flow' else 'invalid_grant')
        if row[1] <= time.time():
            raise APIError(400, 'authorization_expired' if kind == 'flow' else 'invalid_grant')
        data = json.loads(row[2])
        if data['generation'] != self.generation or data.get('revoked'):
            raise APIError(400, 'authorization_invalidated' if kind == 'flow' else 'invalid_grant')
        return data

    def update(self, db, value, data):
        db.execute('UPDATE artifacts SET data=? WHERE hash=?', (json.dumps(data), digest(value)))

    def revoke_family(self, db, family):
        for key, raw in db.execute("SELECT hash,data FROM artifacts WHERE kind IN ('access','refresh')").fetchall():
            value = json.loads(raw)
            if value.get('family') == family:
                value['revoked'] = True
                db.execute('UPDATE artifacts SET data=? WHERE hash=?', (json.dumps(value), key))

    def issue(self, db, scopes, family=None, deadline=None):
        deadline = deadline or time.time() + 30*86400
        common = {'scopes': scopes, 'family': family or secrets.token_urlsafe(24),
                  'deadline': deadline, 'resource': self.resource}
        access, refresh = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        self.put(db, 'access', access, common, min(time.time()+900, deadline))
        self.put(db, 'refresh', refresh, common, deadline)
        return {'access_token': access, 'refresh_token': refresh, 'token_type': 'Bearer',
                'expires_in': min(900, max(0, int(deadline-time.time()))), 'scope': ' '.join(scopes)}

    def verify(self, header, scope=None):
        self.ready()
        if not isinstance(header, str) or not header.startswith('Bearer '):
            raise APIError(401, 'invalid_token')
        try:
            with self.db() as db:
                data = self.load(db, 'access', header[7:])
        except APIError:
            raise APIError(401, 'invalid_token') from None
        if data.get('resource') != self.resource:
            raise APIError(401, 'invalid_token')
        if not set(data['scopes']) <= self.scopes() or scope and scope not in data['scopes']:
            raise APIError(403, 'insufficient_scope')
        return data

    def client(self, request, values):
        identifier, secret = values.get('client_id'), values.get('client_secret')
        header = request.headers.get('Authorization', '')
        if header.startswith('Basic '):
            if identifier or secret:
                raise APIError(401, 'invalid_client')
            try:
                identifier, secret = base64.b64decode(header[6:], validate=True).decode().split(':', 1)
                identifier, secret = unquote_plus(identifier), unquote_plus(secret)
            except (ValueError, UnicodeError):
                raise APIError(401, 'invalid_client') from None
        if identifier != CLIENT or not equal(secret, self.secret):
            raise APIError(401, 'invalid_client')

    def limit_login(self, db):
        now = time.time()
        db.execute('DELETE FROM attempts WHERE at < ?', (now-60,))
        if db.execute('SELECT COUNT(*) FROM attempts').fetchone()[0] >= 10:
            raise APIError(429, 'login_rate_limited')
        db.execute('INSERT INTO attempts VALUES (?)', (now,))

    def install(self, app):
        @web.middleware
        async def boundary(request, handler):
            form_sources = "'self'"
            try:
                self.ready()
                # Chromium checks the redirect destination of a form POST
                # against the initiating document's form-action policy too.
                # Origins come only from validated, pre-registered callbacks;
                # OAuth authorize/token still enforce exact redirect URIs.
                form_sources += ' ' + ' '.join(sorted({
                    'https://' + urlsplit(value).netloc for value in self.redirects}))
                if request.headers.get('Origin') and request.headers['Origin'] != self.origin:
                    raise APIError(403, 'invalid_origin')
                response = await handler(request)
            except APIError as error:
                response = web.json_response({'error': error.code}, status=error.status)
            except (ValueError, UnicodeError):
                response = web.json_response({'error': 'invalid_request'}, status=400)
            response.headers.update({'Cache-Control': 'no-store', 'Pragma': 'no-cache',
                'Referrer-Policy': 'same-origin', 'X-Content-Type-Options': 'nosniff',
                'Content-Security-Policy': "default-src 'none'; form-action " + form_sources + "; frame-ancestors 'none'; base-uri 'none'"})
            return response
        # This middleware is path-scoped so existing REST authentication is unchanged.
        @web.middleware
        async def scoped(request, handler):
            if request.path.startswith('/oauth/') or request.path.startswith('/.well-known/oauth-'):
                return await boundary(request, handler)
            return await handler(request)
        app.middlewares.append(scoped)

        async def resource(request):
            return web.json_response({'resource': self.resource, 'authorization_servers': [self.origin],
                'scopes_supported': sorted(self.scopes()), 'bearer_methods_supported': ['header']})

        async def metadata(request):
            return web.json_response({'issuer': self.origin, 'authorization_endpoint': self.origin+'/oauth/authorize',
                'token_endpoint': self.origin+'/oauth/token', 'revocation_endpoint': self.origin+'/oauth/revoke',
                'response_types_supported': ['code'], 'grant_types_supported': ['authorization_code', 'refresh_token'],
                'token_endpoint_auth_methods_supported': ['client_secret_post', 'client_secret_basic'],
                'code_challenge_methods_supported': ['S256'], 'scopes_supported': sorted(self.scopes()),
                'authorization_response_iss_parameter_supported': True})

        async def authorize(request):
            query = request.query
            if any(len(query.getall(key)) != 1 for key in query):
                raise APIError(400, 'invalid_request')
            scopes = query.get('scope', 'jarvis:read').split()
            if not scopes or not set(scopes) <= self.scopes():
                raise APIError(400, 'invalid_scope')
            if (query.get('client_id') != CLIENT or query.get('response_type') != 'code'
                    or query.get('redirect_uri') not in self.redirects or query.get('resource') != self.resource
                    or query.get('code_challenge_method') != 'S256'
                    or not re.fullmatch(r'[A-Za-z0-9_-]{43}', query.get('code_challenge', ''))
                    or not 1 <= len(query.get('state', '')) <= 512):
                raise APIError(400, 'invalid_request')
            transaction, cookie, csrf = [secrets.token_urlsafe(32) for _ in range(3)]
            with self.db() as db:
                # Bound unauthenticated outstanding flows separately from the persistent token journal.
                db.execute('DELETE FROM artifacts WHERE expires <= ?', (time.time(),))
                if db.execute("SELECT COUNT(*) FROM artifacts WHERE kind='flow'").fetchone()[0] >= 200:
                    raise APIError(429, 'too_many_authorizations')
                self.put(db, 'flow', transaction, {'query': dict(query), 'scopes': sorted(set(scopes)),
                    'cookie': digest(cookie), 'csrf': digest(csrf)}, time.time()+300)
            page = ('<!doctype html><html lang="cs"><meta charset="utf-8"><meta name="viewport" content="width=device-width">'
                '<title>Připojit Jarvise</title><h1>Připojit Jarvise k ChatGPT</h1>'
                '<p>Povolujete přístup k domácnosti: '+html.escape(', '.join(scopes))+'</p>'
                '<p>jarvis:read = čtení; jarvis:control = povolené povely; jarvis:maintain = aktualizace.</p>'
                '<form method="post" action="/oauth/consent">'
                '<input type="hidden" name="transaction" value="'+transaction+'">'
                '<input type="hidden" name="csrf" value="'+csrf+'">'
                '<label>Samostatný přihlašovací klíč vlastníka <input type="password" name="owner_secret" autocomplete="current-password" required></label>'
                '<button name="approve" value="yes">Povolit uvedený přístup</button>'
                '<button name="approve" value="no">Odmítnout</button></form></html>')
            response = web.Response(text=page, content_type='text/html')
            response.set_cookie('jarvis_oauth', cookie, secure=True, httponly=True, samesite='Lax', max_age=300, path='/oauth')
            return response

        async def consent(request):
            if request.headers.get('Origin') != self.origin:
                raise APIError(403, 'invalid_origin')
            values = await request.post()
            if any(len(values.getall(key)) != 1 for key in values):
                raise APIError(400, 'invalid_request')
            # Commit attempts separately: failed authentication must not roll back the limiter.
            with self.db() as db:
                self.limit_login(db)
            with self.db() as db:
                flow = self.load(db, 'flow', values.get('transaction'))
                cookie, csrf = request.cookies.get('jarvis_oauth', ''), values.get('csrf', '')
                if not equal(digest(cookie), flow['cookie']) or not equal(digest(csrf), flow['csrf']):
                    raise APIError(403, 'invalid_csrf')
                if not equal(values.get('owner_secret'), self.owner):
                    raise APIError(403, 'invalid_owner_secret')
                query = flow['query']
                db.execute('DELETE FROM artifacts WHERE hash=?', (digest(values['transaction']),))
                result = {'state': query['state'], 'iss': self.origin}
                if values.get('approve') == 'yes':
                    code = secrets.token_urlsafe(32)
                    self.put(db, 'code', code, {'query': query, 'scopes': flow['scopes']}, time.time()+60)
                    result['code'] = code
                else:
                    result['error'] = 'access_denied'
            response = web.Response(status=303, headers={'Location': query['redirect_uri']+'?'+urlencode(result)})
            response.del_cookie('jarvis_oauth', path='/oauth')
            return response

        async def token(request):
            values = await request.post()
            if any(len(values.getall(key)) != 1 for key in values):
                raise APIError(400, 'invalid_request')
            self.client(request, values)
            if values.get('resource') != self.resource:
                raise APIError(400, 'invalid_target')
            reuse = False
            with self.db() as db:
                if values.get('grant_type') == 'authorization_code':
                    code = self.load(db, 'code', values.get('code'))
                    query = code['query']
                    verifier = values.get('code_verifier', '')
                    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
                    if (not re.fullmatch(r'[A-Za-z0-9._~-]{43,128}', verifier)
                            or not equal(challenge, query['code_challenge'])
                            or values.get('redirect_uri') != query['redirect_uri']):
                        raise APIError(400, 'invalid_grant')
                    db.execute('DELETE FROM artifacts WHERE hash=?', (digest(values['code']),))
                    tokens = self.issue(db, code['scopes'])
                elif values.get('grant_type') == 'refresh_token':
                    refresh = self.load(db, 'refresh', values.get('refresh_token'))
                    if refresh.get('used'):
                        self.revoke_family(db, refresh['family'])
                        reuse = True
                    else:
                        if values.get('scope') and set(values['scope'].split()) != set(refresh['scopes']):
                            raise APIError(400, 'invalid_scope')
                        refresh['used'] = True
                        self.update(db, values['refresh_token'], refresh)
                        tokens = self.issue(db, refresh['scopes'], refresh['family'], refresh['deadline'])
                else:
                    raise APIError(400, 'unsupported_grant_type')
            if reuse:
                raise APIError(400, 'invalid_grant')
            return web.json_response(tokens)

        async def revoke(request):
            values = await request.post()
            self.client(request, values)
            with self.db() as db:
                for kind in ('access', 'refresh'):
                    try:
                        data = self.load(db, kind, values.get('token'))
                    except APIError:
                        continue
                    self.revoke_family(db, data['family'])
            return web.Response(status=200)

        app.router.add_get('/.well-known/oauth-protected-resource', resource)
        app.router.add_get('/.well-known/oauth-protected-resource/mcp', resource)
        app.router.add_get('/.well-known/oauth-authorization-server', metadata)
        app.router.add_get('/oauth/authorize', authorize)
        app.router.add_post('/oauth/consent', consent)
        app.router.add_post('/oauth/token', token)
        app.router.add_post('/oauth/revoke', revoke)

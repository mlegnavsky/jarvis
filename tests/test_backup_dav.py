"""Real HTTP tests for the constrained private backup endpoint."""
import base64
import hashlib
import http.client
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import time
import unittest
import xml.etree.ElementTree as ET

SOURCE = Path(__file__).resolve().parents[1] / 'testing/backup-dav'

class BackupDAVSourceTests(unittest.TestCase):
    def test_endpoint_exists(self):
        self.assertTrue((SOURCE / 'index.php').is_file(), 'private WebDAV endpoint missing')

@unittest.skipUnless(shutil.which('php'), 'PHP runtime required; mandatory in backup-dav CI job')
class BackupDAVTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.web = self.root / 'httpdocs'
        self.web.mkdir()
        self.assertTrue((SOURCE / 'index.php').exists(), 'private WebDAV implementation missing')
        shutil.copytree(SOURCE, self.web / 'backup-dav')
        self.private = self.root / 'ha-backups'
        self.private.mkdir()
        self.password = 'test-only-' + 'a' * 40
        hashed = subprocess.check_output(['php', '-r', 'echo password_hash($argv[1], PASSWORD_DEFAULT);', self.password]).decode()
        self.config = self.private / 'access.json'
        self.config.write_text(json.dumps({'username': 'jarvis-backup', 'password_hash': hashed}))
        self.config.chmod(0o600)
        sock = socket.socket(); sock.bind(('127.0.0.1', 0)); self.port = sock.getsockname()[1]; sock.close()
        self.log = tempfile.TemporaryFile()
        self.proc = subprocess.Popen(['php', '-S', f'127.0.0.1:{self.port}', '-t', str(self.web)], stdout=self.log, stderr=self.log)
        for _ in range(100):
            try:
                s = socket.create_connection(('127.0.0.1', self.port), timeout=.1); s.close(); break
            except OSError: time.sleep(.02)
    def tearDown(self):
        if hasattr(self, 'proc'): self.proc.terminate(); self.proc.wait(timeout=5); self.log.close()
        self.tmp.cleanup()
    def req(self, method='PROPFIND', name='', data=None, auth=True, headers=None):
        h = {'Depth': '1'}
        if auth: h['Authorization'] = 'Basic ' + base64.b64encode(('jarvis-backup:' + self.password).encode()).decode()
        h.update(headers or {})
        c = http.client.HTTPConnection('127.0.0.1', self.port, timeout=5)
        c.request(method, '/backup-dav/index.php/' + name, body=data, headers=h)
        r = c.getresponse(); result = (r.status, dict(r.getheaders()), r.read()); c.close(); return result
    def test_authentication_before_listing_or_write(self):
        for method in ['GET', 'PROPFIND', 'PUT', 'OPTIONS', 'DELETE']:
            self.assertEqual(self.req(method, 'test.tar', b'private', auth=False)[0], 401)
        self.assertFalse((self.private / 'objects').exists())
    def test_bad_password(self):
        self.password = 'incorrect'
        self.assertEqual(self.req()[0], 401)
    def test_missing_config_fails_closed(self):
        self.config.unlink()
        self.assertEqual(self.req()[0], 503)
    def test_config_symlink_rejected(self):
        target = self.root / 'outside.json'; self.config.rename(target); self.config.symlink_to(target)
        self.assertEqual(self.req()[0], 503)
    def test_round_trip_integrity_listing_and_private_config(self):
        payload = os.urandom(100000)
        self.assertEqual(self.req('PUT', 'backup.tar', payload)[0], 201)
        self.assertEqual(self.req('GET', 'backup.tar')[2], payload)
        self.assertEqual(self.req('HEAD', 'backup.tar')[2], b'')
        status, _, listing = self.req()
        self.assertEqual(status, 207); ET.fromstring(listing)
        self.assertIn(b'backup.tar', listing); self.assertNotIn(b'access.json', listing)
        self.assertEqual((self.private / 'objects/backup.tar').read_bytes(), payload)
        self.assertEqual(self.req('GET', 'access.json')[0], 403)
    def test_idempotent_retry_and_conflicting_write(self):
        self.assertEqual(self.req('PUT', 'backup.tar', b'one')[0], 201)
        self.assertEqual(self.req('PUT', 'backup.tar', b'one')[0], 204)
        self.assertEqual(self.req('PUT', 'backup.tar', b'two')[0], 412)
        self.assertEqual(self.req('GET', 'backup.tar')[2], b'one')
    def test_path_traversal_extensions_nested_paths(self):
        for name in ['../access.json', '%2e%2e/access.json', '%252e%252e%252faccess.json', 'x/y.tar', 'x.php', '.hidden.tar', 'x%00.tar', 'x%5cy.tar']:
            with self.subTest(name=name):
                status = self.req('PUT', name, b'x')[0]
                self.assertTrue(400 <= status < 500, status)
                self.assertEqual(json.loads(self.config.read_text())['username'], 'jarvis-backup')
                self.assertFalse((self.web / 'backup-dav/access.json').exists())
    def test_symlink_object_rejected(self):
        self.req('OPTIONS')
        outside = self.root / 'private.tar'; outside.write_bytes(b'secret')
        (self.private / 'objects/escape.tar').symlink_to(outside)
        self.assertEqual(self.req('GET', 'escape.tar')[0], 403)
        self.assertNotIn(b'escape.tar', self.req()[2])
    def test_deletion_and_collection_mutations_disabled(self):
        self.req('PUT', 'backup.tar', b'one')
        for method in ['DELETE', 'MOVE', 'COPY', 'MKCOL', 'PROPPATCH']:
            self.assertEqual(self.req(method, 'backup.tar')[0], 405)
        self.assertEqual(self.req('GET', 'backup.tar')[2], b'one')
    def test_metadata_json_and_options(self):
        self.assertEqual(self.req('PUT', 'backup.metadata.json', b'{}')[0], 201)
        self.assertEqual(self.req('GET', 'backup.metadata.json')[2], b'{}')
        self.assertEqual(self.req('OPTIONS')[0], 200)
    def test_reject_infinite_depth(self):
        self.assertEqual(self.req(headers={'Depth':'infinity'})[0], 403)
    def test_objects_symlink_rejected(self):
        (self.private / 'objects').symlink_to(self.web, target_is_directory=True)
        self.assertEqual(self.req()[0], 503)

    def test_oversize_metadata_does_not_publish_partial_file(self):
        self.assertEqual(self.req('PUT', 'large.metadata.json', b'x' * (1048576 + 1))[0], 413)
        self.assertFalse((self.private / 'objects/large.metadata.json').exists())
        self.assertEqual(list((self.private / 'objects').glob('.incoming-*')), [])
    def test_incomplete_request_never_publishes(self):
        auth = base64.b64encode(('jarvis-backup:' + self.password).encode()).decode()
        conn = socket.create_connection(('127.0.0.1', self.port), timeout=3)
        conn.sendall((f'PUT /backup-dav/index.php/partial.tar HTTP/1.1\r\nHost: localhost\r\nAuthorization: Basic {auth}\r\nContent-Length: 1000\r\nConnection: close\r\n\r\nshort').encode())
        conn.shutdown(socket.SHUT_WR)
        try:
            while conn.recv(4096): pass
        finally: conn.close()
        self.assertFalse((self.private / 'objects/partial.tar').exists())
    def test_busy_upload_lock_rejects_before_body_publication(self):
        import fcntl
        with (self.private / 'uploads.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.assertEqual(self.req('PUT', 'busy.tar', b'one')[0], 423)
            self.assertFalse((self.private / 'objects/busy.tar').exists())
        self.assertEqual(self.req('PUT', 'busy.tar', b'one')[0], 201)
    def test_setup_only_generates_hash_configuration(self):
        c = http.client.HTTPConnection('127.0.0.1', self.port, timeout=5)
        before = self.config.read_bytes()
        c.request('GET', '/backup-dav/setup.php'); r = c.getresponse(); body = r.read(); c.close()
        self.assertEqual(r.status, 200)
        import re
        encoded = re.search(rb'data:application/json;base64,([^"\s]+)', body).group(1)
        config = json.loads(base64.b64decode(encoded))
        self.assertEqual(config['username'], 'jarvis-backup')
        self.assertIn('password_hash', config); self.assertNotIn('password', config)
        self.assertEqual(self.config.read_bytes(), before)

    def test_native_home_assistant_webdav_client(self):
        import asyncio
        from aiohttp import ClientSession, ClientTimeout
        from aiowebdav2.client import Client, ClientOptions
        async def run():
            async with ClientSession() as session:
                client = Client(url=f'http://127.0.0.1:{self.port}/backup-dav/index.php/', username='jarvis-backup', password=self.password,
                                options=ClientOptions(session=session, timeout=ClientTimeout(total=5)))
                self.assertTrue(await client.check())
                self.assertTrue(await client.check('/'))
                payload = b'encrypted-backup-test' * 100
                async def chunks():
                    yield payload[:50]
                    yield payload[50:]
                await client.upload_iter(chunks(), '/native.tar', content_length=len(payload))
                await client.upload_iter('{"backup_id":"test"}', '/native.metadata.json')
                files = await client.list_files('/')
                self.assertTrue(any(name.endswith('native.metadata.json') for name in files), files)
                stream = await client.download_iter('/native.tar')
                result = b''.join([chunk async for chunk in stream])
                self.assertEqual(result, payload)
        asyncio.run(run())

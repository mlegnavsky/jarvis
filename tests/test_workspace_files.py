import base64
import hashlib
import os
from pathlib import Path
import tempfile
import unittest
from app.policy import APIError


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        from app.workspace_files import WorkspaceFiles
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.files = WorkspaceFiles(self.root, 'addons')

    def test_source_write_and_executable_mode_are_preserved(self):
        self.files.write('jarvis_core/run.sh', '#!/bin/sh\necho test\n', 'missing')
        (self.root/'jarvis_core/run.sh').chmod(0o755)
        before = self.files.read('jarvis_core/run.sh')
        self.files.write('jarvis_core/run.sh', '#!/bin/sh\necho updated\n', before['revision'])
        self.assertEqual((self.root/'jarvis_core/run.sh').stat().st_mode & 0o777, 0o755)
        self.files.write('jarvis_core/Dockerfile', 'FROM scratch\n', 'missing')
        self.assertEqual(len(self.files.inventory()['items']), 2)

    def test_traversal_symlink_hardlink_and_secret_paths_are_rejected(self):
        for p in ('../x.py', '/etc/passwd', 'x/.env', 'x/secrets.yaml', 'x/options.json', 'x/.git/config', 'x/key.pem'):
            with self.assertRaises(APIError, msg=p):
                self.files.read(p)
        (self.root/'outside.py').write_text('pass\n')
        (self.root/'project').mkdir()
        (self.root/'project/link.py').symlink_to(self.root/'outside.py')
        with self.assertRaises(APIError):
            self.files.read('project/link.py')
        os.link(self.root/'outside.py', self.root/'project/hard.py')
        with self.assertRaises(APIError):
            self.files.read('project/hard.py')

    def test_binary_upload_chunks_verify_hash_before_publish(self):
        from app.workspace_files import Uploads, WorkspaceFiles
        files = WorkspaceFiles(self.root/'media', 'media')
        files.root.mkdir()
        upload = Uploads(self.root/'private')
        data = b'\x89PNG\x00binary'
        args = {'upload_id': 'sample', 'workspace': 'media', 'path': 'test/image.png', 'expected_revision': 'missing', 'size': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
        upload.begin(args)
        upload.chunk('sample', 0, base64.b64encode(data[:5]).decode())
        with self.assertRaises(APIError):
            upload.chunk('sample', 0, base64.b64encode(b'wrong').decode())
        upload.chunk('sample', 5, base64.b64encode(data[5:]).decode())
        result = upload.finish('sample', files)
        self.assertTrue(result['verified'])
        self.assertEqual((files.root/'test/image.png').read_bytes(), data)

    def test_bad_upload_digest_and_stale_target_never_replace_file(self):
        from app.workspace_files import Uploads, WorkspaceFiles
        files = WorkspaceFiles(self.root/'media', 'media')
        files.root.mkdir()
        upload = Uploads(self.root/'private')
        upload.begin({'upload_id': 'bad', 'workspace': 'media', 'path': 'bad.png', 'expected_revision': 'missing', 'size': 1, 'sha256': '0'*64})
        upload.chunk('bad', 0, base64.b64encode(b'x').decode())
        with self.assertRaises(APIError):
            upload.finish('bad', files)
        self.assertFalse((files.root/'bad.png').exists())

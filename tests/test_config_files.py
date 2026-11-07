import os
from pathlib import Path
import tempfile
import unittest
from app.policy import APIError


class ConfigFilesTests(unittest.TestCase):
    def setUp(self):
        from app.config_files import ConfigFiles
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'ha'
        self.root.mkdir()
        self.files = ConfigFiles(self.root)

    def test_write_revision_replacement_and_delete(self):
        self.assertEqual(self.files.read('packages/test.yaml')['revision'], 'missing')
        result = self.files.write('packages/test.yaml', 'test: 1\n', 'missing')
        self.assertEqual(self.files.read('packages/test.yaml')['content'], 'test: 1\n')
        with self.assertRaises(APIError):
            self.files.write('packages/test.yaml', 'test: 2\n', 'missing')
        self.files.write('packages/test.yaml', None, result['revision'])
        self.assertEqual(self.files.read('packages/test.yaml')['revision'], 'missing')

    def test_traversal_sensitive_files_symlinks_and_hardlinks_rejected(self):
        for path in ('../outside.yaml', '/etc/passwd', '.storage/auth', 'secrets.yaml',
                     'packages/../secrets.yaml', 'packages/.hidden.yaml', 'custom_components/x/a.zip'):
            with self.assertRaises(APIError, msg=path):
                self.files.read(path)
        external = Path(self.tmp.name) / 'outside'
        external.mkdir()
        (self.root / 'packages').symlink_to(external, target_is_directory=True)
        with self.assertRaises(APIError):
            self.files.write('packages/test.yaml', 'test: 1', 'missing')
        (self.root / 'packages').unlink()
        (self.root / 'packages').mkdir()
        (external / 'secret.yaml').write_text('secret: value')
        os.link(external / 'secret.yaml', self.root / 'packages/hard.yaml')
        with self.assertRaises(APIError):
            self.files.read('packages/hard.yaml')
        (self.root / 'packages/link.yaml').symlink_to(external / 'secret.yaml')
        with self.assertRaises(APIError):
            self.files.read('packages/link.yaml')

    def test_syntax_checked_without_execution_and_ha_tags_supported(self):
        for path, content in [('packages/test.yaml', 'x: [unterminated'),
                              ('custom_components/test/__init__.py', 'invalid python !'),
                              ('custom_components/test/manifest.json', '{')]:
            with self.assertRaises(APIError):
                self.files.write(path, content, 'missing')
        self.files.write('configuration.yaml', 'automation: !include automations.yaml\npassword: !secret test\n', 'missing')
        self.assertEqual(self.files.read('configuration.yaml')['revision'] == 'missing', False)
        self.files.write('custom_components/test/__init__.py', 'raise Exception("not executed")\n', 'missing')

    def test_file_size_and_nonregular_targets_are_bounded(self):
        with self.assertRaises(APIError):
            self.files.write('packages/large.yaml', 'a'*262145, 'missing')
        (self.root / 'packages').mkdir()
        (self.root / 'packages/dir.yaml').mkdir()
        with self.assertRaises(APIError):
            self.files.read('packages/dir.yaml')

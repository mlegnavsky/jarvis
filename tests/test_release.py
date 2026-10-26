"""Release gate rejects packages that Home Assistant would mislabel."""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        source = Path(__file__).resolve().parents[1]
        for name in ('jarvis', 'jarvis_updater', 'scripts'):
            shutil.copytree(source / name, self.root / name)

    def check(self):
        return subprocess.run([sys.executable, 'scripts/check_manifest.py'], cwd=self.root,
                              capture_output=True, text=True)

    def test_current_release_is_consistent(self):
        result = self.check()
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_runtime_version_mismatch_blocks_release(self):
        (self.root / 'jarvis/app/__init__.py').write_text("VERSION = '0.0.0'\n")
        result = self.check()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('runtime version', result.stderr)

    def test_changelog_suffix_blocks_release(self):
        path = self.root / 'jarvis/CHANGELOG.md'
        lines = path.read_text().splitlines()
        lines[0] += ' — description that breaks HA selection'
        path.write_text('\n'.join(lines) + '\n')
        result = self.check()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('changelog', result.stderr)

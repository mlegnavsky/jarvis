"""Boot diagnostics must be observational, and cloud tests must be explicit."""
import ast
from pathlib import Path
import unittest

class StartupPolicyTests(unittest.TestCase):
 def test_companion_test_never_changes_pipeline_configuration(self):
  tree=ast.parse(Path(__file__).with_name('__init__.py').read_text())
  calls=[n.func.id for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name)]
  self.assertNotIn('async_update_pipeline',calls)
 def test_boot_does_not_start_cloud_conversation(self):
  tree=ast.parse(Path(__file__).with_name('__init__.py').read_text())
  start=next(n for n in ast.walk(tree) if isinstance(n,ast.AsyncFunctionDef) and n.name=='start')
  calls=[n.func.id for n in ast.walk(start) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name)]
  self.assertNotIn('companion_test',calls)

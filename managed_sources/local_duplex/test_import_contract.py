"""Check our cross-component imports against their actual source exports."""
import ast
from pathlib import Path
import unittest


class ImportContractTests(unittest.TestCase):
    def test_custom_component_named_imports_exist(self):
        root=Path(__file__).resolve().parents[1]
        sources={
            'custom_components.extended_openai_conversation.dialogue':root/'companion/dialogue.py',
            'custom_components.jarvis_voice_diagnostics.turn_taking':root/'voice_diagnostics/turn_taking.py',
        }
        tree=ast.parse(Path(__file__).with_name('__init__.py').read_text())
        for node in ast.walk(tree):
            if isinstance(node,ast.ImportFrom) and node.module in sources:
                target=ast.parse(sources[node.module].read_text())
                exported={n.name for n in ast.walk(target) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef))}
                exported.update(a.asname or a.name for n in ast.walk(target) if isinstance(n,ast.ImportFrom) for a in n.names)
                for imported in node.names:self.assertIn(imported.name,exported,node.module)

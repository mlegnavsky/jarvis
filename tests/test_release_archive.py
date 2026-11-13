import importlib.util
import tempfile
import unittest
from pathlib import Path
import zipfile

class ReleaseArchiveTests(unittest.TestCase):
 def module(self):
  path=Path(__file__).resolve().parents[1]/'scripts/build_release_archive.py'
  self.assertTrue(path.exists(), 'release archive builder missing')
  spec=importlib.util.spec_from_file_location('builder',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
 def test_exact_source_and_integrity_manifest(self):
  m=self.module()
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);(root/'jarvis').mkdir();(root/'jarvis/config.yaml').write_text('version: "1.2.3"\n');(root/'jarvis/app.py').write_text('print(1)\n')
   result=m.build(root,root/'out','a'*40,['jarvis'])
   self.assertEqual(result['packages'][0]['version'],'1.2.3')
   with zipfile.ZipFile(root/'out'/result['packages'][0]['file']) as z:self.assertIn('jarvis/app.py',z.namelist())
   self.assertEqual(len(result['packages'][0]['sha256']),64)
 def test_refuses_secret_file(self):
  m=self.module()
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);(r/'jarvis').mkdir();(r/'jarvis/config.yaml').write_text('version: "1.0.0"\n');(r/'jarvis/.env').write_text('SECRET=x')
   with self.assertRaises(ValueError):m.build(r,r/'out','a'*40,['jarvis'])
 def test_refuses_symlink(self):
  m=self.module()
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);(r/'jarvis').mkdir();(r/'jarvis/config.yaml').write_text('version: "1.0.0"\n');(r/'secret').write_text('secret');(r/'jarvis/link').symlink_to(r/'secret')
   with self.assertRaises(ValueError):m.build(r,r/'out','a'*40,['jarvis'])

 def test_refuses_hidden_parent_directory(self):
  m=self.module()
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);(r/'jarvis/.ssh').mkdir(parents=True);(r/'jarvis/config.yaml').write_text('version: "1.0.0"\n');(r/'jarvis/.ssh/id_rsa').write_text('secret')
   with self.assertRaises(ValueError):m.build(r,r/'out','a'*40,['jarvis'])

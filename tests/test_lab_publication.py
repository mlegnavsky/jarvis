import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

class PublicationTests(unittest.TestCase):
 def test_rejects_bad_checksum_without_publishing_catalog(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);src=r/'src';pub=r/'pub';rel=r/'release'
   (src/'testing/reports').mkdir(parents=True);rel.mkdir();pub.mkdir()
   (src/'testing/reports/heating-latest.json').write_text(json.dumps({'verified':True,'production_connected':False}))
   (rel/'x.zip').write_bytes(b'wrong')
   (rel/'release.json').write_text(json.dumps({'source_commit':'a'*40,'packages':[{'file':'x.zip','sha256':'0'*64}]}))
   out=subprocess.run([sys.executable,'scripts/publish_lab_snapshot.py','--source',str(src),'--public',str(pub),'--release',str(rel),'--commit','a'*40,'--run','test'],capture_output=True)
   self.assertNotEqual(out.returncode,0);self.assertIn(b'checksum mismatch',out.stderr);self.assertFalse((pub/'catalog.json').exists())

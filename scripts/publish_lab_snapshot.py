"""Publish only public release files; preserve all previous versions."""
import argparse
import datetime
import json
from pathlib import Path
import re
import shutil

def main():
 p=argparse.ArgumentParser()
 for field in ('source','public','release','commit','run'):p.add_argument('--'+field,required=True)
 a=p.parse_args()
 if not re.fullmatch('[a-f0-9]{40}',a.commit):raise ValueError('invalid commit')
 source=Path(a.source);public=Path(a.public);release=Path(a.release)
 manifest=json.loads((release/'release.json').read_text())
 if manifest['source_commit']!=a.commit:raise ValueError('commit mismatch')
 report=json.loads((source/'testing/reports/heating-latest.json').read_text())
 if report.get('verified') is not True or report.get('production_connected') is not False:raise ValueError('unverified simulation')
 dest=public/'releases'/a.commit;dest.mkdir(parents=True,exist_ok=True)
 import hashlib
 for item in manifest['packages']:
  name=item['file']
  if Path(name).name!=name or not name.endswith('.zip'):raise ValueError('invalid package filename')
  data=(release/name).read_bytes()
  if hashlib.sha256(data).hexdigest()!=item['sha256']:raise ValueError('checksum mismatch')
  target=dest/name
  if target.exists() and target.read_bytes()!=data:raise ValueError('immutable conflict')
  target.write_bytes(data)
 shutil.copyfile(release/'release.json',dest/'release.json')
 (dest/'heating-report.json').write_text(json.dumps(report,indent=2)+'\n')
 for name in ('index.html','portal.js'):shutil.copyfile(source/'testing/lab-public'/name,public/name)
 path=public/'catalog.json';catalog=json.loads(path.read_text()) if path.exists() else {'format':'jarvis-lab-catalog-v1','releases':[]}
 entry={**manifest,'verified_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'workflow_run':a.run,'checks':'tests_and_container_builds_passed'}
 catalog['releases']=[entry]+[x for x in catalog['releases'] if x['source_commit']!=a.commit]
 path.write_text(json.dumps(catalog,indent=2)+'\n')
if __name__=='__main__':main()

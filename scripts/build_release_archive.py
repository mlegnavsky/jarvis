"""Build auditable, immutable source packages. Never archive production data."""
import hashlib
import json
import re
from pathlib import Path
import zipfile

APPS=('jarvis','jarvis_updater')
def build(root, output, commit, apps=APPS):
 root=Path(root);output=Path(output)
 if not re.fullmatch(r'[0-9a-f]{40}',commit):raise ValueError('invalid source commit')
 packages=[];output.mkdir(parents=True,exist_ok=True)
 for app in apps:
  if app not in APPS:raise ValueError('invalid app')
  base=root/app
  version=re.search(r'^version:\s*[\"\']?([0-9]+\.[0-9]+\.[0-9]+)',(base/'config.yaml').read_text(),re.M)
  if not version:raise ValueError('invalid version')
  members=[]
  for p in sorted(base.rglob('*')):
   if p.is_symlink():raise ValueError('symlink forbidden')
   rel=p.relative_to(root)
   if '__pycache__' in rel.parts or p.suffix=='.pyc':continue
   if p.is_dir():continue
   if any(part.startswith('.') for part in rel.parts[:-1]) or (p.name.startswith('.') and p.name != '.dockerignore'):raise ValueError('hidden file forbidden: '+str(rel))
   if p.name.lower() in ('secrets.yaml','options.json','credentials.json') or p.suffix.lower() in ('.key','.pem','.sqlite','.db'):raise ValueError('private file forbidden: '+str(rel))
   members.append((str(rel),p.read_bytes()))
  filename=f'{app}-{version[1]}-{commit}.zip';target=output/filename
  # Reproducible metadata and sorted members; stage before exclusive final creation.
  import io
  buf=io.BytesIO()
  with zipfile.ZipFile(buf,'w',compression=zipfile.ZIP_DEFLATED) as z:
   for name,content in members:
    info=zipfile.ZipInfo(name,date_time=(2026,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16;z.writestr(info,content)
  data=buf.getvalue()
  if target.exists():
   if target.read_bytes()!=data:raise ValueError('immutable package conflict')
  else:
   with target.open('xb') as f:f.write(data)
  packages.append({'app':app,'version':version[1],'source_commit':commit,'file':filename,'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data),'kind':'source_package_not_built_image'})
 result={'format':'jarvis-release-v1','source_commit':commit,'packages':packages}
 (output/'release.json').write_text(json.dumps(result,indent=2)+'\n')
 return result

if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--commit',required=True);p.add_argument('--output',required=True);a=p.parse_args()
 print(json.dumps(build(Path(__file__).resolve().parents[1],a.output,a.commit),indent=2))

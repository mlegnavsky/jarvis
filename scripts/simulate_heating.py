"""Run real heating policy/adapter scenarios without production connections."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import os
ROOT=Path(__file__).resolve().parents[1]
def main():
 env=dict(os.environ,PYTHONPATH=str(ROOT/'managed_sources/solar_heating'))
 result=subprocess.run([sys.executable,'-m','unittest','discover','-s',str(ROOT/'managed_sources/solar_heating/tests'),'-q'],env=env,capture_output=True,text=True)
 files={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'managed_sources/solar_heating').glob('*.py')}
 report={'format':'jarvis-simulation-v1','production_connected':False,'source_sha256':files,'verified':result.returncode==0,'output':result.stdout+result.stderr}
 path=ROOT/'testing/reports/heating-latest.json';path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(report,indent=2)+'\n')
 print(report['output']);print('Simulation verified:',report['verified']);return result.returncode
if __name__=='__main__':raise SystemExit(main())

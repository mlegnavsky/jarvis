"""Prepare scoped live views and retire the old automatic grid-bias writer."""
import argparse
import json
from pathlib import Path
import sys
import yaml
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'managed_sources/spot_control'))
from sale_view import augment_spot,view

def main():
 p=argparse.ArgumentParser();p.add_argument('--spot',required=True);p.add_argument('--automations',required=True);p.add_argument('--out',required=True);a=p.parse_args()
 spot=yaml.safe_load(Path(a.spot).read_text());automations=yaml.safe_load(Path(a.automations).read_text())
 matches=[x for x in automations if x.get('id')=='jarvis_bezny_odber_0_w']
 if len(matches)>1:raise ValueError('Duplicate legacy writer; refusing blind overwrite')
 outputs={'spot-control-view.yaml':augment_spot(spot),'spot-sales-view.yaml':view(),'automations.yaml':[x for x in automations if x not in matches]}
 out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
 for name,body in outputs.items():(out/name).write_text(yaml.safe_dump(body,allow_unicode=True,sort_keys=False))
 print(json.dumps({n:(out/n).stat().st_size for n in outputs}))

if __name__=='__main__':main()

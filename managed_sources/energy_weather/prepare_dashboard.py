"""Prepare additive dashboard/config patches against fresh HA file copies."""
from pathlib import Path
import sys
import yaml
config, dashboard = map(Path, sys.argv[1:3])
s=config.read_text()
module='    - /local/jarvis-energy-weather.js?v=1.0.0\n'
if module not in s:
 s=s.replace('  extra_module_url:\n','  extra_module_url:\n'+module)
if '\njarvis_energy_weather:' not in s: s+='\njarvis_energy_weather:\n'
if '\nrecorder:' not in s: s+='\nrecorder:\n  exclude:\n    entities:\n      - sensor.jarvis_pocasi_zitenice\n'
config.with_suffix('.prepared.yaml').write_text(s)
d=yaml.safe_load(dashboard.read_text())
for v in d['views']:
 if v.get('path')=='energie':
  if not any('custom:jarvis-energy-weather' in str(section) for section in v.get('sections',[])):
   v['sections'].append({'type':'grid','column_span':3,'cards':[{'type':'custom:jarvis-energy-weather','mode':'energy','grid_options':{'columns':'full'}}]})
 if v.get('path')=='pocasi':
  if not any(c.get('type')=='custom:jarvis-energy-weather' for c in v['cards']):
   v['cards'].append({'type':'custom:jarvis-energy-weather','mode':'weather'})
  cards=v.pop('cards',None)
  if cards is not None:
   for card in cards: card['grid_options']={'columns':'full'}
   v.update(type='sections',max_columns=3,sections=[{'type':'grid','column_span':3,'cards':cards}])
dashboard.with_suffix('.prepared.yaml').write_text(yaml.safe_dump(d,allow_unicode=True,sort_keys=False,width=140))

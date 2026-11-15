"""Version static paths and touch the dashboard YAML without reserializing it."""
from pathlib import Path
import re
import yaml

BUILD='finance-20261115b'
ROOT=Path(__file__).resolve().parents[1]

def prepare(dashboard,view):
 if "!include 'spot-control-view.yaml'" not in dashboard:raise ValueError('Unknown dashboard include')
 config=yaml.safe_load(view)
 if config.get('path')!='spoty' or len(config.get('cards',[]))!=1 or config['cards'][0].get('type')!='iframe':raise ValueError('Unknown Spoty layout')
 config['cards'][0]['url']=f'/local/jarvis-spot-hub-{BUILD}.html'
 html=(ROOT/'managed_sources/spot_hub/index.html').read_text()
 html=re.sub(r'/local/jarvis-accounting\.js\?v=[^"<>]+',f'/local/jarvis-accounting-{BUILD}.js',html)
 html=re.sub(r'/local/jarvis-spot-hub\.js\?v=[^"<>]+',f'/local/jarvis-spot-hub-{BUILD}.js',html)
 html=html.replace('<head>','<head><meta name="jarvis-finance-build" content="'+BUILD+'">',1)
 marker=f'# Spot finance client: {BUILD}'
 return {'jarvis_workspace/hlavni-prehled.yaml':dashboard if marker in dashboard else dashboard.rstrip()+'\n\n'+marker+'\n',
  'jarvis_workspace/spot-control-view.yaml':yaml.safe_dump(config,allow_unicode=True,sort_keys=False),
  f'www/jarvis-spot-hub-{BUILD}.html':html,
  f'www/jarvis-spot-hub-{BUILD}.js':(ROOT/'managed_sources/spot_hub/hub.js').read_text(),
  f'www/jarvis-accounting-{BUILD}.js':(ROOT/'managed_sources/spot_hub/accounting.js').read_text()}

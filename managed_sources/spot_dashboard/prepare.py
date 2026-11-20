"""Add the Spoty view and module to freshly read files; no inverter writes."""
from pathlib import Path
import sys,yaml
source,module,output=map(Path,sys.argv[1:])
assert module.name == 'jarvis-energy-weather.js', 'Use the entry point configured in frontend.extra_module_url, not the unverified v2 resource'
s=source.read_text()
assert '\n  path: spoty\n' not in s, 'Spoty already exists; review current view before editing'
view='''\n- title: Spoty
  path: spoty
  icon: mdi:lightning-bolt
  type: panel
  cards:
  - type: custom:jarvis-spot-dashboard
'''
new=s.rstrip()+view+'\n'
yaml.compose(new)
output.write_text(new)
js=module.read_text();assert 'class JarvisSpotDashboard' not in js
output.with_suffix('.js').write_text(js+'\n'+Path(__file__).with_name('card.js').read_text())
print('Prepared one additional view; unchanged existing dashboard prefix and JS prefix.')

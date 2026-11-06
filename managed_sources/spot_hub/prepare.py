"""A frontend-only Spoty replacement; all previous native controls stay available."""
import json,yaml,base64,copy
from pathlib import Path

def with_temperatures(house):
 house=copy.deepcopy(house)
 prefix='data:image/svg+xml;base64,'
 if house.get('image','').startswith(prefix):
  svg=base64.b64decode(house['image'][len(prefix):]).decode()
  svg=svg.replace('x="723" y="24" width="255" height="126"','x="723" y="24" width="255" height="190"')
  house['image']=prefix+base64.b64encode(svg.encode()).decode()
 for entity,top in [('sensor.inverter_battery_temperature','32%'),('sensor.inverter_temperature','38%')]:
  if not any(e.get('entity')==entity for e in house.get('elements',[])):
   house.setdefault('elements',[]).append({'type':'state-label','entity':entity,'style':{'left':'85%','top':top,'font-size':'10px'}})
 return house

def prepare(spot):
 old=yaml.safe_load(spot);left=old['sections'][0]['cards'];right=old['sections'][1]['cards']
 if old.get('path')!='spoty' or right[0].get('type')!='picture-elements':raise ValueError('Unexpected native Spoty structure')
 advanced=[x for x in left if x.get('type') not in ('conditional',) and x.get('name') not in ('Automatický prodej','Vlastní prodej')]
 config={'house':with_temperatures(right[0]),'advanced':advanced,'source':'existing_native_spot_view'}
 view={'title':'Spoty','path':'spoty','icon':old.get('icon','mdi:lightning-bolt'),'type':'panel','cards':[{'type':'iframe','url':'/local/jarvis-spot-hub.html?v=1.2.2','aspect_ratio':'85%'}]}
 return yaml.safe_dump(view,allow_unicode=True,sort_keys=False),json.dumps(config,ensure_ascii=False,separators=(',',':'))
if __name__=='__main__':
 import sys
 view,config=prepare(Path(sys.argv[1]).read_text());out=Path(sys.argv[2]);out.mkdir(exist_ok=True,parents=True)
 (out/'spot-control-view.yaml').write_text(view);(out/'config.json').write_text(config)

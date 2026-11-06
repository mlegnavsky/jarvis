"""A frontend-only Spoty replacement; all previous native controls stay available."""
import json,yaml
from pathlib import Path

def prepare(spot):
 old=yaml.safe_load(spot);left=old['sections'][0]['cards'];right=old['sections'][1]['cards']
 if old.get('path')!='spoty' or right[0].get('type')!='picture-elements':raise ValueError('Unexpected native Spoty structure')
 advanced=[x for x in left if x.get('type') not in ('conditional',) and x.get('name') not in ('Automatický prodej','Vlastní prodej')]
 config={'house':right[0],'advanced':advanced,'source':'existing_native_spot_view'}
 view={'title':'Spoty','path':'spoty','icon':old.get('icon','mdi:lightning-bolt'),'type':'panel','cards':[{'type':'iframe','url':'/local/jarvis-spot-hub.html?v=1.0.1','aspect_ratio':'85%'}]}
 return yaml.safe_dump(view,allow_unicode=True,sort_keys=False),json.dumps(config,ensure_ascii=False,separators=(',',':'))
if __name__=='__main__':
 import sys
 view,config=prepare(Path(sys.argv[1]).read_text());out=Path(sys.argv[2]);out.mkdir(exist_ok=True,parents=True)
 (out/'spot-control-view.yaml').write_text(view);(out/'config.json').write_text(config)

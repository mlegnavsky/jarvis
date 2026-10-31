"""Build dashboard includes from a fresh dashboard and the current DEYE inventory."""
from pathlib import Path
import copy,json,yaml,sys
from catalogue import catalogue,card
ROOT=Path(__file__).parent
class Include(str):pass
def dump_include(dumper,value):return dumper.represent_scalar('!include',str(value))
yaml.SafeDumper.add_representer(Include,dump_include)

def build(d,states):
 entries=catalogue(states)
 view=copy.deepcopy(next(v for v in d['views'] if v.get('path')=='deye-baterie'))
 def md(text):return {'type':'markdown','content':text}
 potential=md((ROOT/'potential.jinja').read_text())
 pv=card([e for e in entries if e['id'] in ['sensor.inverter_pv1_voltage','sensor.inverter_pv1_current','sensor.inverter_pv1_power','sensor.inverter_pv2_voltage','sensor.inverter_pv2_current','sensor.inverter_pv2_power','sensor.inverter_pv_power']], 'Panely · skutečně odebíraný výkon')
 pv['content']+='\n\n**Kontrola U × I:**\n\nPV1: {% if is_number(states("sensor.inverter_pv1_voltage")) and is_number(states("sensor.inverter_pv1_current")) %}{{ (states("sensor.inverter_pv1_voltage")|float * states("sensor.inverter_pv1_current")|float)|round(0) }} W{% else %}Nedostupné{% endif %}\n\nPV2: {% if is_number(states("sensor.inverter_pv2_voltage")) and is_number(states("sensor.inverter_pv2_current")) %}{{ (states("sensor.inverter_pv2_voltage")|float * states("sensor.inverter_pv2_current")|float)|round(0) }} W{% else %}Nedostupné{% endif %}\n\nSoučin se může mírně lišit od výkonu hlášeného měničem kvůli zaokrouhlení a času vzorkování.'
 view['sections'].insert(1,{'type':'grid','column_span':2,'cards':[pv]})
 view['sections'].insert(2,{'type':'grid','cards':[potential]})
 view['sections'][0]['cards'].append({'type':'button','name':'Všechny údaje a měnitelná nastavení · 203 položek','icon':'mdi:format-list-bulleted','tap_action':{'action':'navigate','navigation_path':'/hlavni-prehled/deye-vsechny-udaje'}})
 # Give wide tables enough width in native sections.
 for section in view['sections']:
  for c in section['cards']:
   c.setdefault('grid_options',{'columns':'full','rows':'auto'})
 detail={'title':'DEYE · všechny údaje','path':'deye-vsechny-udaje','icon':'mdi:format-list-bulleted','subview':True,'type':'sections','max_columns':2,'sections':[]}
 intro='## Všechny údaje DEYE a baterie\n\nKatalog **'+str(len(entries))+' položek**: '+str(sum(not e['writable'] for e in entries))+' měření a stavů, '+str(sum(e['writable'] for e in entries))+' položek, pro které integrace vystavuje zápis.\n\nČervené **„můžeme změnit“** znamená dostupnou možnost zápisu v integraci; přijetí měničem zatím nebylo prakticky testováno. Nedostupné hodnoty jsou označené samostatně. Tato stránka je pouze pro čtení.\n\nÚdaje se aktualizují z Greenu. Některé hodnoty jsou dopočítané integrací. Síťové ochrany, BMS a ekvalizace jsou servisní nastavení; zobrazení parametru nepotvrzuje, že se používá v aktuálním režimu.'
 detail['sections'].append({'type':'grid','column_span':2,'cards':[md(intro)]})
 for group in dict.fromkeys(e['group'] for e in entries):
  selected=[e for e in entries if e['group']==group]
  # Bounded table height for mobile scrolling, preserve every item exactly once.
  for start in range(0,len(selected),18):
   c=card(selected[start:start+18],group+(' · pokračování' if start else ''))
   c['grid_options']={'columns':'full','rows':'auto'}
   detail['sections'].append({'type':'grid','cards':[c]})
 detail['sections'].append({'type':'grid','column_span':2,'cards':[md('### Co v připojení chybí\n\nNapětí jednotlivých článků, rozdíly mezi články, samostatné údaje bateriových modulů a podrobnosti balancování BMS zde nejsou dostupné.\n\nSamostatná obnovitelná záloha kompletního nastavení měniče zatím není vytvořená. Předchozí verze dashboardu je uchovaná nasazovacím systémem.')]})
 d=copy.deepcopy(d);d['views']=[v for v in d['views'] if v.get('path')!='deye-vsechny-udaje']
 index=next(i for i,v in enumerate(d['views']) if v.get('path')=='deye-baterie')
 d['views'][index]=Include('deye-baterie.yaml');d['views'].insert(index+1,Include('deye-vsechny-udaje.yaml'))
 return d,view,detail,entries
if __name__=='__main__':
 d,v,detail,entries=build(yaml.safe_load(Path(sys.argv[1]).read_text()),json.loads(Path(sys.argv[2]).read_text()))
 out=Path(sys.argv[3]);out.mkdir(exist_ok=True)
 for name,data in [('hlavni-prehled.yaml',d),('deye-baterie.yaml',v),('deye-vsechny-udaje.yaml',detail)]:
  (out/name).write_text(yaml.safe_dump(data,allow_unicode=True,sort_keys=False,width=140))
 (ROOT/'entities.json').write_text(json.dumps([{'entity_id':e['id']} for e in entries],ensure_ascii=False,indent=2)+'\n')
 print('Generated',len(entries),'items; file sizes:',[(p.name,p.stat().st_size) for p in out.glob('*.yaml')])

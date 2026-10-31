"""Patch fresh floorplan while preserving all !include references and actions."""
from copy import deepcopy
import yaml
class Include(str):pass
class Loader(yaml.SafeLoader):pass
class Dumper(yaml.SafeDumper):pass
Loader.add_constructor('!include',lambda l,n:Include(l.construct_scalar(n)))
Dumper.add_representer(Include,lambda d,v:d.represent_scalar('!include',str(v)))
BATTERIES={'switch.aqara_retrofit_valves_t1':'sensor.aqara_retrofit_valves_t1_baterie','lock.vstup_zamek_vchod':'sensor.vstup_zamek_vchod_baterie','sensor.aqara_temp_humidity_sensor_t1_teplota':'sensor.aqara_temp_humidity_sensor_t1_baterie','sensor.aqara_temp_humidity_sensor_t1_vlhkost_vzduchu':'sensor.aqara_temp_humidity_sensor_t1_baterie','valve.aqara_retrofit_valves_t1':'sensor.aqara_retrofit_valves_t1_baterie'}
HEAT={'switch.aqara_smart_plug_eu':'sensor.jarvis_topeni_child','switch.aqara_smart_plug_eu_2':'sensor.jarvis_topeni_living'}
def patch(d):
 def walk(v):
  if isinstance(v,dict):
   if v.get('type') in ('state-icon','state-label') and v.get('entity') in BATTERIES|HEAT:
    entity=v['entity'];label=v['type']=='state-label';v['type']='custom:jarvis-device-status';v['kind']='label' if label else 'lock' if entity.startswith('lock.') else 'icon'
    if entity in BATTERIES:v['battery_entity']=BATTERIES[entity]
    if entity in HEAT:v['heating_entity']=HEAT[entity]
   if v.get('type')=='markdown' and isinstance(v.get('content'),str):v['content']=v['content'].replace('Ruční vypnutí vrací automatiku. Při dostatku slunce se může po pauze opět zapnout.','Ruční vypnutí uzamkne daný radiátor do dalšího ručního zapnutí nebo do půlnoci (Europe/Prague). Potom se vrací automatika.').replace('Režim „Ze soláru“ označuje řízení podle výroby, nikoli záruku nulového odběru baterie/sítě.','Označení zdroje vychází z výroby, spotřeby a směru baterie; nabitá baterie je jen povolení výjimky, nikoli důkaz vybíjení.')
   if v.get('type')=='markdown' and 'Dům → baterie' in v.get('content','') and 'inverter_power_losses' not in v['content']:
    v['content']+="\n\n{% set l=states('sensor.inverter_power_losses') %}{% if is_number(l) %}**Ztráty měniče: {{ l|float|round(0)|int }} W**{% else %}Ztráty měniče: nedostupné{% endif %}\n\nSolár a baterie mohou napájet dům současně. Rozdíl vstupů a spotřeby zahrnuje ztráty měniče; při různých časech měření nemusí bilance přesně souhlasit."
   for x in list(v.values()):walk(x)
  elif isinstance(v,list):
   for x in v:walk(x)
 walk(d)
 for v in d['views']:
  if isinstance(v,dict) and v.get('path')=='domov':
   cards=v['sections'][1]['cards']
   if not any(c.get('type')=='custom:jarvis-battery-overview' for c in cards):cards.insert(1,{'type':'custom:jarvis-battery-overview'})
 return d
if __name__=='__main__':
 import sys
 from pathlib import Path
 p=Path(sys.argv[1]);d=yaml.load(p.read_text(),Loader=Loader);p.with_suffix('.status.yaml').write_text(yaml.dump(patch(d),Dumper=Dumper,allow_unicode=True,sort_keys=False,width=140))

"""Add live heating labels and an explicit automation overview; preserve all views."""
import sys
from pathlib import Path
import yaml

def patch(d):
 def walk(value):
  if isinstance(value,dict):
   if value.get('type')=='picture-elements':
    elements=value.get('elements',[])
    for room,entity in [('child','switch.aqara_smart_plug_eu'),('living','switch.aqara_smart_plug_eu_2')]:
     icon=next((e for e in elements if e.get('type')=='state-icon' and e.get('entity')==entity),None)
     sensor='sensor.jarvis_topeni_'+room
     if icon and not any(e.get('entity')==sensor for e in elements):
      style=icon['style'];top=float(style['top'].rstrip('%'));left=style['left']
      elements.append({'type':'state-label','entity':sensor,'title':'Topení – aktuální režim a důvod','tap_action':{'action':'more-info'},'style':{'left':left,'top':str(top+6)+'%','color':'#fff','background':'rgba(3,19,39,.94)','border':'1px solid #e4ad46','border-radius':'8px','padding':'3px 7px','font-size':'12px','max-width':'170px','text-align':'center'}})
   for item in list(value.values()):walk(item)
  elif isinstance(value,list):
   for item in list(value):walk(item)
 walk(d)
 for view in d['views']:
  if view.get('path')=='automatizace':
   view['cards']=[{'type':'entities','title':'Solární topení','show_header_toggle':False,'entities':[
    {'entity':'automation.jarvis_solarni_topeni','name':'Automatické řízení topení'},
    {'entity':'sensor.jarvis_topeni_child','name':'Dětský pokoj – režim'},
    {'entity':'sensor.jarvis_topeni_living','name':'Obývák – režim'},
    {'entity':'sensor.jarvis_topeni_solar_prumer','name':'Výroba – průměr 5 minut'},
    {'entity':'sensor.aqara_temp_humidity_sensor_t1_teplota','name':'Společná řídicí teplota'},
    {'entity':'sensor.inverter_battery','name':'Nabití baterie'},
    {'entity':'switch.aqara_smart_plug_eu','name':'Dětský pokoj – ručně zapnout/vypnout'},
    {'entity':'switch.aqara_smart_plug_eu_2','name':'Obývák – ručně zapnout/vypnout'}]},
    {'type':'markdown','title':'Jak topení pracuje','content':'**Automatika:** pod 22 °C zapíná podle pětiminutového průměru výroby. Dětský pokoj 1 200 / 1 000 W; obývák 3 500 / 3 100 W. Vypíná při 23,5 °C. Po vypnutí automatická pauza 5 minut.\n\n**Nabitá baterie:** výjimka od 90 %, končí pod 85 %.\n\n**Ručně:** zapnutí radiátoru obejde solární podmínku, končí při 23,5 °C nebo baterii 50 %. Ruční vypnutí vrací automatiku. Při dostatku slunce se může po pauze opět zapnout.\n\n**Ochrana baterie:** při souvislém vybíjení nad 300 W odpojí automatický obývák po 2 minutách, dětský pokoj po dalších 2 minutách. Před zapnutím kontroluje volný výkon. Režim „Ze soláru“ označuje řízení podle výroby, nikoli záruku nulového odběru baterie/sítě.'},
    {'type':'entities','title':'Hlas – původní záložní automatizace','show_header_toggle':False,'entities':[
     {'entity':'automation.stiseni_apple_tv_pri_komunikacis_ai','name':'Záloha – stišení HomePodu'},
     {'entity':'automation.hlasitost_podomluveni_s_ai_se_vrati_na_45','name':'Záloha – obnovení hlasitosti'}]},
    {'type':'markdown','content':'**Hlavní hlasový výstup řídí nový adaptér.** Tyto dvě původní automatizace mají podmínku, která je při aktivním adaptéru blokuje. Jejich přepínač proto sám o sobě neznamená, že právě ovládají hlasitost. Běžné odpovědi mají nastaveno 35 %.'}]
   view.pop('sections',None);view.pop('max_columns',None);view['type']='masonry'
 return d
if __name__=='__main__':
 p=Path(sys.argv[1]);p.with_suffix('.prepared.yaml').write_text(yaml.safe_dump(patch(yaml.safe_load(p.read_text())),allow_unicode=True,sort_keys=False,width=140))

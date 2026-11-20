"""Readable Czech catalogue with category navigation; all settings remain read-only."""
from pathlib import Path
import base64,copy,json,sys,yaml
from catalogue import catalogue,card
from extend import Include
ROOT=Path(__file__).parent

def banner():
 svg='''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="250" viewBox="0 0 1200 250"><defs><linearGradient id="g" x2="1" y2="1"><stop stop-color="#112d45"/><stop offset="1" stop-color="#087c85"/></linearGradient></defs><rect width="1200" height="250" rx="26" fill="url(#g)"/><circle cx="105" cy="65" r="28" fill="#ffd365"/><path d="M35 160L132 94L229 160V222H35Z" fill="#e6f2f5"/><path d="M89 148H197L168 202H60Z" fill="#16547c" stroke="#75daed" stroke-width="3"/><path d="M100 148L71 202M124 148L95 202M148 148L119 202M172 148L143 202M79 166H187M69 185H177" stroke="#75daed" stroke-width="2"/><rect x="250" y="144" width="55" height="77" rx="8" fill="#e6f2f5"/><rect x="264" y="135" width="27" height="9" rx="3" fill="#e6f2f5"/><rect x="260" y="170" width="35" height="40" rx="3" fill="#34d399"/><g font-family="sans-serif" fill="white"><text x="350" y="70" font-size="40" font-weight="700">Vaše elektrárna srozumitelně</text><text x="352" y="112" font-size="22">22 panelů • 9,9 kWp • jihovýchod • sklon 45°</text><text x="352" y="148" font-size="20">Dvě pole po 11 panelech • baterie • dům • síť</text></g><rect x="352" y="177" width="310" height="46" rx="15" fill="#d4f5df"/><circle cx="379" cy="200" r="9" fill="#16803c"/><text x="400" y="207" font-family="sans-serif" font-size="20" fill="#166534">Zelená = můžeme změnit</text><rect x="680" y="177" width="345" height="46" rx="15" fill="#fde2e2"/><circle cx="707" cy="200" r="9" fill="#c62828"/><text x="729" y="207" font-family="sans-serif" font-size="20" fill="#991b1b">Červená = nelze měnit</text></svg>'''
 return {'type':'picture','image':'data:image/svg+xml;base64,'+base64.b64encode(svg.encode()).decode(),'tap_action':{'action':'none'},'grid_options':{'columns':'full','rows':'auto'}}
def md(s):return {'type':'markdown','content':s,'grid_options':{'columns':'full','rows':'auto'}}

def build(main,overview,states):
 entries=catalogue(states);groups=list(dict.fromkeys(e['group'] for e in entries))
 icons=['mdi:battery-heart','mdi:battery-charging','mdi:solar-power','mdi:transmission-tower','mdi:home-lightning-bolt','mdi:sine-wave','mdi:flash','mdi:engine','mdi:alert-circle-outline','mdi:cog','mdi:clock-outline']
 files={};category_views=[]
 menu={'title':'DEYE · všechny údaje','path':'deye-vsechny-udaje','icon':'mdi:view-dashboard','subview':True,'type':'sections','max_columns':2,'sections':[{'type':'grid','column_span':2,'cards':[banner(),md('## Vyberte si, co chcete prohlédnout\n\n🟢 **Zelená: můžeme změnit** – integrace nabízí zápis.\n\n🔴 **Červená: nelze měnit** – jde o měření, nebo je ovládací položka právě nedostupná. Červená zde **neznamená poruchu**.\n\nU každé hodnoty najdete vysvětlení **„K čemu to je“**. Přehled ukazuje všech **203 položek**; neobsahuje přepínače ani tlačítka, která by měnila měnič. Přijetí zápisu měničem ještě nebylo prakticky ověřeno.')]}]}
 for index,group in enumerate(groups):
  selected=[e for e in entries if e['group']==group];slug='deye-skupina-'+str(index+1);filename=slug+'.yaml';icon=next((v for k,v in [('Baterie','mdi:battery-charging'),('Solární','mdi:solar-power'),('Distribuční','mdi:transmission-tower'),('Dům','mdi:home-lightning-bolt'),('Výstup','mdi:sine-wave'),('Měření','mdi:current-ac'),('Generátor','mdi:engine'),('Časové','mdi:clock-outline'),('Diagnostika','mdi:heart-pulse')] if group.startswith(k)),'mdi:cog')
  heading=group.replace(' · ',' — ')
  button={'type':'button','name':heading+' · '+str(len(selected))+' údajů','icon':icon,'show_state':False,'tap_action':{'action':'navigate','navigation_path':'/hlavni-prehled/'+slug},'grid_options':{'columns':'full','rows':2}}
  menu['sections'].append({'type':'grid','cards':[button,md('**'+('Nastavitelné parametry' if all(e['writable'] for e in selected) else 'Měřené hodnoty a provozní stavy')+'**\n\n'+('Zelené označení ukazuje dostupnou možnost změny; nedostupné položky zůstávají červené.' if all(e['writable'] for e in selected) else 'Tyto hodnoty pouze sledujeme. Mění se podle skutečného provozu zařízení.'))]})
  view={'title':heading,'path':slug,'icon':icon,'subview':True,'type':'sections','max_columns':2,'sections':[{'type':'grid','column_span':2,'cards':[{'type':'heading','heading':heading,'icon':icon},md('🟢 Můžeme změnit · 🔴 Nelze měnit. Barva vyjadřuje možnost změny, nikoli stav zařízení.'),{'type':'button','name':'Zpět na všechny oblasti','icon':'mdi:arrow-left','tap_action':{'action':'navigate','navigation_path':'/hlavni-prehled/deye-vsechny-udaje'}}]}]}
  for e in selected:
   c=card([e],'');c['content']=c['content'].replace('\n## \n','\n');c['grid_options']={'columns':'full','rows':'auto'}
   view['sections'].append({'type':'grid','cards':[c]})
  files[filename]=view;category_views.append(Include(filename))
 glossary=md('## Slovníček bez technické hatmatilky\n\n| Výraz | Co znamená |\n|:--|:--|\n| W / kW | Výkon právě teď; 1 kW = 1 000 W. |\n| kWh | Množství energie. Spotřebič o výkonu 1 kW za hodinu spotřebuje 1 kWh. |\n| V / A | Napětí / proud. U panelů V × A dává skutečně odebíraný výkon ve W. |\n| SOC | Kolik procent energie zbývá v baterii. |\n| SOH | Hlášená kondice baterie vůči nové. |\n| PV1 / PV2 | Dvě samostatně sledovaná pole po 11 solárních panelech. |\n| MPPT | Hledání pracovního bodu, ve kterém panely odevzdají nejvyšší výkon. |\n| BMS | Elektronika baterie, která hlídá její provoz. |\n| L1 / L2 / L3 | Tři elektrické fáze. |\n| CT | Proudový snímač pro měření toku elektřiny. |\n| UPS | Záložní výstup pro napájení při výpadku sítě. |\n| Export / import | Dodávka do sítě / odběr ze sítě. |\n| SmartLoad | Řízená zátěž na pomocném výstupu měniče. |\n| Ekvalizace | Vyrovnávací nabíjení; přítomnost parametru neznamená použití u lithiové baterie. |\n| Absorpce / Float | Dokončovací / udržovací fáze nabíjení. |\n\n**Servisní hodnoty:** síťové ochrany, napětí baterie a typ BMS měníme až po ověření správných parametrů. Zelená barva sama o sobě není doporučení hodnotu změnit.')
 menu['sections'].append({'type':'grid','column_span':2,'cards':[glossary]});files['deye-vsechny-udaje.yaml']=menu
 overview=copy.deepcopy(overview);overview['sections'][0]['cards'].insert(0,banner())
 overview['sections'][0]['cards'].append(md('### Jak se v přehledu vyznat\n\n☀️ **Panely** vyrábějí · 🔋 **Baterie** ukládá · 🏠 **Dům** spotřebovává · ⚡ **Síť** dodává nebo odebírá.\n\n🟢 **Můžeme změnit** · 🔴 **Nelze měnit**. Podrobné vysvětlení každého parametru najdete přes tlačítko **Všechny údaje**.'))
 for section in overview['sections']:
  for c in section['cards']:
   if c.get('type')=='markdown' and 'Chybí sklon a orientace' in c.get('content',''):
    c['content']=c['content'].replace('**Chybí sklon a orientace panelů.** Proto zatím nelze poctivě vyčíslit nevyužitý výkon ani dnešní nevyužitou energii.','**Rozložení panelů máme potvrzené:** 22 × 450 W = 9,9 kWp, jihovýchod, sklon 45°, dvě pole po 11 panelech (2 × 4,95 kWp).\n\n**Výpočet nevyužité výroby ještě není aktivní.** Je nutné doplnit model záření pro tuto nakloněnou plochu a porovnávat stejně dlouhé časové intervaly. Níže uvedené skutečné výkony již sledujeme.')
 files['deye-baterie.yaml']=overview
 main=copy.deepcopy(main)
 main['views']=[v for v in main['views'] if not isinstance(v,Include) or not str(v).startswith('deye-skupina-')]
 main['views'].extend(category_views);files['hlavni-prehled.yaml']=main
 return files
if __name__=='__main__':
 class Loader(yaml.SafeLoader):pass
 Loader.add_constructor('!include',lambda loader,node:Include(loader.construct_scalar(node)))
 main=yaml.load(Path(sys.argv[1]).read_text(),Loader=Loader);overview=yaml.safe_load(Path(sys.argv[2]).read_text());states=json.loads((ROOT/'entities.json').read_text())
 out=Path(sys.argv[3]);out.mkdir(exist_ok=True)
 for name,data in build(main,overview,states).items():(out/name).write_text(yaml.safe_dump(data,allow_unicode=True,sort_keys=False,width=140))
 print('Written',len(list(out.glob('*.yaml'))),'dashboard files')

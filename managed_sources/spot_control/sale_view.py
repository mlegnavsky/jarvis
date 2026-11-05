"""Native mobile form: navigation is inert; Start is an explicit separate action."""
def md(content):return {'type':'markdown','content':content}
def tile(name,icon,service,color):
 return {'type':'tile','entity':'sensor.jarvis_energy_sales','name':name,'icon':icon,'color':color,'hide_state':True,
  'tap_action':{'action':'perform-action','perform_action':'jarvis_spot_control.'+service},
  'icon_tap_action':{'action':'perform-action','perform_action':'jarvis_spot_control.'+service}}
def conditional(phase,card):return {'type':'conditional','conditions':[{'condition':'state','entity':'sensor.jarvis_energy_sales','state':phase}], 'card':card}
def summary_cards():
 return [md('''## Prodej elektřiny
{% set p=state_attr('sensor.jarvis_energy_sales','price') %}
{% if p %}**Výkup po poplatku: {{ p.net | round(3) }} Kč/kWh**{% else %}Výkupní cena není dostupná.{% endif %}

**{{ state_attr('sensor.jarvis_energy_sales','reason') or 'Čekám na měření.' }}**

{% if state_attr('sensor.jarvis_energy_sales','error') %}⚠️ {{ state_attr('sensor.jarvis_energy_sales','error') }}{% endif %}

Rezerva pro prodej **60 %** · maximální provozní strop **9,3 kW**.

Automatický prodej je nyní omezen na úvodních **3 kW**. Baterie se automaticky neprodává, dokud není ověřeno její časové ukončení.
'''),
 {'type':'tile','entity':'switch.jarvis_sale_automatic','name':'Automatický prodej','icon':'mdi:solar-power','color':'green'},
 {'type':'tile','entity':'sensor.jarvis_energy_sales','name':'Vlastní prodej','icon':'mdi:transmission-tower-export','color':'green','hide_state':True,
  'tap_action':{'action':'navigate','navigation_path':'/hlavni-prehled/vlastni-prodej'},
  'icon_tap_action':{'action':'navigate','navigation_path':'/hlavni-prehled/vlastni-prodej'}},
 conditional('running',tile('Prodej běží · zastavit','mdi:transmission-tower-export','stop_sale','blue'))]

def view():
 cards=[md('''## Vlastní prodej
{% set p=state_attr('sensor.jarvis_energy_sales','price') %}
**Výkup po odečtení 0,30 Kč/kWh:** {% if p %}{{ p.net | round(3) }} Kč/kWh{% else %}nedostupný{% endif %}

Nastav maximální dodávku do sítě a délku. Skutečný výkon závisí na dostupné energii. Baterie zůstane nejméně na 60 %.
'''),
 {'type':'entities','title':'Nastavení vlastního prodeje','show_header_toggle':False,'entities':[
  {'entity':'select.jarvis_sale_source','name':'Co prodávat'},
  {'entity':'number.jarvis_sale_power_w','name':'Maximální výkon do sítě (W)'},
  {'entity':'number.jarvis_sale_minutes','name':'Délka (minuty)'}]},
 {'type':'conditional','conditions':[{'condition':'state','entity':'sensor.jarvis_energy_sales','state':'idle'},
  {'condition':'state','entity':'binary_sensor.jarvis_sales_ready','state':'on'}],
  'card':tile('Spustit prodej','mdi:play-circle','start_sale','green')},
 conditional('starting',md('🟠 **Připravuji prodej · čekám na potvrzení měniče.**')),
 conditional('awaiting_power',md('🟠 **Prodej povolen · čekám na naměřenou dodávku.**')),
 conditional('running',tile('Prodej běží','mdi:transmission-tower-export','stop_sale','blue')),
 conditional('stopping',md('🟠 **Ukončuji prodej · ověřuji návrat bez přetoků.**')),
 tile('Zastavit prodej i automatiku','mdi:stop-circle','stop_sale','red'),
 md('''### Průběh
**{{ state_attr('sensor.jarvis_energy_sales','reason') or 'Čekám na řídicí službu.' }}**

{% set end=state_attr('sensor.jarvis_energy_sales','deadline') %}{% if end %}Konec: **{{ end | timestamp_custom('%H:%M:%S', true) }}**{% endif %}

{% if state_attr('sensor.jarvis_energy_sales','error') %}⚠️ {{ state_attr('sensor.jarvis_energy_sales','error') }}{% endif %}

Časové ukončení vyžaduje běžící Home Assistant a spojení s měničem. Při výpadku řízení může dodávka z panelů pokračovat pod nativním výkonovým limitem. Prodej z baterie se zpřístupní po ověření jeho ochran.
'''),
 md('''### Historie
Měření se ukládá do soukromého energetického archivu. Rozhodnutí a změny prodeje se zaznamenávají ihned a trvale.

Stav archivu: **{{ states('sensor.jarvis_energy_archive') }}**.

Výkupní částka v Jarvisu je provozní odhad. Konečné vyúčtování vystavuje EnerSpot z distribučních dat.
''')]
 return {'title':'Vlastní prodej','path':'vlastni-prodej','subview':True,'back_path':'/hlavni-prehled/spoty','type':'sections','max_columns':1,'sections':[{'type':'grid','cards':cards}]}

def augment_spot(spot):
 """Upgrade the known native layout without touching the household diagram."""
 import copy
 result=copy.deepcopy(spot)
 left=result['sections'][0]['cards'];right=result['sections'][1]['cards']
 if any(c.get('name')=='Vlastní prodej' for c in left):return result
 if len(left)!=5 or len(right)!=5:raise ValueError('Spot dashboard layout changed; refusing blind overwrite')
 result['sections'][0]['cards']=summary_cards()+[left[1],left[3],left[4]]
 right[1]={'type':'grid','columns':2,'square':False,'cards':[
  md('### Nákup · ČEZ\n## 5 Kč/kWh\nVčetně poplatků · sazba zadaná majitelem'),
  md("### Výkup · EnerSpot\n{% set p=state_attr('sensor.jarvis_energy_sales','price') %}\n## {{ p.net | round(3) if p else '—' }} Kč/kWh\nPo odečtení 0,30 Kč/kWh · konečné vyúčtování dle smlouvy")]}
 right[4]=md('### Řízení a historie\nAutomatika prodává dostupné přebytky panelů při kladné ceně. Prodej z baterie se zpřístupní po ověření ochran. Rezerva pro prodej je nejméně **60 %**, celková dodávka nejvýše **9,3 kW**.\n\nRozhodnutí a změny se zaznamenávají trvale. Stav archivu: **{{ states("sensor.jarvis_energy_archive") }}**.')
 for section in result['sections']:
  for card in section['cards']:card['grid_options']={'columns':'full'}
 return result

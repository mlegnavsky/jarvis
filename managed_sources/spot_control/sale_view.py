"""Native mobile form: navigation is inert; Start is an explicit separate action."""
def md(content):return {'type':'markdown','content':content}
def grid_target_card():
 action={'action':'perform-action','perform_action':'automation.trigger',
         'target':{'entity_id':'automation.jarvis_bezny_odber_0_w'},'data':{'skip_condition':False}}
 return {'type':'vertical-stack','grid_options':{'columns':'full'},'cards':[
  {'type':'tile','entity':'number.inverter_zero_export_power','name':'Nastavit všude 1 W',
   'icon':'mdi:transmission-tower','color':'blue','hide_state':True,
   'tap_action':action,'icon_tap_action':dict(action),'hold_action':{'action':'none'}},
  md("""{% set target=state_attr('sensor.jarvis_energy_sales','grid_target_w') %}
{% set program=state_attr('sensor.jarvis_energy_sales','native_program') or {} %}
{% set actual=program.get('register_104') %}
**Požadováno: {{ target if target is not none else '—' }} W · měnič: {{ actual if actual is not none else '—' }} W**
{% if actual==1 %}Měnič při posledním načtení potvrdil 1 W.{% elif actual is not none %}Měnič zatím 1 W nepotvrdil.{% else %}Čekám na čtení měniče.{% endif %}
Tlačítko obnoví společné nastavení 1 W při běžném provozu. Stav se aktualizuje po načtení měniče.
""")]}
def verification_card():
 return md("### Stav ověřování\n{% set s=state_attr('sensor.jarvis_energy_sales','settings') or {} %}\n{% set c=s.get('command',{}) %}\n{% set t=state_attr('sensor.jarvis_energy_sales','native_test') or {} %}\n{% if t %}\n**Test baterie: {{ {'preparing':'příprava','armed':'čekám na začátek','measuring':'měřím průběh','expiry_observed':'nativní konec ověřen','stopping':'ukončuji a vracím nastavení'}.get(t.get('phase'),'ověřování') }} · nejvýše 500 W**\nZačátek: **{{ t.get('start') | timestamp_custom('%H:%M:%S',true) }}**, konec: **{{ t.get('end') | timestamp_custom('%H:%M:%S',true) }}**.\nRezerva při testu **{{ t.get('minimum_soc',95) }} %**.\n{% if t.get(\'selling_first\') %}Doběh regulace sleduji nejvýše 60 s po konci při stejném výkonovém stropu. Režim Selling First · mimo okno je dočasně nastaveno 100 %. Dům může odebírat ze sítě, dokud neobnovím běžné nastavení.{% endif %}\n{% elif c.get('status')=='failed' %}\n**Test se nespustil.** {{ c.get('error') }}\n{% else %}\nČekám na další ověřovací krok.\n{% endif %}\nBateriová automatika: **{{ 'ověřená' if s.get('battery_verified') else 'dosud neověřená' }}**.\n")
def tile(name,icon,service,color):
 return {'type':'tile','entity':'sensor.jarvis_energy_sales','name':name,'icon':icon,'color':color,'hide_state':True,
  'tap_action':{'action':'perform-action','perform_action':'jarvis_spot_control.'+service},
  'icon_tap_action':{'action':'perform-action','perform_action':'jarvis_spot_control.'+service}}
def conditional(phase,card):return {'type':'conditional','conditions':[{'condition':'state','entity':'sensor.jarvis_energy_sales','state':phase}], 'card':card}
def daily_block_card():
 return md("""### Denní plán baterie · 2 hodiny
{% set b=state_attr('sensor.jarvis_energy_sales','selected_block') or {} %}
{% if b.get('start') and b.get('end') %}
**{{ b.get('day','') }} · {{ b.start | timestamp_custom('%H:%M',true) }}–{{ b.end | timestamp_custom('%H:%M',true) }}**
{% set price=b.get('average_net',b.get('net')) %}
{% if price is not none %}Průměrný výkup po poplatku: **{{ price | round(3) }} Kč/kWh**.{% endif %}
{% else %}
Úplný dvouhodinový blok zatím není dostupný. Čekám na souvislé zveřejněné kladné ceny pro zbývající část dne.
{% endif %}
Každý den vybírám nejvýhodnější zbývající souvislý blok. Prodejní rezerva je pevně **60 %**; výkon vychází z aktuální energie nad rezervou po odečtení odhadu spotřeby domu a ztrát. Budoucí výrobu panelů do dostupné energie nepřičítám.
Při dosažení rezervy, neplatné ceně nebo poruše skončí prodej dříve.
""")
def battery_sale_card():
 return md("""{% set b=state_attr('sensor.jarvis_energy_sales','battery_sale') or {} %}
{% if b %}
### Prodej z baterie
{% if b.get('phase')=='armed' %}🟠 **Čekám na začátek bateriového prodeje.**
{% elif b.get('phase')=='stopping' %}🟠 **Ukončuji prodej a obnovuji domácí nastavení.**
{% elif b.get('phase')=='expiry_observed' %}**Nativní konec bateriového vybíjení byl potvrzen.** Obnovuji domácí nastavení.
{% elif b.get('observed') %}🔵 **Prodej běží · dodávka potvrzena měřením.**
{% else %}🟠 **Připravuji prodej · čekám na naměřenou dodávku.**{% endif %}
{% if b.get('start') and b.get('end') %}Okno **{{ b.start | timestamp_custom('%H:%M',true) }}–{{ b.end | timestamp_custom('%H:%M',true) }}**.{% endif %}
{% if b.get('power_w') %}Výkonový strop: **{{ b.power_w | round(0) }} W**.{% endif %}
{% endif %}
{% if state_attr('sensor.jarvis_energy_sales','battery_sale_error') %}⚠️ {{ state_attr('sensor.jarvis_energy_sales','battery_sale_error') }}{% endif %}
""")
def planning_card():
 return md("""### Informační výhled pro dům
{% set p=state_attr('sensor.jarvis_energy_sales','planning') or {} %}
{% if not p or p.get('quality')=='insufficient' %}
{{ p.get('reason','Načítám historii spotřeby a předpověď.') }}
{% else %}
Odhad potřebné zásoby pro dům: **{{ p.required_soc }} %**.
Výhled spotřeby na 24 hodin: **{{ p.estimated_house_kwh | round(1) }} kWh**.
{% if p.get('quality')=='energy_only' %}Časový průběh není úplný; solární výrobu nezapočítávám.{% elif p.get('pv_forecast_known') %}Využitelný solár podle kalibrované předpovědi: přibližně {{ p.credited_pv_kwh | round(1) }} kWh.{% else %}Neznámou nebo nedoloženou výrobu nezapočítávám.{% endif %}
{% endif %}
{% if p.get('history_error') %}{{ p.history_error }}{% endif %}
Tento výhled nemění pevnou prodejní rezervu 60 % ani výběr denního bloku.
""")
def summary_cards():
 return [grid_target_card(),md('''## Prodej elektřiny
{% set p=state_attr('sensor.jarvis_energy_sales','price') %}
{% if p %}**Výkup po poplatku: {{ p.net | round(3) }} Kč/kWh**{% else %}Výkupní cena není dostupná.{% endif %}

**{{ state_attr('sensor.jarvis_energy_sales','reason') or 'Čekám na měření.' }}**

{% if state_attr('sensor.jarvis_energy_sales','error') %}⚠️ {{ state_attr('sensor.jarvis_energy_sales','error') }}{% endif %}

Rezerva pro prodej **60 %** · maximální provozní strop **9,3 kW**.

Automatika vybírá denní dvouhodinový blok pro baterii a prodává dostupné přebytky panelů. Aktivace baterie vyžaduje ověřené ochrany.
'''),
 daily_block_card(),
 battery_sale_card(),
 verification_card(),
 planning_card(),
 conditional('native_test',tile('Zastavit ověřovací test','mdi:stop-circle','stop_sale','red')),
 *[conditional(phase,tile('Zastavit bateriový prodej','mdi:stop-circle','stop_sale','red')) for phase in ('armed','measuring','expiry_observed','stopping')],
 {'type':'tile','entity':'switch.jarvis_sale_automatic','name':'Automatický prodej','icon':'mdi:solar-power','color':'green'},
 {'type':'tile','entity':'sensor.jarvis_energy_sales','name':'Vlastní prodej','icon':'mdi:transmission-tower-export','color':'green','hide_state':True,
  'tap_action':{'action':'navigate','navigation_path':'/hlavni-prehled/vlastni-prodej'},
  'icon_tap_action':{'action':'navigate','navigation_path':'/hlavni-prehled/vlastni-prodej'}},
 conditional('running',tile('Prodej běží · zastavit','mdi:transmission-tower-export','stop_sale','blue'))]

def view():
 cards=[grid_target_card(),md('''## Vlastní prodej
{% set p=state_attr('sensor.jarvis_energy_sales','price') %}
**Výkup po odečtení 0,30 Kč/kWh:** {% if p %}{{ p.net | round(3) }} Kč/kWh{% else %}nedostupný{% endif %}

Nastav maximální dodávku do sítě a délku. Skutečný výkon závisí na dostupné energii. Prodejní rezerva baterie je pevně 60 %. U baterie nastav nejméně 5 minut; nativní začátek je na následující pětiminutové hranici.
'''),
 daily_block_card(),battery_sale_card(),
 {'type':'entities','title':'Nastavení vlastního prodeje','show_header_toggle':False,'entities':[
  {'entity':'select.jarvis_sale_source','name':'Co prodávat'},
  {'entity':'number.jarvis_sale_power_w','name':'Maximální výkon do sítě (W)'},
  {'entity':'number.jarvis_sale_minutes','name':'Délka (minuty)'}]},
 {'type':'conditional','conditions':[{'condition':'state','entity':'sensor.jarvis_energy_sales','state':'idle'},
  {'condition':'state','entity':'binary_sensor.jarvis_sales_ready','state':'on'}],
  'card':tile('Spustit prodej','mdi:play-circle','start_sale','green')},
 conditional('starting',md('🟠 **Připravuji prodej · čekám na potvrzení měniče.**')),
 conditional('preparing',md('🟠 **Připravuji nativní časové okno baterie.**')),
 conditional('armed',md('🟠 **Čekám na začátek bateriového prodeje.**')),
 conditional('awaiting_power',md('🟠 **Prodej povolen · čekám na naměřenou dodávku.**')),
 conditional('running',tile('Prodej běží','mdi:transmission-tower-export','stop_sale','blue')),
 conditional('awaiting_surplus',md('🟠 **Čekám na přebytky panelů · prodej je povolen, právě není potvrzená dodávka.**')),
 conditional('stopping',md('🟠 **Ukončuji prodej · ověřuji návrat bez přetoků.**')),
 tile('Zastavit prodej i automatiku','mdi:stop-circle','stop_sale','red'),
 md('''### Průběh
**{{ state_attr('sensor.jarvis_energy_sales','reason') or 'Čekám na řídicí službu.' }}**

{% set end=state_attr('sensor.jarvis_energy_sales','deadline') %}{% if end %}Konec: **{{ end | timestamp_custom('%H:%M:%S', true) }}**{% endif %}

{% if state_attr('sensor.jarvis_energy_sales','error') %}⚠️ {{ state_attr('sensor.jarvis_energy_sales','error') }}{% endif %}

U panelů vyžaduje časové ukončení běžící Home Assistant a spojení s měničem; při výpadku může PV export pokračovat pod nativním limitem.

Bateriové okno používá nativní SOC a časový program. Mimo něj dočasných 100 % omezuje také běžné vybíjení pro dům; při výpadku řízení dům využije dostupnou síť do obnovení domácího nastavení. PV export a opakování uloženého rozvrhu tím nejsou jednorázově ukončeny.
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
 owned=any(c.get('name')=='Vlastní prodej' for c in left)
 if len(right)!=5:raise ValueError('Spot dashboard layout changed; refusing blind overwrite')
 if owned:
  title_first=left[0].get('content','').startswith('## Prodej elektřiny')
  button_first=left[0]==grid_target_card() and len(left)>1 and left[1].get('content','').startswith('## Prodej elektřiny')
  if len(left) not in (10,len(summary_cards())+2,len(summary_cards())+3) or not (title_first or button_first):
   raise ValueError('Sales overview layout changed; refusing blind overwrite')
  retained=left[-3:]
 else:
  if len(left)!=5:raise ValueError('Spot dashboard layout changed; refusing blind overwrite')
  retained=[left[1],left[3],left[4]]
 result['sections'][0]['cards']=summary_cards()+retained
 right[1]={'type':'grid','columns':2,'square':False,'cards':[
  md('### Nákup · ČEZ\n## 5 Kč/kWh\nVčetně poplatků · sazba zadaná majitelem'),
  md("### Výkup · EnerSpot\n{% set p=state_attr('sensor.jarvis_energy_sales','price') %}\n## {{ p.net | round(3) if p else '—' }} Kč/kWh\nPo odečtení 0,30 Kč/kWh · konečné vyúčtování dle smlouvy")]}
 right[4]=md('### Řízení a historie\nAutomatika vybírá denní dvouhodinový blok s kladným výkupem. Prodejní rezerva je pevně **60 %**, celková dodávka nejvýše **9,3 kW**. Výhled počasí a historie je informační. Aktivace baterie vyžaduje ověřené ochrany.\n\nRozhodnutí a změny se zaznamenávají trvale. Stav archivu: **{{ states("sensor.jarvis_energy_archive") }}**.')
 for section in result['sections']:
  for card in section['cards']:card['grid_options']={'columns':'full'}
 return result

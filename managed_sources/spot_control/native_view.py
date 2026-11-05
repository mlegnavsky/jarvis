"""Reliable built-in Lovelace view; controls call the installed transaction service."""
import copy, json, yaml
class Loader(yaml.SafeLoader): pass
Loader.add_constructor('!include', lambda l,n: {'include':l.construct_scalar(n)})
DEVICE_DETAILS="""<details>
<summary><strong>🌡 Měnič a baterie · rozbalit</strong></summary>

{% macro reading(id, unit, absolute=false) -%}
{% set v=states(id) %}{% if is_number(v) %}{{ ((v|float|abs) if absolute else (v|float))|round(2) }} {{ unit }}{% else %}nedostupné{% endif %}
{%- endmacro %}
### Baterie · Felicity FLA48460-EU
{% set b=states('sensor.inverter_battery_power') %}
**Stav:** {% if not is_number(b) %}měření nedostupné{% elif b|float < -30 %}nabíjí se{% elif b|float > 30 %}vybíjí se{% else %}v klidu{% endif %}

**Nabití:** {{ reading('sensor.inverter_battery','%') }}

**Teplota baterie:** {{ reading('sensor.inverter_battery_temperature','°C') }}

**Napětí:** {{ reading('sensor.inverter_battery_voltage','V') }}

**Proud baterie:** {{ reading('sensor.inverter_battery_current','A',true) }} · směr podle stavu výše

**Výkon baterie:** {% if is_number(b) %}{{ (b|float|abs/1000)|round(2) }} kW{% else %}nedostupné{% endif %}

**Celkový nabíjecí limit:** {{ reading('number.inverter_battery_max_charging_current','A') }}

**Limit nabíjení ze sítě:** {{ reading('number.inverter_battery_grid_charging_current','A') }}

**Hlášení baterie:** {% if is_state('binary_sensor.inverter_battery_alarm','on') or is_state('binary_sensor.inverter_battery_fault','on') %}⚠️ Hlášen alarm nebo porucha{% elif is_state('binary_sensor.inverter_battery_alarm','off') and is_state('binary_sensor.inverter_battery_fault','off') %}Bez hlášeného alarmu a poruchy{% else %}Údaje o alarmu a poruše nejsou dostupné{% endif %}

### Měnič · DEYE SUN-12K-SG05LP3-EU-SM2
**Teplota měniče:** {{ reading('sensor.inverter_temperature','°C') }}

**Hlášené ztráty:** {{ reading('sensor.inverter_power_losses','W') }}

**Pracovní režim:** {% if states('select.inverter_work_mode') in ['unknown','unavailable'] %}nedostupný{% elif is_state('select.inverter_work_mode','Zero Export To CT') %}Bez přetoků podle CT{% else %}{{ states('select.inverter_work_mode') }}{% endif %}

**Nabíjecí test:** {% if is_state('sensor.jarvis_spot_control','running') %}běží{% elif is_state('sensor.jarvis_spot_control','idle') %}neběží{% elif is_state('sensor.jarvis_spot_control','restoring') %}obnovuje nastavení{% else %}{{ states('sensor.jarvis_spot_control') }}{% endif %}

</details>"""
def build(text):
    doc=yaml.load(text,Loader=Loader)
    home=next(v for v in doc['views'] if v.get('path')=='domov')
    house=next(copy.deepcopy(c) for section in home['sections'] for c in section['cards'] if c.get('type')=='picture-elements' and any(e.get('image','').endswith('/solar-house.png') for e in c.get('elements',[])))
    md=lambda text: {'type':'markdown','content':text}
    def button(name,icon,service):
        return {'type':'tile','entity':'sensor.jarvis_spot_control','name':name,'icon':icon,'hide_state':True,'vertical':True,'color':'green' if service=='start_test' else 'red','tap_action':{'action':'perform-action','perform_action':'jarvis_spot_control.'+service},'icon_tap_action':{'action':'perform-action','perform_action':'jarvis_spot_control.'+service},'hold_action':{'action':'none'}}
    modes={'type':'grid','columns':3,'square':False,'cards':[
        md('### Plně AI\nZatím neaktivní'),md('### Vlastní plán\nZatím neaktivní'),md("### {{ '✅' if is_state('select.inverter_work_mode','Zero Export To CT') and is_state('switch.inverter_export_surplus','off') else '⚠️' }} Offgrid\nBez přetoků · síť připojena")]}
    actions={'type':'grid','columns':2,'square':False,'cards':[
        {"type":"vertical-stack","cards":[{"type":"conditional","conditions":[{"condition":"state","entity":"sensor.jarvis_spot_control","state":"idle"}],"card":{"type":"tile","entity":"sensor.jarvis_spot_control","name":"Dobít baterii ze sítě","icon":"mdi:battery-plus","color":"green","hide_state":True,"vertical":True,"tap_action":{"action":"perform-action","perform_action":"jarvis_spot_control.start_test"},"icon_tap_action":{"action":"perform-action","perform_action":"jarvis_spot_control.start_test"},"hold_action":{"action":"none"},"double_tap_action":{"action":"none"}}},{"type":"conditional","conditions":[{"condition":"state","entity":"sensor.jarvis_spot_control","state":"starting"}],"card":{"type":"tile","entity":"sensor.jarvis_spot_control","name":"Spouštím nabíjení…","icon":"mdi:timer-sand","color":"amber","hide_state":True,"vertical":True,"tap_action":{"action":"none"},"icon_tap_action":{"action":"none"},"hold_action":{"action":"none"},"double_tap_action":{"action":"none"}}},{"type":"conditional","conditions":[{"condition":"state","entity":"sensor.jarvis_spot_control","state":"running"}],"card":{"type":"tile","entity":"sensor.jarvis_spot_control","name":"Nabíjení běží","icon":"mdi:battery-charging","color":"blue","hide_state":True,"vertical":True,"tap_action":{"action":"none"},"icon_tap_action":{"action":"none"},"hold_action":{"action":"none"},"double_tap_action":{"action":"none"}}},{"type":"conditional","conditions":[{"condition":"state","entity":"sensor.jarvis_spot_control","state":"restoring"}],"card":{"type":"tile","entity":"sensor.jarvis_spot_control","name":"Ukončuji · vracím nastavení","icon":"mdi:backup-restore","color":"amber","hide_state":True,"vertical":True,"tap_action":{"action":"none"},"icon_tap_action":{"action":"none"},"hold_action":{"action":"none"},"double_tap_action":{"action":"none"}}},{"type":"conditional","conditions":[{"condition":"state","entity":"sensor.jarvis_spot_control","state_not":"idle"},{"condition":"state","entity":"sensor.jarvis_spot_control","state_not":"starting"},{"condition":"state","entity":"sensor.jarvis_spot_control","state_not":"running"},{"condition":"state","entity":"sensor.jarvis_spot_control","state_not":"restoring"}],"card":{"type":"tile","entity":"sensor.jarvis_spot_control","name":"Stav nabíjení není dostupný","icon":"mdi:battery-alert","color":"red","hide_state":True,"vertical":True,"tap_action":{"action":"none"},"icon_tap_action":{"action":"none"},"hold_action":{"action":"none"},"double_tap_action":{"action":"none"}}}]},button('Zastavit a vrátit','mdi:stop-circle-outline','stop_restore')]}
    status=md("""## Spotové řízení
{% set active = state_attr('sensor.jarvis_spot_control','active') %}
{% if active %}🔵 **Test nabíjení běží** · cíl {{ state_attr('sensor.jarvis_spot_control','target_soc') }} %
{% elif state_attr('sensor.jarvis_spot_control','ready') %}🟢 **Připraveno k ručnímu testu**
{% else %}🟠 **Čekám na řídicí službu**{% endif %}
{% if state_attr('sensor.jarvis_spot_control','error') %}
**{{ state_attr('sensor.jarvis_spot_control','error') }}**
{% endif %}
Nabíjení spustíš tlačítkem níže. Automatický prodej je vypnutý.
""")
    prices={'type':'grid','columns':2,'square':False,'cards':[md('### Nákup · ČEZ\n## 5 Kč/kWh\nPevná sazba zadaná majitelem'), md("### Prodej nyní\n## {{ states('sensor.jarvis_spot_ote') | float(0) | round(3) if is_number(states('sensor.jarvis_spot_ote')) else '—' }} Kč/kWh\nTest OTE · bez DPH a poplatků")]}
    flows=md("""{% macro power(v) -%}{% if not is_number(v) %}—{% else %}{% set n=v|float|abs %}{% if n < 1000 %}{{ n|round(0)|int }} W{% else %}{{ (n/1000)|round(2) }} kW{% endif %}{% endif %}{%- endmacro %}
### Co se právě děje
{% set b=states('sensor.inverter_battery_power') %}{% set g=states('sensor.inverter_grid_power') %}
🔋 **Baterie:** {% if not is_number(b) %}měření nedostupné{% elif b|float < -30 %}nabíjí se{% elif b|float > 30 %}vybíjí se{% else %}v klidu{% endif %} · {{ power(b) }}

⚡ **Síť:** {% if not is_number(g) %}měření nedostupné{% elif g|float < -30 %}dodáváme{% elif g|float > 30 %}odebíráme{% else %}téměř vyrovnaná{% endif %} · {{ power(g) }}

{% if state_attr('sensor.jarvis_spot_control','charging_observed') %}**Současně naměřen odběr ze sítě a nabíjení baterie.**{% endif %}
""")
    limits=md("""### Krátký test nabíjení
Nejvýše **10 minut**, cíl **+5 procentních bodů**, maximálně **90 %**. Proud nejvýše **{{ state_attr('sensor.jarvis_spot_control','test_current_limit') }} A na straně baterie**.

**Zastavit a vrátit** ukončí test a obnoví hodnoty, které změnil. Není to úplná obnova všech nastavení měniče.

Při vypnutém Home Assistantu desetiminutový dohled neběží; na měniči platí aktivní časový interval.
""")
    history={'type':'entities','title':'Dnes · naměřená energie','show_header_toggle':False,'entities':[{'entity':'sensor.inverter_today_energy_export','name':'Prodáno do sítě'},{'entity':'sensor.inverter_today_energy_import','name':'Nakoupeno ze sítě'}]}
    more=md("""### Další řízení
**Prodávat přebytky:** zatím neaktivní. Rezerva **60 % / určuje AI** zatím není připojená k automatice.

Částky za den, týden a měsíc čekají na intervalové vyúčtování. Původní záloha nastavení je uložená; úplné obnovení zatím není připojené.

Ruční test · automatický prodej vypnutý
""")
    view={'title':'Spoty','path':'spoty','icon':'mdi:lightning-bolt','type':'sections','max_columns':2,'sections':[{'type':'grid','cards':[status,md(DEVICE_DETAILS),modes,actions,limits]},{'type':'grid','cards':[house,prices,flows,history,more]}]}
    for section in view['sections']:
        for c in section['cards']: c['grid_options']={'columns':'full'}
    marker='\n- title: Spoty\n'
    assert text.count(marker)==1
    prefix,old=text.split(marker)
    assert '\n- title:' not in old
    return (prefix+"\n- !include 'spot-control-view.yaml'\n",
            json.dumps(view,ensure_ascii=False,separators=(',',':'))+'\n')

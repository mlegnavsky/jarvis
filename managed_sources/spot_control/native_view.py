"""Reliable built-in Lovelace view; controls call the installed transaction service."""
import copy, json, yaml
class Loader(yaml.SafeLoader): pass
Loader.add_constructor('!include', lambda l,n: {'include':l.construct_scalar(n)})
def build(text):
    doc=yaml.load(text,Loader=Loader)
    home=next(v for v in doc['views'] if v.get('path')=='domov')
    house=next(copy.deepcopy(c) for section in home['sections'] for c in section['cards'] if c.get('type')=='picture-elements' and any(e.get('image','').endswith('/solar-house.png') for e in c.get('elements',[])))
    md=lambda text: {'type':'markdown','content':text}
    def button(name,icon,service):
        return {'type':'button','name':name,'icon':icon,'show_state':False,'tap_action':{'action':'perform-action','perform_action':'jarvis_spot_control.'+service},'hold_action':{'action':'none'}}
    modes={'type':'grid','columns':3,'square':False,'cards':[
        md('### Plně AI\nZatím neaktivní'),md('### Vlastní plán\nZatím neaktivní'),md("### {{ '✅' if is_state('select.inverter_work_mode','Zero Export To CT') and is_state('switch.inverter_export_surplus','off') else '⚠️' }} Offgrid\nBez přetoků · síť připojena")]}
    actions={'type':'grid','columns':2,'square':False,'cards':[
        button('Dobít baterii ze sítě','mdi:battery-charging','start_test'),button('Zastavit a vrátit','mdi:stop-circle-outline','stop_restore')]}
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
    prices={'type':'grid','columns':2,'square':False,'cards':[md('### '+label+"\n## {{ states('sensor.jarvis_spot_ote') | float(0) | round(3) if is_number(states('sensor.jarvis_spot_ote')) else '—' }} Kč/kWh\nTest OTE · bez DPH a poplatků") for label in ['Nákup nyní','Prodej nyní']]}
    flows=md("""### Co se právě děje
{% set b=states('sensor.inverter_battery_power') %}{% set g=states('sensor.inverter_grid_power') %}
🔋 **Baterie:** {% if not is_number(b) %}měření nedostupné{% elif b|float < -30 %}nabíjí se{% elif b|float > 30 %}vybíjí se{% else %}v klidu{% endif %} · {{ b }} W

⚡ **Síť:** {% if not is_number(g) %}měření nedostupné{% elif g|float < -30 %}dodáváme{% elif g|float > 30 %}odebíráme{% else %}téměř vyrovnaná{% endif %} · {{ g }} W

{% if state_attr('sensor.jarvis_spot_control','charging_observed') %}**Současně naměřen odběr ze sítě a nabíjení baterie.**{% endif %}
""")
    limits=md("""### Krátký test nabíjení
Nejvýše **10 minut**, cíl **+5 procentních bodů**, maximálně **90 %**. Proud nejvýše **20 A na straně baterie**.

**Zastavit a vrátit** ukončí test a obnoví hodnoty, které změnil. Není to úplná obnova všech nastavení měniče.

Při vypnutém Home Assistantu desetiminutový dohled neběží; na měniči platí aktivní časový interval.
""")
    history={'type':'entities','title':'Dnes · naměřená energie','show_header_toggle':False,'entities':[{'entity':'sensor.inverter_today_energy_export','name':'Prodáno do sítě'},{'entity':'sensor.inverter_today_energy_import','name':'Nakoupeno ze sítě'}]}
    more=md("""### Další řízení
**Prodávat přebytky:** zatím neaktivní. Rezerva **60 % / určuje AI** zatím není připojená k automatice.

Částky za den, týden a měsíc čekají na intervalové vyúčtování. Původní záloha nastavení je uložená; úplné obnovení zatím není připojené.

Spoty 0.2.1 · ruční test · automatický prodej vypnutý
""")
    view={'title':'Spoty','path':'spoty','icon':'mdi:lightning-bolt','type':'sections','max_columns':2,'sections':[{'type':'grid','cards':[status,modes,actions,limits]},{'type':'grid','cards':[house,prices,flows,history,more]}]}
    for section in view['sections']:
        for c in section['cards']: c['grid_options']={'columns':'full'}
    marker='\n- title: Spoty\n'
    assert text.count(marker)==1
    prefix,old=text.split(marker)
    assert '\n- title:' not in old
    return (prefix+"\n- !include 'spot-control-view.yaml'\n",
            json.dumps(view,ensure_ascii=False,separators=(',',':'))+'\n')

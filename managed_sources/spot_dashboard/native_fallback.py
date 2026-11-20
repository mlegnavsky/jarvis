"""Replace only Spoty with built-in cards; preserve every other view byte-for-byte."""
from pathlib import Path
import copy, sys, yaml, json
class Loader(yaml.SafeLoader): pass
Loader.add_constructor('!include', lambda loader,node: {'include':loader.construct_scalar(node)})
def build(text):
    doc=yaml.load(text,Loader=Loader)
    home=next(v for v in doc['views'] if v.get('path')=='domov')
    house=next(copy.deepcopy(c) for section in home['sections'] for c in section['cards'] if c.get('type')=='picture-elements' and any(e.get('image','').endswith('/solar-house.png') for e in c.get('elements',[])))
    def md(content,title=None):
        return {'type':'markdown',**({'title':title} if title else {}),'content':content}
    def entities(title,items):
        return {'type':'entities','title':title,'show_header_toggle':False,'entities':[{'entity':i,'name':n} for i,n in items]}
    states=md('''{% set zero = is_state('select.inverter_work_mode','Zero Export To CT') and is_state('switch.inverter_export_surplus','off') %}
| Plně AI | Vlastní plán | Offgrid / bez přetoků |
| :---: | :---: | :---: |
| Nepřipojeno | Nepřipojeno | {{ '✅ Zjištěný režim' if zero else 'Nepotvrzeno' }} |

**Příprava · řízení neaktivní.** Současný provoz se nemění. Offgrid zde znamená provoz bez přetoků, nikoli odpojení od sítě.''','Spotové řízení')
    price=md('''{% set ns = namespace(price=none) %}
{% for r in state_attr('sensor.jarvis_spot_ote','rows') or [] %}
{% set t = as_timestamp(r.time, 0) %}
{% if t <= as_timestamp(now()) < t + 900 and r.price is number %}{% set ns.price = r.price %}{% endif %}
{% endfor %}
| Aktuální nákup | Aktuální prodej |
| :---: | :---: |
| {{ ('%.3f Kč/kWh' % ns.price) if ns.price is not none else 'Nedostupná cena' }} | {{ ('%.3f Kč/kWh' % ns.price) if ns.price is not none else 'Nedostupná cena' }} |

Testovací ceny **OTE bez DPH a poplatků** pro obě strany. {% if ns.price is none or ns.price <= 0 %}**Prodej by byl blokován.**{% endif %} Skutečné obchodování není aktivní.''')
    flows=md('''{% set b = states('sensor.inverter_battery_power') %}
{% set g = states('sensor.inverter_grid_power') %}
**Baterie:** {% if not is_number(b) %}měření nedostupné{% elif b|float < -30 %}nabíjí se{% elif b|float > 30 %}vybíjí se{% else %}v klidu{% endif %}.

**Síť:** {% if not is_number(g) %}měření nedostupné{% elif g|float < -30 %}dodáváme do sítě{% elif g|float > 30 %}odebíráme ze sítě{% else %}téměř vyrovnaná{% endif %}.

Podíl zdrojů prodeje zatím není vypočítaný.''','Směr energie')
    telemetry=entities('Živé hodnoty',[('sensor.inverter_pv_power','Výroba soláru'),('sensor.inverter_load_power','Spotřeba domu'),('sensor.inverter_battery','Nabití baterie'),('sensor.inverter_battery_power','Baterie · − nabíjení / + vybíjení'),('sensor.inverter_grid_power','Síť · − prodej / + odběr')])
    plan=md('''**Dobít baterii ze sítě · Prodávat přebytky · Zastavit akci**

Tyto povely zatím nejsou aktivní. Rezerva pro připravované řízení: **60 %**, později volba „Určuje AI“.

**Obnovit výchozí nastavení:** výchozí dostupná nastavení jsou uložená, obnovovací povel zatím není připojený.''','Připravené ovládání')
    totals=entities('Dnes · skutečné čítače měniče',[('sensor.inverter_today_energy_export','Prodáno do sítě'),('sensor.inverter_today_energy_import','Nakoupeno ze sítě')])
    more=md('''<details><summary>Finance, historie a omezení přípravy</summary>

Částky a týdenní/měsíční součty zatím nejsou připojené. Historickou energii neoceňujeme aktuální cenou. Řízení podle počasí, automatický prodej a obnovení nastavení nejsou spuštěné.

</details>

Spoty · kompatibilní přehled 0.1.1''')
    view={'title':'Spoty','path':'spoty','icon':'mdi:lightning-bolt','type':'sections','max_columns':2,'sections':[{'type':'grid','cards':[states,house,price,flows]},{'type':'grid','cards':[plan,totals]}]}
    for section in view['sections']:
        for card in section['cards']:
            card['grid_options']={'columns': 'full'}
    marker='\n- title: Spoty\n'
    assert text.count(marker)==1
    prefix,old=text.split(marker)
    assert '\n- title:' not in old, 'Spoty must be last; refuse to drop later views'
    return prefix+'\n- '+json.dumps(view,ensure_ascii=False,separators=(',',':'))+'\n'
if __name__=='__main__':
    source,target=map(Path,sys.argv[1:]);target.write_text(build(source.read_text()))

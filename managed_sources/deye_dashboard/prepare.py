"""Add a read-only native Lovelace DEYE page to a fresh dashboard copy."""
import copy,sys,yaml
from pathlib import Path

def build(d):
 energy=next(v for v in d['views'] if v.get('path')=='energie')
 def md(text):return {'type':'markdown','content':text}
 def table(title,rows):
  return md('### '+title+'\n\n| Parametr | Aktuální hodnota |\n|:--|--:|\n'+'\n'.join('| '+label+" | {{ states('"+entity+"') }} "+unit+' |' for label,entity,unit in rows))
 def row(label,suffix,unit=''):return label,'sensor.inverter_'+suffix,unit
 overview=copy.deepcopy(energy['sections'][1])
 overview['column_span']=2
 cards=[{'type':'heading','heading':'DEYE a baterie','icon':'mdi:solar-power-variant'},md('Živý přehled • pouze čtení. Nastavení měniče se z této stránky nemění.\n\n**Stav:** {{ {"Normal":"V pořádku"}.get(states("sensor.inverter_device_state"), states("sensor.inverter_device_state")) }} · **Připojení:** {{ "Připojeno" if is_state("binary_sensor.inverter_connection", "on") else "Nedostupné" }}\n\nPoslední data: {{ as_local(states.sensor.inverter_battery.last_updated).strftime("%d. %m. %Y %H:%M:%S") }}')]
 sections=[{'type':'grid','column_span':3,'cards':cards},overview,{'type':'grid','cards':[{'type':'gauge','entity':'sensor.inverter_battery','name':'Nabití baterie','min':0,'max':100,'severity':{'red':0,'yellow':20,'green':40}},table('Baterie',[
 row('Teplota','battery_temperature','°C'),row('Napětí','battery_voltage','V'),row('Proud','battery_current','A'),row('Kondice baterie','battery_soh','%')]),md('**Baterie právě:** {{ {"charging":"Nabíjí se","discharging":"Vybíjí se","idle":"V klidu"}.get(states("sensor.inverter_battery_state"),states("sensor.inverter_battery_state")) }}\n\nVýkon: {{ states("sensor.inverter_battery_power") }} W • kladné číslo = vybíjení, záporné = nabíjení.\n\nKapacita hlášená měničem: {{ states("sensor.inverter_battery_capacity") }} kWh. Nejde o ověření skutečné využitelné kapacity.')]}]
 sections.append({'type':'grid','cards':[table('Dnes · energie',[
 row('Vyrobeno ze slunce','today_production','kWh'),row('Spotřeba domu','today_load_consumption','kWh'),row('Odběr ze sítě','today_energy_import','kWh'),row('Dodávka do sítě','today_energy_export','kWh'),row('Do baterie','today_battery_charge','kWh'),row('Z baterie','today_battery_discharge','kWh')]),md('### Nákup a prodej\n\nFinanční výsledek zatím nepočítáme: není zde ověřený kompletní spotový ceník včetně poplatků. Smlouva Spotty začíná **5. listopadu 2026**. Množství odebrané a dodané energie je živé.') ]})
 sections.append({'type':'grid','cards':[md('### Režim měniče\n\n**Provoz:** {{ {"Zero Export To CT":"Bez přetoků podle měření CT","Selling First":"Přednost dodávky do sítě","Zero Export To Load":"Bez přetoků podle zátěže"}.get(states("select.inverter_work_mode"),states("select.inverter_work_mode")) }}\n\n**Priorita:** {{ {"Load First":"Nejdříve spotřeba domu","Battery First":"Nejdříve baterie"}.get(states("select.inverter_energy_pattern"),states("select.inverter_energy_pattern")) }}\n\n**Nabíjení ze sítě – hlavní povolení:** {{ "Zapnuto" if is_state("switch.inverter_battery_grid_charging","on") else "Vypnuto" if is_state("switch.inverter_battery_grid_charging","off") else "Nedostupné" }}\n\nSamotné hlavní povolení neznamená, že baterie právě nabíjí ze sítě. Rozhodují také časové programy a další podmínky.'),table('Limity · pouze zobrazení',[
 ('Max. nabíjecí proud','number.inverter_battery_max_charging_current','A'),('Max. vybíjecí proud','number.inverter_battery_max_discharging_current','A'),('Nízké nabití','number.inverter_battery_low_soc','%'),('Vypnutí baterie','number.inverter_battery_shutdown_soc','%'),('Limit dodávky do sítě','number.inverter_grid_max_export_power','W')]),md('**Záloha nastavení měniče:** zatím není vytvořená úplná obnovitelná záloha. Tato stránka pouze čte hodnoty; neobsahuje tlačítko obnovy.') ]})
 schedule='### Šest časových programů\n\nČasy zobrazené přímo z měniče. Každý interval končí začátkem následujícího; šestý pokračuje přes půlnoc.\n\n| Od | Do | Cílové nabití | Výkonový limit | Nabíjení |\n|:--|:--|--:|--:|:--|\n'
 for i in range(1,7):
  j=i%6+1
  schedule+=f'| {{{{ states("time.inverter_program_{i}_time") }}}} | {{{{ states("time.inverter_program_{j}_time") }}}} | {{{{ states("number.inverter_program_{i}_soc") }}}} % | {{{{ states("number.inverter_program_{i}_power") }}}} W | '+ '{{ {"Disabled":"Vypnuto","Grid":"Ze sítě","Generator":"Z generátoru","Grid & Generator":"Síť a generátor"}.get(states("select.inverter_program_'+str(i)+'_charging"),states("select.inverter_program_'+str(i)+'_charging")) }} |\n'
 sections.append({'type':'grid','column_span':3,'cards':[md(schedule)]})
 sections.extend([{'type':'grid','column_span':2,'cards':[{'type':'history-graph','title':'Výkony za posledních 24 hodin','hours_to_show':24,'entities':[{'entity':'sensor.inverter_pv_power','name':'Slunce'},{'entity':'sensor.inverter_load_power','name':'Dům'},{'entity':'sensor.inverter_grid_power','name':'Síť (+ odběr / − dodávka)'},{'entity':'sensor.inverter_battery_power','name':'Baterie (+ vybíjení / − nabíjení)'}]}]}, {'type':'grid','cards':[table('Diagnostika',[
 row('Teplota měniče','temperature','°C'),row('Alarm měniče','device_alarm'),row('Porucha měniče','device_fault'),row('Interval aktualizací','update_interval','s')]),md('### Jak číst přehled\n\n**W** = okamžitý výkon. **kWh** = množství energie. **%** = stav nabití.\n\n**Síť:** kladný výkon znamená odběr, záporný dodávku. **Baterie:** kladný výkon znamená vybíjení.\n\nPři výpadku komunikace mohou poslední hodnoty zůstat zobrazené. Kontrolujte připojení a čas posledních dat nahoře.')]}])
 view={'title':'DEYE a baterie','path':'deye-baterie','icon':'mdi:battery-charging','type':'sections','max_columns':3,'sections':sections}
 d['views']=[v for v in d['views'] if v.get('path')!='deye-baterie']; d['views'].insert(4,view)
 # Add a visible entry point without modifying the existing energy layout.
 energy['sections'][0]['cards'].append({'type':'button','name':'DEYE a baterie · podrobný přehled','icon':'mdi:battery-charging','tap_action':{'action':'navigate','navigation_path':'/hlavni-prehled/deye-baterie'},'grid_options':{'columns':'full','rows':1}})
 return d
if __name__=='__main__':
 p=Path(sys.argv[1]);p.with_suffix('.prepared.yaml').write_text(yaml.safe_dump(build(yaml.safe_load(p.read_text())),allow_unicode=True,sort_keys=False,width=140))

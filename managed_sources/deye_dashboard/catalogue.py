"""Generate Czech read-only catalogue rows; never emit device service actions."""
import re
WRITABLE={'number','select','switch','button','time','datetime'}
NAMES={
'device':'Typ měniče','device_state':'Provozní stav měniče','device_relay':'Stav relé měniče','device_alarm':'Alarm měniče','device_fault':'Porucha měniče','update_interval':'Interval aktualizací',
'battery':'Nabití baterie','battery_soh':'Hlášené zdraví baterie (SOH)','battery_capacity':'Hlášená kapacita baterie','battery_state':'Stav baterie','battery_control_mode':'Způsob řízení baterie','battery_operation_mode':'Provozní režim baterie','battery_bms_type':'Typ komunikace BMS',
'battery_equalization':'Ekvalizační napětí','battery_absorption':'Absorpční napětí','battery_float':'Udržovací napětí','battery_empty':'Napětí prázdné baterie','battery_equalization_cycle':'Interval ekvalizace','battery_equalization_time':'Doba ekvalizace','battery_temperature_compensation':'Teplotní kompenzace baterie','battery_max_charging_current':'Maximální nabíjecí proud','battery_max_discharging_current':'Maximální vybíjecí proud','battery_resistance':'Nastavený odpor baterie','battery_charging_efficiency':'Nastavená účinnost nabíjení',
'battery_shutdown_soc':'Vypnutí baterie podle nabití','battery_restart_soc':'Obnovení baterie podle nabití','battery_low_soc':'Nízké nabití baterie','battery_shutdown_voltage':'Vypínací napětí baterie','battery_restart_voltage':'Napětí obnovení baterie','battery_low_voltage':'Nízké napětí baterie','battery_wake_up':'Probuzení baterie',
'battery_grid_charging':'Povolení nabíjení baterie ze sítě','battery_grid_charging_start':'Start nabíjení ze sítě podle nabití','battery_grid_charging_start_voltage':'Start nabíjení ze sítě podle napětí','battery_grid_charging_current':'Nabíjecí proud ze sítě',
'battery_generator_charging':'Povolení nabíjení z generátoru','battery_generator_charging_start':'Start nabíjení z generátoru podle nabití','battery_generator_charging_start_voltage':'Start nabíjení z generátoru podle napětí','battery_generator_charging_current':'Nabíjecí proud generátoru',
'zero_export_power':'Korekce nulových přetoků','export_surplus_power':'Limit výkonu přebytků','export_surplus':'Povolení exportu přebytků','grid_max_export_power':'Maximální export do sítě','grid_max_import_power':'Maximální import ze sítě','grid_power_factor':'Účiník sítě – škálování nutno ověřit','grid_voltage':'Jmenovité síťové napětí','grid_frequency':'Jmenovitá síťová frekvence','grid_voltage_protection_high':'Horní napěťová ochrana','grid_voltage_protection_low':'Dolní napěťová ochrana','grid_frequency_protection_high':'Horní frekvenční ochrana','grid_frequency_protection_low':'Dolní frekvenční ochrana',
'energy_pattern':'Priorita využití energie','work_mode':'Pracovní režim měniče','time_of_use':'Platnost časových programů','io_mode':'Režim pomocného portu','charging_signal':'Nabíjecí signál','ac_coupling':'Vazba střídavých zdrojů (AC coupling)',
'access_point':'Přístupový bod','cloud':'Cloudové připojení','restart':'Restart měniče','self_check_time':'Doba vlastní kontroly','date_time':'Datum a čas měniče','off_grid':'Přepínač Off Grid – neznamená stav odpojení domu','export_asymmetry':'Asymetrie exportu','mppt_multi_point_scanning':'Vícebodové vyhledávání MPPT','microinverter_export_cut_off':'Odpojení exportu mikroinvertoru',
'generator_operating_time':'Doba provozu generátoru','generator_cooling_time':'Doba chlazení generátoru','generator_min_pv_power':'Minimální výkon panelů pro generátor','generator_peak_shaving':'Omezování špiček generátoru','grid_peak_shaving':'Omezování odběrových špiček sítě','generator_on_grid':'Generátor při připojené síti','generator_grid_side':'Generátor na straně sítě',
'smartload_off_voltage':'Vypnutí SmartLoad podle napětí','smartload_off':'Vypnutí SmartLoad podle nabití','smartload_on_voltage':'Zapnutí SmartLoad podle napětí','smartload_on':'Zapnutí SmartLoad podle nabití',
'connection':'Komunikační spojení', 'dc_temperature':'Teplota DC části měniče','temperature':'Teplota měniče','power':'Celkový výstupní výkon měniče','power_losses':'Okamžité ztráty systému','today_losses':'Dnešní ztráty energie','total_losses':'Celkové ztráty energie'}
WORDS={'today':'dnes','total':'celkem','battery':'baterie','life':'ekvivalentní','cycles':'cykly','charge':'nabito','discharge':'vybito','pv':'panely','pv1':'solární vstup PV1','pv2':'solární vstup PV2','power':'výkon','voltage':'napětí','current':'proud','temperature':'teplota','grid':'distribuční síť','energy':'energie','import':'odběr','export':'dodávka','production':'výroba','load':'spotřeba domu','consumption':'spotřeba','output':'výstup měniče','frequency':'frekvence','generator':'generátor','internal':'interní','external':'externí','ct1':'měření CT1','ct2':'měření CT2','ct3':'měření CT3','ups':'záložní výstup UPS','alarm':'alarm','fault':'porucha','l1':'L1','l2':'L2','l3':'L3'}

def label(entity):
 domain,suffix=entity.split('.',1);suffix=suffix.removeprefix('inverter').lstrip('_')
 if not suffix:return {'switch':'Zapnutí měniče','binary_sensor':'Běh měniče'}.get(domain,'Měnič')
 if suffix=='battery_capacity' and domain=='number':return 'Nastavená kapacita baterie (Ah)'
 if domain=='binary_sensor' and suffix in ('grid','generator'):return 'Přítomnost '+('distribuční sítě' if suffix=='grid' else 'generátoru')
 if domain=='switch' and suffix=='generator':return 'Zapnutí generátoru'
 if suffix=='pv_power' and domain=='number':return 'Nastavený limit výkonu panelů'
 if suffix=='grid_frequency' and domain=='sensor':return 'Skutečná frekvence sítě'
 if suffix=='grid_peak_shaving' and domain=='number':return 'Limit odběrových špiček sítě'
 if suffix=='generator_peak_shaving' and domain=='number':return 'Limit špiček generátoru'
 if suffix in NAMES:return NAMES[suffix]
 m=re.fullmatch(r'program_(\d)_(.+)',suffix)
 if m:return 'Program '+m[1]+' · '+{'time':'začátek','power':'výkonový limit','soc':'cílové nabití','voltage':'cílové napětí','charging':'režim nabíjení'}[m[2]]
 text=' · '.join(WORDS.get(w,w) for w in suffix.split('_'))
 return text[0].upper()+text[1:]

def group(e):
 id=e['entity_id'];s=id.split('.',1)[1]
 if id.split('.')[0] in WRITABLE:
  if '_program_' in s or s.endswith('_time_of_use'):return 'Časové programy · nastavení'
  if '_battery_' in s:return 'Baterie · nastavení'
  if any(k in s for k in ('generator','smartload','io_mode')):return 'Generátor a SmartLoad · nastavení'
  return 'Měnič a síť · nastavení'
 if 'battery' in s:return 'Baterie · měření a statistiky'
 if any(k in s for k in ('_pv','production')):return 'Solární panely · měření'
 if any(k in s for k in ('internal','external')):return 'Měření CT · proudy a výkony'
 if 'generator' in s:return 'Generátor · měření'
 if any(k in s for k in ('_load','consumption')):return 'Dům a záložní výstup · měření'
 if any(k in s for k in ('_grid','energy_import','energy_export')):return 'Distribuční síť · měření'
 if '_output_' in s or s=='inverter_power':return 'Výstup měniče · měření'
 return 'Diagnostika a ztráty'

def catalogue(states):
 return [dict(id=e['entity_id'],label=label(e['entity_id']),group=group(e),writable=e['entity_id'].split('.')[0] in WRITABLE) for e in states]

TRANSLATIONS={'on':'Zapnuto / přítomno','off':'Vypnuto / nepřítomno','unavailable':'Nedostupné','unknown':'Neznámé','Normal':'V pořádku','OK':'V pořádku','charging':'Nabíjí se','discharging':'Vybíjí se','idle':'V klidu','Disabled':'Zakázáno','Grid':'Ze sítě','Generator':'Generátor','Load First':'Přednost spotřeby domu','Battery First':'Přednost baterie','Zero Export To CT':'Bez přetoků podle CT','Zero Export To Load':'Bez přetoků podle zátěže','Selling First':'Přednost dodávky do sítě','Week':'Celý týden','Lithium':'Lithiová baterie','Capacity':'Podle kapacity','Voltage':'Podle napětí'}

def card(entries,title):
 import json
 text='### '+title+'\n\n| Údaj | Aktuální hodnota | Možnost |\n|:--|:--|:--|\n'
 for e in entries:
  id=e['id'];value='{{ '+json.dumps(TRANSLATIONS,ensure_ascii=False)+'.get(states("'+id+'"),states("'+id+'")) }} {{ state_attr("'+id+'","unit_of_measurement") or "" }}'
  possibility='{% if states("'+id+'") in ["unavailable","unknown"] %}Nyní nelze potvrdit{% else %}<font color="#d32f2f">🔴 **můžeme změnit**</font>{% endif %}' if e['writable'] else 'Pouze čtení'
  text+='| '+e['label']+' | '+value+' | '+possibility+' |\n'
 # One shared translation object avoids repeating it in every row.
 mapping=json.dumps(TRANSLATIONS,ensure_ascii=False)
 text='{% set cz = '+mapping+' %}\n'+text.replace(mapping+'.get','cz.get')
 return {'type':'markdown','content':text}

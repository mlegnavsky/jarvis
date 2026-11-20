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

# Plain-language help stays next to the live value, not in a separate manual.
def explain(entity):
 domain,s=entity.split('.',1);s=s.removeprefix('inverter').lstrip('_')
 exact={
 'battery':'Kolik procent energie právě zbývá v baterii.',
 'battery_soh':'Odhad kondice vůči nové baterii. Hlášený údaj, nikoli provedený kapacitní test.',
 'battery_capacity':'Odhad kapacity hlášený integrací.' if domain=='sensor' else 'Kapacita nastavená v ampérhodinách; není to přímo počet kWh.',
 'battery_state':'Zda baterie právě přijímá energii, dodává ji, nebo je v klidu.',
 'battery_max_charging_current':'Horní mez proudu při nabíjení baterie; vyšší proud může znamenat rychlejší nabíjení, pokud to dovolí BMS.',
 'battery_max_discharging_current':'Horní mez proudu, který smí baterie dodávat do měniče.',
 'battery_bms_type':'Komunikační protokol mezi měničem a elektronikou baterie. BMS hlídá provoz baterie.',
 'battery_control_mode':'Jaký typ baterie měnič obsluhuje, například lithiovou baterii.',
 'battery_operation_mode':'Zda se baterie řídí podle procent nabití, nebo podle napětí.',
 'work_mode':'Určuje, zda měnič dodává přebytky do sítě, nebo výrobu omezuje podle spotřeby.',
 'energy_pattern':'Určuje, zda mají přednost spotřebiče v domě, nebo nabití baterie.',
 'zero_export_power':'Malý cílový odběr ze sítě, který pomáhá zabránit nechtěným přetokům.',
 'grid_max_export_power':'Nastavený výkonový limit dodávky do distribuční sítě. Nenahrazuje smluvně povolený limit.',
 'grid_max_import_power':'Nastavený horní limit odběru z distribuční sítě.',
 'export_surplus':'Povoluje dodávku přebytečné elektřiny. Závisí také na pracovním režimu a dalších podmínkách.',
 'export_surplus_power':'Výkonový parametr přebytků; uplatnění závisí na zvoleném režimu měniče.',
 'off_grid':'Servisní volba ostrovního provozu. Samotné Zapnuto neprokazuje odpojení domu od sítě.',
 'grid_power_factor':'Parametr související s účiníkem. Význam a škálování tohoto konkrétního údaje je nutné před změnou ověřit.',
 'mppt_multi_point_scanning':'Měnič hledá vhodný pracovní bod panelů, aby získal vyšší výkon i při nerovnoměrném osvitu.',
 'power_losses':'Integrací hlášený rozdíl výkonů v systému. Není to výkon, který panely kvůli omezení přestaly vyrábět.',
 'today_losses':'Dnešní hlášené ztráty v systému. Nejde o součet nevyužité sluneční energie.',
 'total_losses':'Dlouhodobý součet hlášených ztrát; nezahrnuje automaticky nevyužitý potenciál panelů.',
 'connection':'Zda má Green spojení s měničem. Při výpadku mohou jiné údaje zůstat na poslední hodnotě.',
 'time_of_use':'Určuje, kdy mají platit časové programy pro práci s baterií.',
 'io_mode':'Volí účel pomocného portu: například generátor nebo řízenou zátěž.',
 'ac_coupling':'Spolupráce s dalším zdrojem připojeným na střídavé straně elektrické instalace.',
 'export_asymmetry':'Volba rozdělení dodávky mezi fáze. Nastavení musí odpovídat připojení a podmínkám sítě.',
 'charging_signal':'Servisní volba nabíjecího signálu; samotný název nepotvrzuje její konkrétní účinek.',
 'microinverter_export_cut_off':'Volba omezování dodávky z připojeného mikroinvertoru.',
 'update_interval':'Čas mezi aktualizacemi údajů měniče. Menší číslo znamená častější aktualizaci.',
 'date_time':'Vnitřní hodiny měniče; důležité pro začátky časových programů.',
 'access_point':'Bezdrátový přístupový bod komunikačního zařízení.',
 'cloud':'Způsob spojení s cloudovou službou.',
 'restart':'Povel k restartu měniče. V tomto přehledu jej nespouštíme.',
 'self_check_time':'Servisní časový parametr vlastní kontroly měniče.',
 'device':'Identifikace typu zařízení hlášená integrací.',
 'device_state':'Celkový provozní stav, například běžný chod nebo porucha.',
 'device_relay':'Hlášené propojení měniče a sítě přes relé.',
 'device_alarm':'Aktuální varování měniče; V pořádku znamená bez hlášeného alarmu.',
 'device_fault':'Hlášená porucha měniče; V pořádku znamená bez hlášené poruchy.',
 'battery_wake_up':'Povel k probuzení baterie; účinek závisí na baterii a jejím stavu.',
 }
 if s in exact:return exact[s]
 if not s:return 'Povoluje nebo ukazuje běh měniče podle typu položky.'
 if '_program_' in entity:
  end=s.rsplit('_',1)[-1]
  return {'time':'Začátek tohoto intervalu; konec určuje následující program.', 'soc':'Cílová hodnota nabití baterie pro tento interval; účinek závisí na režimu.', 'voltage':'Cílové napětí baterie pro interval při řízení podle napětí.', 'power':'Výkonový limit pro práci baterie v daném intervalu; nejde o výkon právě vyráběný panely.', 'charging':'Volí povolené nabíjení v intervalu: zakázáno, síť nebo generátor.'}.get(end,'Parametr časového programu baterie.')
 if 'equalization' in s:return 'Vyrovnávací nabíjení a jeho servisní parametry. Přítomnost volby neznamená, že se používá u lithiové baterie.'
 if 'absorption' in s:return 'Napětí hlavní dokončovací fáze nabíjení; musí odpovídat požadavkům baterie.'
 if 'float' in s:return 'Napětí pro udržování nabití podle zvoleného režimu baterie.'
 if 'compensation' in s:return 'Korekce nabíjecího napětí při změně teploty; servisní parametr baterie.'
 if 'resistance' in s:return 'Servisní hodnota odporu bateriového okruhu používaná měničem.'
 if 'efficiency' in s:return 'Nastavený odhad účinnosti nabíjení; nejde o právě změřenou účinnost.'
 if 'shutdown' in s:return 'Hranice, při které měnič přestane využívat baterii, aby ji chránil.'
 if 'restart' in s:return 'Hranice, po jejímž dosažení smí měnič znovu začít využívat baterii.'
 if 'battery_low' in s or s=='battery_empty':return 'Dolní mez stavu baterie pro její řízení a ochranu.'
 if 'charging_start' in s:return 'Hranice nabití nebo napětí, při které může začít povolené nabíjení z daného zdroje.'
 if 'charging_current' in s:return 'Nastavený proud pro nabíjení z tohoto zdroje; skutečný výkon závisí také na napětí a limitech baterie.'
 if 'battery_grid_charging' in s:return 'Hlavní povolení nabíjení ze sítě. Nabíjení ještě závisí na časových programech a dalších podmínkách.'
 if 'battery_generator_charging' in s:return 'Hlavní povolení nabíjení baterie z generátoru.'
 if 'smartload' in s:return 'Hranice pro zapnutí či vypnutí řízené zátěže na pomocném výstupu, podle procent nabití nebo napětí.'
 if 'peak_shaving' in s:return 'Omezuje odběrové špičky daného zdroje; přepínač funkci povoluje, číselná hodnota stanovuje limit.'
 if 'protection' in s:return 'Síťová ochranná hranice; při jejím překročení může měnič přestat dodávat do sítě. Servisní parametr.'
 if 'life_cycles' in s:return 'Dopočítané ekvivalentní plné cykly podle prošlé energie; nikoli počet každého dílčího nabití.'
 if 'internal' in s or 'external' in s:return 'Měření uvnitř měniče nebo externími proudovými snímači CT. CT je snímač proudu.'
 if 'temperature' in s:return 'Teplota příslušné části zařízení; nejde o teplotu solárních panelů na střeše.'
 if any(x in s for x in ['today','total','energy','production','consumption','charge','discharge']):return 'Množství energie za uvedené období. Dnes se vztahuje k dnešnímu dni, celkem k čítači integrace nebo zařízení.'
 if 'voltage' in s:return 'Elektrické napětí ve voltech. L1, L2 a L3 označují jednotlivé fáze; PV1/PV2 dvě pole panelů.'
 if 'current' in s:return 'Elektrický proud v ampérech. U panelů napětí × proud dává skutečně odebíraný výkon.'
 if 'frequency' in s:return 'Frekvence střídavé sítě v hertzech, běžně kolem 50 Hz.'
 if 'power' in s:return 'Okamžitý výkon ve wattech. U sítě + znamená odběr a − dodávku; u baterie + vybíjení a − nabíjení.'
 if 'alarm' in s or 'fault' in s:return 'Hlášené varování nebo porucha baterie či zařízení.'
 if 'generator' in s:return 'Údaj nebo servisní volba pomocného zdroje – generátoru; význam závisí na jeho zapojení.'
 if s=='grid':return 'Zda měnič hlásí přítomnost distribuční sítě.'
 return 'Provozní údaj příslušné části zařízení; aktuální hodnotu poskytuje integrace měniče.'

# Override the compact legacy table with readable value cards.
def card(entries,title):
 import json
 text='{% set cz = '+json.dumps(TRANSLATIONS,ensure_ascii=False)+' %}\n## '+title+'\n\n'
 for e in entries:
  id=e['id']
  value='{{ cz.get(states("'+id+'"),states("'+id+'")) }} {{ state_attr("'+id+'","unit_of_measurement") or "" }}'
  read='<font color="#c62828">🔴 **nelze měnit · jen čtení**</font>'
  available='<font color="#16803c">🟢 **můžeme změnit**</font>'
  unavailable='<font color="#c62828">🔴 **nyní nelze měnit · údaj nedostupný**</font>'
  ability='{% if states("'+id+'") in ["unavailable","unknown"] %}'+unavailable+'{% else %}'+available+'{% endif %}' if e['writable'] else read
  text+='### '+e['label']+'\n\n**'+value+'**\n\n'+ability+'\n\n**K čemu to je:** '+explain(id)+'\n\n---\n\n'
 return {'type':'markdown','content':text}

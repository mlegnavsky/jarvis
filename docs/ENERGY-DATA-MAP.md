# Energetika — mapa dat a ověřených skutečností
Ověřeno 4. 11. 2026. Tento dokument čti před dotazy na historii, baterii a spotové řízení. Doplňuj nové nálezy s datem, zdrojem a rozlišením zdrojového kódu / nasazení / živého výsledku. Nikdy nezaměňuj nepřístupnost dat konkrétním konektorem za neexistenci historie.

## Kde hledat
- Repo mlegnavsky/jarvis, produkční větev feat/jarvis-addon.
- Dashboard: jarvis_workspace/hlavni-prehled.yaml (číst přes jarvis.admin/file s aktuální revision).
- Graf Výkon během dne: managed_sources/energy_weather/power-sun.js; metody ids, fetchHistory, dayAverages, archiveDay, fetchStats.
- Podrobná historie grafu: autentizované HA GET /api/history/period/{ISO-start}?end_time={ISO-end}&filter_entity_id={ids}&minimal_response&no_attributes.
- Starší dny: HA WebSocket recorder/statistics_during_period, period hour, types mean. Jde o hodinové průměry, nikoli maxima.
- Energie den/týden/měsíc: stejný WS dotaz, types change, energy kWh, period hour/day.
- Soukromý archiv: managed_sources/energy_archive/__init__.py; HA GET /api/jarvis_energy_archive/day?date=YYYY-MM-DD, vyžaduje přihlášení. Dny Europe/Prague, body t v milisekundách.
- Archivní server: https://laborator.odladeni.cz/energy-archive/index.php; op day se start/end v sekundách. Použít pouze existující autorizované připojení, nikdy nepřenášet hesla z konfigurace.
- Lokální trvalá odesílací fronta: HA .storage/jarvis_energy_archive_outbox.sqlite; implementace managed_sources/energy_archive/store.py. Není to kompletní archiv: potvrzené dávky se mažou. Limit obsahu 64 MiB, při zaplnění se příjem zastaví a existující data zůstanou.
- Diagnostika archivu: sensor.jarvis_energy_archive (status, queued_records, last_ack, error, server). Nominální snímání 10 s, upload 60 s. Přítomnost zdroje neprokazuje úspěšné odesílání.
- Jarvis inventář vrací aktuální stavy. Současný admin kontrakt nemá čtení historie/archivního dne. Potřebujeme podporovanou autentizovanou cestu pro asistenta; nepředstírat, že inventář obsahuje historii.

## Význam entit
| Entita | Veličina / znaménko |
|---|---|
| sensor.inverter_pv_power | Výkon panelů W |
| sensor.inverter_load_power | Spotřeba domu W |
| sensor.inverter_grid_power | Síť W; + odběr, − dodávka |
| sensor.inverter_battery | SOC baterie %; není nabíjecí výkon |
| sensor.inverter_battery_power | Výkon baterie W; při živém nabíjení záporný |
| sensor.inverter_battery_current | Proud baterie A; při živém nabíjení záporný |
| sensor.jarvis_vykon_baterie | Normalizovaný výkon baterie; před výpočtem ověřit aktuální šablonu/znaménko |
| sensor.jarvis_spot_ote | Testovací OTE ceny; nejsou konečné smluvní ceny |
Graf ids() kreslí PV, load, grid, SOC a OTE. Archiv ukládá navíc jarvis_vykon_baterie, ztráty a energetické čítače; proud/napětí nejsou v jeho seznamu IDS.

## Jak ověřit maximum nabíjení ze soláru
1. Zjistit dostupný rozsah historie a stav archivu; uvést prohledané období i mezery.
2. Použít naměřený nabíjecí výkon, ne SOC nebo samotný výkon panelů. Nepočítat špičku z hodinového mean. Statistiky min/max mohou najít kandidátní interval, ne přesný souběh.
3. Pro kandidáty porovnat časově odpovídající PV, spotřebu, síť a případně režim grid-charge. Kontrolovat source_updated, nevydávat zastaralý opakovaný vzorek za nové měření.
4. Ověřit, že v danou dobu nešlo o nabíjení ze sítě. Bez souběžných dat uvést jen maximum nabíjení neznámého původu.
5. Výsledek uložit s časem Europe/Prague, výkonem W, případně naměřeným proudem/napětím a rozlišením zdroje. Historická špička sama nepotvrzuje bezpečný trvalý proud instalace.
Stav 4.11.: maximum zatím NEVYPOČTENO. Historie existuje, chybí ověřené načtení jejích bodů přes připojení asistenta.

## Baterie — identifikace a limity
Účetní evidence Přijaté Fa: https://docs.google.com/spreadsheets/d/1aU6I8tf3qt-rLEw6mw58VZxA1xK1MpCMsUq7HEU9I8g/edit
Záznam 4.6.2026, interní 2026000118, E3M Group s.r.o., FV2026031: Felicity FLA48460-EU (v evidenci 23,6 kWh). Originál faktury nebyl přečten; množství nepotvrzeno.
Oficiální manuál: https://doc.felicitysolar.com/Manual-lang/2.FR/FR-Manual_FLA48460-EU%20Guide%20utilisateur%20-%20Fran%C3%A7ais.pdf
Příloha I / PDF strana 30: 23,5 kWh, 51,2 V nominálně, 44,8–57,6 V, maximální trvalý nabíjecí/vybíjecí proud 200 A, výkon 10 000 W, nabíjení 0–55 °C. Proud závisí na SOC a teplotě. Nezaměňovat krátkodobých 300 A / 15 s s trvalým limitem.
Měnič podle dříve přečtené ELKOV FV6100006049: DEYE SUN12K-SG05LP3-EU-SM2.
Živě 4.11.2026: number.inverter_battery_max_charging_current=100 A a max_discharging_current=100 A. Nastavení není důkaz fyzické hodnoty pojistky; ta nebyla ověřena. Uživatel požaduje nepřekračovat 100 A a dříve autorizoval zkoušku 99 A. Zkouška 99 A zatím neprovedena. 99 A × 53,7 V ≈ 5,3 kW.

## Ruční test 4.11.2026
Řízení managed_sources/spot_control v0.2.0, služby jarvis_spot_control.start_test a stop_restore; sensor.jarvis_spot_control.
Uživatel spustil test kolem 16:40:35 Europe/Prague. Zvolený proud 20 A, pozorováno přibližně 943–947 W do baterie, 17,67 A, 53,72 V, PV 0–1 W, SOC 43 %, teplota 13,5 °C.
V 16:55 ověřeno: controller idle od 16:50:42; grid charging current obnoven na 40 A; baterie již vybíjela kolem 209 W. Je to důkaz ukončení testu a návratu tohoto parametru, ne nový audit všech nastavení.
Při testu zachován Zero Export To CT, export vypnut, offset 20 W. Výchozí soukromý snapshot jarvis_workspace/spot-baseline-20261104.json nepublikovat.
Desetiminutový časovač závisí na běžícím HA; při jeho výpadku nelze slibovat ukončení po 10 minutách.

## Co udržovat
Při každém novém nálezu aktualizovat tento dokument a odkazy z WORK-MANIFEST. Pro implementované API aktualizovat zdrojový generátor operations-manifest, nikoli do generovaného kontraktu připsat neexistující operaci. Do OPEN-WORK patří konkrétní nevyřešené kroky; přístupy, tajemství a historická tvrzení nesmí být domýšleny.


## Nákup a zobrazení — upřesnění vlastníka 4.11.2026
Nákup elektřiny probíhá přes ČEZ za PEVNOU sazbu 5 Kč/kWh (výslovně sděleno Martinem). OTE není nákupní cena. OTE zatím zůstává testovací cenou prodeje; vlastní výkupní sazba bude dopojena. Rozpad DPH, poplatků a stálých plateb nebyl specifikován — nic automaticky nepřičítat ani netvrdit, že uvedených 5 Kč je bez DPH. Pro proměnnou cenu nákupu použít 5 Kč/kWh, stálé platby nejsou součástí výpočtu kWh × sazba.
Jednotky okamžitého výkonu: abs(W)<1000 zobrazit celé W, jinak kW na max. dvě desetinná místa; kWh a Kč/kWh zůstávají. Opraveno ve zdrojích obou spotových karet, regresní příklady tests/power_units.cjs. Živě 17:10:38: síť odběr 11 W, zero_export_power 20 W, Zero Export To CT, export_surplus off, grid_charging_current zpět 40 A. Nastavený cíl 20 W neznamená přesně 20 W v každém vzorku.


## 5 November 2026 — current charging settings and authorization
Owner explicitly superseded previous100 A cap with150 A and authorized adding the narrow Jarvis permission to change max charging. Supported addon_options added only number.inverter_battery_max_charging_current, services unchanged. At06:06UTC fresh max charging150 A and grid charging150 A; native controller0.3.3 requests min(150,inverter maximum), active verified after backed-up restart. Existing temperature/SOC/600s/recovery/no-export checks unchanged. No physical150 A charging test started by assistant. Prior tests observed~78.4 A/~4.29kW at80 A and~97 A/~5.33kW at100 A, not a guarantee of150 A installation behavior. Manufacturer battery max200 A depends on temperature/SOC; Deye12K datasheet max240 A. Full operation/permission scope proof docs/evidence/2026-11-05-charging-button-150a.json. Previous100 A settings and permission gap are historical.


## 5 November 2026 06:25 UTC — owner-selected175 A in both directions
Fresh post-restart settings: maxcharging175 A, gridcharging175 A, maxdischarging175 A. Explicit owner request supersedes previous150/100 limits. Added only max-discharging entity to existing Jarvis permission list through supported CAS admin options; services unchanged. Native0.3.4/button requests min(175,inverter maximum), runtimeidle verified. No assistant-started175 A physical test or trading. Prior150 A test read146.19 A/8.116kW at55.57V, battery15C/inverter42C with no battery alarm/fault; controller idle by06:17:52UTC. Short test observations do not prove long-term installation behavior. Keep BMS and manufacturer200 A/max10kW limits; actual BMS current can be lower. Proof docs/evidence/2026-11-05-charging-discharging-175a.json.

## 5 November2026 — owner grid-import policy
The owner explicitly replaced the former20W anti-export bias with a0W target.
Normal demand is supplied from PV/battery; grid import remains permitted for an
actual energy/power shortfall and explicit grid charging. A0W target is not a
promise of an exactly zero instantaneous meter reading. Charge and sale recovery
must not restore the old20W value from historical snapshots. The original private
snapshot remains historical evidence. The native parameter is Zero Export power,
register104; existing native charge/sale controllers do not include it in their
restore lists. Audited live automations.yaml (three household automations), empty
scripts.yaml, configuration.yaml and managed sales/charge/heating sources: no
periodic writer restoring20W found. The only observed source was the native bias.

## 5 November15:31local — physical bias and daily cash evidence
Native register104 remains20 after two requested0W writes and a1W probe;
optimistic HA0/1 state is not physical confirmation. No scale/offset was found
in the resolved active profile. Do not assert firmware hard minimum without
manufacturer confirmation, and do not write negative/unsigned wrapped values.
The owner's desired normal target remains0W, not yet achieved. Main grid-charge
switch was explicitly turnedOFF; manual charging can still temporarily enable
and restore it. Audit found no recurring writer that restores20W.
Finance now samples fresh signed grid measurements every5s, anchors purchase to
the daily meter at5CZK/kWh, integrates export at each dated quarter's OTE minus
0.30CZK/kWh, and reconciles the private10s archive every60s. At15:31local,
archive_loaded=true/history_error empty, purchase~24.85CZK/sale~0.39CZK estimates,
~0.0753kWh integrated export. Gaps remain gaps and coarse counters are not exact
interval billing. Existing daily history is preserved. Both desktop/mobile Domov
and Energie use the two live monetary sensors. Physical PV-only500W test passed;
later low-PV operation triggered a battery-discharge guard, so stable automatic
PV behavior is not fully accepted. See commissioning evidence for current gate.

## 5 November16:26local — actual native commissioning state
Jarvis administration cap1000 was reached exactly; independentUpdater installed
3.12.5 while preserving all1000 receipts. New capacity10000/read-only count and
409 full-journal error are active. New writes verified again. Native spot0.4.7
recognizes installed profile's LV device codes5/1280; other guards unchanged.
Actual native clock16:24:08 at capture16:24:10 is within2.35s after synchronization.
Native500W/5min window ARMED for16:30–16:35local, SOC floor95/current20A,
ZeroCT/SolarSellOFF, normal other house SOC30/power12000 retained. Do not restart
or claim success until actual export, native expiry and restoration are verified.
Production battery automation still blocked. Daily-recurrence and forecast gates
remain open. See freshest sales-runtime.json, not old93.7s clock snapshot.

## 5 November18:19local — battery sale and conservativehomeplan
ActualSellingFirst500Wnativepilotexported~501–511WwithPV0,battery613–627W.
Observednativepowerdecayafter18:05,butconnectedstopat+25spreventedproving
nativeexpiry; no productionacceptance. Fullnativehouseprogramrestoreverified
includingdelayedreadback.0.5.3sourceadds60sboundedobserverandconservative
history/forecastplan; see freshestcommissioningevidence/source vsruntime.
Plannerusesrolling24hcounterenvelopewhenpowerhistoryhasgapsandcreditsnoPV
inthatmode; missingplanprotects100%anddoesnotbreakcontrol.0Wstillnative20.

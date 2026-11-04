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

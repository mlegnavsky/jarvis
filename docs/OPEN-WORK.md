Warning: truncated output (original token count: 33215)
Total output lines: 819

Warning: truncated output (original token count: 50759)
Total output lines: 1106

# HA sale reserve — 6 November 2026 16:02UTC

Owner clarified: inverter ordinary SOC30 stays unchanged; HA alone stops automatic export at saleSOC60 or the planned end.0.9.1 is active_verified (ha60-prepare/apply-20261106, backup74bbe3f5), automatic command confirmed, armed17:05–17:45Prague, no measured export yet. Only export cap was written during preparation; no TOU/SOC/current programming.

Follow-up0.9.2 source484e3822c999981af88d145cbe1ab3ce4548dffe adds HA-deadline cycle acceptance,683 testsOK/20 skips. Prepared ha60-proof-prepare-20261106, not applied: free1.1GiB below2GiB backup requirement. Need explicit approval before deleting old snapshots161ca94d/1c893f9c (13:27/13:42Prague). No backups deleted. Lease releaseha60-release-20261106 requested; verify before next mutation. Evidence docs/evidence/2026-11-06-ha-sale-reserve-091.md.

# Current: owner settings0.9.0 — 6 November 2026

Approved accordion settings and Czech diagnostics deployed: sourceb032ac35142a4786a6e858e18925342e917d42a5, display follow-up7df0d112248c8e1dfd9c223594c20e809ef4e954. owner-settings-prepare/apply verified active_verified, backup479b3769; sales0.9.0/heating1.2.2; Core2026.6.4 unchanged. Root settings view and display follow-up verified/file_written; exact UI/root/cash readbacks matched. Current policy defaults97PV/20Wbias/home30/resume31/plan60/120min/9300W and21/22C heating retained. Per-card save is revision-bound, persisted and confirmed; sale edits while active are rejected. Save never enables automation or clears guards. No assistant hardware test, unblock or ON operation.

Read-only14:43:33UTC:0.9.0 ready/armed, requested+automatictrue, inhibitedfalse, error empty. Existing selected block15:45–17:45Prague, average8.85647985. This is HA's ordinary owner-requested planned operation, not assistant commissioning. Full production/battery export or native expiry is not asserted from an armed state. Finance live at14:43:37UTC. Heating settings revision exactly preserved. Local679 testsOK/20optional skips plus28heating and8cash tests; DOM draft/CAS/readback checks passed. Chromium rendering was blocked by the executor's Unix-socket policy; pixel mobile/desktop acceptance is not claimed.

See docs/evidence/2026-11-06-owner-settings-090.md. It distinguishes original failure from cleanup and separate latest battery/PV diagnostics. Missing historical original causes remain explicitly unknown.

# Solar — current deployment 6 November 2026

Sales0.8.7 / Spoty1.0.7 is active. Source240876bbdc22ecee4e3c15a48fdb6b02ea9763d3; recovery087-prepare/apply verified active_verified, backup3dd998f0, Core2026.6.4 unchanged. Native HA automation.jarvis_obnova_prodeje is on and calls the atomic resume_confirmed_sale(stop_id), preserving owner Off. At13:35:14UTC ordinary runtime was ready/running PV, automatic/requestedON, inhibitedfalse, healthytrue, error empty, and measured grid−353W. House native reserve30 was confirmed across all six slots. No assistant hardware test/commissioning or backup deletion.

Owner explicitly simplified automatic planned production: selected valid block and actualSOC>60 request existing9300W ceiling; stop at60 or end. Consumption/forecast budgeting and commissioning admission are removed for automatic production; no proof flag is forged and native electrical/health/current/timing guards remain. Manual commissioning gates are separate. Continuous bias target is20W above30; PV surplus from97. Current selected block15:45–17:45 Prague, average net8.85647985CZK/kWh. Do not reinstate obsolete automatic battery_verified/forecast gating from older sections.

UI short plan time/average green, errors red, stopping state explicit. UI HTML/JS/CSS exact readbacks matched. Local669 tests OK,20 optional skips. Native recovery template+handler conditions cover ownerOFF, stale token, unknown cleanup, health and conflicts; independent review closed the owner-Off race by checking intent under the application lock. No artificial pause was induced to exercise recovery on hardware; owner performs actual load/plan acceptance.

Evidence: docs/evidence/2026-11-06-house-group-085.md, docs/evidence/2026-11-06-simple-plan-086.md, docs/evidence/2026-11-06-conditional-recovery-087.md. Older notes below are historical; the earlier SOC100 preservation/commissioning barrier claims are superseded by this owner-authorized implementation. Literal zero grid import or exact20W export is not guaranteed beyond native battery/inverter limits and response tolerances.

# Latest: 4 November 2026 — half duplex 1.3.7 ACTIVE

Owner chose no barge-in. See final section below and docs/experiments/2026-11-04-half-duplex.md.
Do not resume archived AEC/reference experiments without a new request.

# Stav práce — 29.10.2026, po nasazení3.12.0

## Dokončeno a živě ověřeno

- Jarvis3.12.0: updater job fe80a464e071434aa44666c6c80c743c verified, backup20e5ace6.
- Schválené zálohy91ee007c/fd90919a/e7b028f1 odstraněny novým backup_delete API, všechny tři joby verified.36c1e560 dříve odstraněna přes již přihlášenou UI správu. Žádné další zálohy odstraněny nebyly. Protected9659c1f3 a94e01687 zachovány. Po úklidu3.8GiB volných.
- Původní heat101-activate-20261029 zůstává historicky unknown po odmítnuté přípravě; NESPOUŠTĚT znovu. Nahrazeno doloženým novým nasazením níže.
- Topení1.1.0 včetně opravy staré chyby: ops312-heating-plan-20261029 / ops312-heating-apply-20261029 dokončeno10:50:55UTC, phase active_verified, backup4bb0a0c2, Core2026.6.4. Oba runtime senzory potvrdily version1.1.0.
- Parametry bez restartu ověřeny: min_off_s300→301→300, oba joby verified a původní revize nastavení2e33ab6517018b1048706474a7b0d8c69a2db7095f6d48eeba3ecfc35040ecef obnovena. Výchozí dohodnuté podmínky zachovány.
- Živý test souběžného zápisu ops312-lock-conflict-proof správně selhal deployment_owned_by_another_work před zápisem.
- Živý návrat testovacího souboru ops312-rollback-proof-plan: apply verified/file_written (nikoli runtime active), rollback verified/rolled_back_files, soubor deployment-proof.txt opět missing. Produkční soubory tím nebyly vraceny.
- Hlasový smoke: Jarvis zvolen, mute off, satellite idle. Žádný akustický test ani nové nahrávání neproběhlo.
- CI commit724ec35ad0524d557d37697b32ccec1e92a7eebc: oba běhy40860262447/40860252736 success.203 addon testů,21 testů topení,5 firmware-native testů, kontejnerové buildy/startup. Zdroj implementaceb1e4d520d0383b3b9489017b3be04d4a78231afd.

## Zbývající skutečné hranice

1. Trvale hostovaný oddělený Home Assistant ještě není spuštěný. Připravený Docker Compose v testing/compose.yaml. Lokální a GitHub simulace fungují. Odladění konektor potvrzuje PHP správu, proc_open=false; žádný SSH/Docker/VM nástroj ani dříve ověřený samostatný HA runtime nebyl nalezen. Potřeba skutečný připojený kontejnerový/VM host, nikoli pouze subdoména. Nežádat uživatele o vložení hesla do chatu.
2. Retence vrací bezpečný náhled (keep_latest3 + protected); automatické mazání je vypnuté. Schválení čtyř přesných smazání není souhlas s neomezeným budoucím mazáním. Pro automatický úklid nejdřív určit a schválit rozsah/uchovávání.
3. Deployment lease chrání Admin operace, nikoli nezávislý updater, ruční UI ani cizí přímé zapisovače. Ti musí respektovat proces a CAS. Source_commit je deklarovaný operátorem; soubory jsou ověřeny přes konkrétní hash, nikoli vzdálené kryptografické ověření Gitu v Greenu.
4. TV/SledovaniTV/Discovery: funkční přímé URL ani celý kanálový povel stále neověřen. Řeší oddělený TV work; nespouštět souběžný Core restart bez koordinace.

## Pro pokračování

Čti AGENTS.md → WORK-MANIFEST → OPERATIONS-3.12.md → operations-manifest.json. Ověř deployment_status a aktuální runtime; nepřebírej staré hodnoty jako živé. Všechny další změny běžných parametrů dělej heating_settings, ne editací konstant a restartem. Pro nové zdroje používej připravený bundle + runtime checks. Doplňky/Core/OS neupgradovat hromadně jako vedlejší efekt údržby.

## Jarvis Lab na Odladění

Zdroj portálu: managed_sources/staging_portal; cílová cesta https://plaginy.odladeni.cz/jarvis/. Veřejné bezpečné testovací podklady, snapshot výsledků, odkazy na Git a CI. Není to spuštěný HA runtime; tato mezera výše trvá. Žádné produkční údaje ani veřejná zapisovací operace.

## Laboratorní pipeline

Implementace: scripts/build_release_archive.py, scripts/publish_lab_snapshot.py, testing/lab-public a publikační job Check Jarvis. Přesný kontrakt a zbývající aktivace: docs/LAB-AND-RELEASES.md. Webhook i automatické nasazení ověřeny: commit30348df692f92e6833a926254eba3a9e933669f7, push run40891692482 success; HTTP katalog i SHA256 obou ZIPů odpovídají. Soukromá kopie HA záloh mimo Green stále není zprovozněná. Žádné soukromé zálohy neposílat do public webroot ani public Git.

Vlastník vybral výhradně vlastní server pro HA zálohy. SFTP Storage je nativně podporovaná cesta; serverový účet/soukromá složka a dostupnost SFTP dosud neověřeny. Konektor nemá správu Plesk účtů a Admin neumí založit config flow. Přesný postup a přijímací podmínky: LAB-AND-RELEASES.md. Neukládat soukromé zálohy do veřejného webu.

## Own-server backups: HTTPS implementation (29.10.2026 evening)

SFTP external5.9.58.145:22 timed out from user Windows and native HA setup. Plesk terminal works internally127.0.0.1:22; restricted account has no /proc or SFTP client, reseller UI has no firewall. Private /ha-backups exists owned jarvis_lab and outside httpdocs. Stop repeating SFTP guesses.

Implementation path: native HA WebDAV to constrained PHP endpoint; docs/PRIVATE-BACKUPS.md is the bootstrap, acceptance, rollback and limits. Private credentials must be placed through owner Plesk session; no current direct tool can access this isolated subscription's private folder or start a new HA integration flow. Endpoint and passing CI are not proof of an actual Green backup. Keep status activation_pending until actual encrypted upload completes; no automatic deletion authorized.

## DEYE read-only dashboard — 29.10.2026 19:17 UTC

Production source 7c34a435639c6ccb1988608956adcf8f4ea02415, managed_sources/deye_dashboard/prepare.py. Existing authenticated jarvis_action supports service jarvis.admin, entity_id jarvis.system: data={action:read,query,target} or data={action:change,operation,arguments}. Do not mistake absence of separate admin tool for absence of deployment access.

Prepared deye-plan-20261029 and applied deye-apply-20261029: state verified, phase file_written, no restart. Live file jarvis_workspace/hlavni-prehled.yaml read back exactly, revision11b058ce1a3443083e3b0cc56dec1e74fb52cd30aa49c27c938be4b631470619. Prior image held in deployment plan for CAS rollback. New view deye-baterie and Energy navigation button; all27 prior views preserved. All57 entity references exist in fresh inventory; YAML/Jinja parse checks passed. No device settings changed. Native YAML view loads on opening/reloading dashboard. Visual browser verification remains unperformed: separate cloud browser is at HA login, not an authenticated session. Admin config_check timed out at gateway; subsequent status confirmed backend connected/version3.12.0; no restart attempted. No full inverter-settings backup created. Financial spot result intentionally unavailable pending verified tariff/fees. Dashboard shows live actual values, not lab sample values.

## Complete DEYE catalogue — 29.10.2026 20:50 UTC

Source4789474968f06828b32d87aeb3fb9b8eb5790dca; prepare deye-v2-plan, apply deye-v2-apply verified/file_written. Readback of all3 files matched exact bytes. Native YAML includes deye-baterie.yaml and deye-vsechny-udaje.yaml keep each below256KiB. New detail subview has all203 currently exposed inverter entities:100 measured/status and103 write-capable domains. All displayed values are live templates, no device write actions. Red label means integration exposes a write; unavailable/unknown items do not claim a currently confirmed change. No actual inverter writes tested or performed.27 unrelated views preserved;3 catalogue/template tests plus all YAML/Jinja/entity/include checks pass. Visual authenticated UI verification remains unavailable from cloud browser; file deployment is verified, not a rendered screenshot.

PV1/PV2 voltage/current/power and U*I display added. Real inverter losses distinguished from curtailment. Open-Meteo existing hourly GHI can show a horizontal25C reference only, NOT lost power: roof tilt/azimuth and PV1/PV2 array split are unconfirmed after context search. Therefore actual unavailable generation in W/kWh is deliberately not fabricated. Need those geometry inputs plus calibration and time-aligned history for a usable curtailment estimate. Source references: https://pvpmc.sandia.gov/modeling-guide/2-dc-module-iv/point-value-models/pvwatts/ and https://open-meteo.com/en/docs/historical-weather-api . Full model and cumulative curtailment sensor are NOT implemented. A full inverter-settings backup is NOT created by this dashboard change.

## DEYE presentation v3 — 29.10.2026 21:28 UTC

User changed capability colors: available write green, measured/read-only and unavailable write red; red is explicitly NOT a fault indication. Added graphic roof/battery banner,12 category subviews with individual live value cards, plain Czech help for every203 field and glossary. Main overview and catalogue menu link categories; all device actions remain absent. Source bf2bc9d1dbf67b9be0fe6a04572be3d657bd1e5a; generator enhance.py.5 targeted tests pass;15 YAML/Jinja/include checks resolve and203 unique catalogue fields preserved. Combined prepare deye3-plan rejected HTTP413 before creation (admin_job_not_found confirmed), no mutation. Split into deye3-children-plan/apply then deye3-root-plan/apply, both verified/file_written. All15 live file readbacks match byte-for-byte. No restart, no inverter settings changed. Authenticated rendered UI remains not visually verified.

IMPORTANT: owner has now confirmed22 panels, southeast orientation,45-degree tilt,2 strings of11. With previous450W specification this gives9.9kWp total,4.95kWp/string. Do NOT ask again for those inputs. They appear in banner and replace stale missing-geometry text. Curtailment calculation itself remains NOT active: next work is tilted irradiation/temperature model, aligned measured power/calibration and accumulated energy. No actual lost W/kWh claim is made by current reference-GHI panel.


## Denní energetický graf — 30.10.2026

Upraven managed_sources/energy_weather/power-sun.js: pražský kalendářní den 00:00–24:00 včetně DST, přepínače nahoře, hodnoty pod kurzorem a časový jezdec s klávesnicí. Veřejná laboratorní ukázka /energy/ používá tentýž zdroj a pouze označená syntetická data. Green není v tomto kroku změněný. Node testy hranic dne, DST a nedostupných hodnot a Chromium interakční test jsou povinné před publikací. Předchozí source caa9627 nepublikován kvůli testu kurzoru; browser opravy 0c8e11d prošly. Poslední oprava zachovává přesné now při výchozím výběru, aby zaokrouhlení nevytvořilo budoucí čtení. Nasazení ověřit podle aktuálního CI a HTTP obsahu /energy/.


### Green deployment receipt — 30.10.2026 12:07 CET

Source ae64421be01c7db5d8cda1edc13097d7a996b208 (CI push41045240503 all jobs success, laboratory HTTP exact match). Native bundle daychart-plan-20261030 prepared and daychart-apply-20261030 verified/file_written; activation none, no Core restart. Green www/jarvis-power-sun.js read back byte-for-byte equal to tested source, SHA256 1b84013f71f9dcde44c08052a6fe00bcad72379ffe880a97eb76bf8abbbe7fbc. Existing dashboard references custom:jarvis-power-sun and is unchanged. Before-image retained in prepared plan for explicit rollback. Browser reload required to replace already-loaded custom element. User browser/runtime rendering on Green not independently observed; unauthenticated external HTTP attempt received403 and is not proof of frontend failure.


### Browser acceptance and resource activation — 30.10.2026 12:23 CET

Owner screenshot showed old runtime despite verified JS write. Missing step: update existing storage-mode Lovelace resource URL, not only file bytes. Through owner-authorized signed-in native UI changed /local/jarvis-power-sun.js?v=1.2.0 to ?v=f75a397. Final JS source f75a39736b81e383bf5589a2767720c3428d4371 fixes past/current cursor rounding on repeated render; Node regression passed. Green bundle daychart-livefix-plan-20261030/apply verified, readback SHA256 a228e5d17de63f64b531fdf2ae0cf34214a577f4131ec5836b04ae2ac3cb03a4. Native resource table confirmed final URL. Fresh navigation to /hlavni-prehled/energie visibly showed Výkon během dne, 00:00–24:00, top toggles and real measured values (5043/2650/11 W); screenshot captured. No Core restart. Browser mobile/app reload itself remains user-side; prior CI Chromium mobile-width and interaction tests passed. Resource management is missing from current Admin API and should be added as bounded native WS operation in a separate improvement, not bypassed via arbitrary storage editing.


## Expanded daily chart — 30.10.2026 12:51 CET

Source3b2c1e8f7c765ef033600e8ae9e58b9911f2045a; push41050673874 all jobs success including Chromium day navigation/future battery/native published spot/mobile/focus and Node DST/null-price/race checks. Added battery %, market spot Kč/kWh without VAT before trader fees, independent scales, date and prev/next/today. History via HA recorder incl spot-state history; native published quarter-hour rows override history (including missing price). Future measurements absent. Green energy-expanded-plan-20261030/apply verified/file_written, exact readback SHA256 a53142ea612cc5776b29426c1aad57496f4daa1d9878e2b3c217ac215a547a88. Native UI resource changed to /local/jarvis-power-sun.js?v=3b2c1e8; fresh energy page visibly confirmed battery90–91%, spot5.6Kč/kWh and six toggles. Native previous-day test29.10 23:59 showed battery71%, spot5.9Kč/kWh and measured powers. Tomorrow31.10 correctly missing measurements and unpublished price. Returned to today. No restart; lease released. Historic availability limited by recorder retention; future price availability by OTE publication and existing sensor refresh.


## Energy speed, battery gaps and weather strip — 30.10.2026 13:05 CET

Source c50da3fbd76b39c9b109c934348f0137caac0f8d; push41052281828 all jobs success including Chromium weather strip/temperature and previous interaction tests, Node cached-day reuse/overnight partial refresh/battery interpolation/no extrapolation/decimation peak-gap preservation. Memory cache7days,120s current/24h completed-history snapshots, relevant-entity render filtering/coalescing and binary-search cursor; no server first-fetch latency guarantee. Battery gaps joined with dashed green estimate and≈ cursor between actual endpoints only. Weather/temp strip aligned to plot uses existing Open-Meteo forecast sensor; unavailable past weather left blank. Explicit cursor stays pinned, default cursor advances with live readings. Green energy-weather-speed-plan-20261030/apply verified/file_written; exactreadback SHA2561c0f9de98fefbf10471193b766b631b5e2c75e3d2bd462f057462a54e65ef293. Native resource URL ?v=c50da3f confirmed in UI; fresh energy page showed weather/temperature cells, real values,21 dashed battery gap bridges and current forecast summary. Screenshot captured. No Core restart; lease released. Cached history is memory-only per card/browser session; opening a day for first time still queries Green. Historical weather persistence not implemented.


## Energy periods, compact night weather and Moon — 30.10.2026

Source680f9c398a64cd7822a76636b19ccc5f962e0705; push41055361225 all jobs success incl Chromium period controls/compact weather and Node calendar/stat-sum/missingstats. Native recorder statistics_during_period change/day (hour for historical day), kWh; current-day bucket replaced by live today counters, partial historical notice. Added Den/Týden/Měsíc/Rok and grouped bars. Compact inline temperature/icon, night moon phase from existing SunCalc and illumination%. Green energy-period-plan-20261030/apply verified/file_written, exactreadback4761d231e19abcb50c88d390c0904abcb19502469278e9ab087048d718f953d7; UI resource URL?v=680f9c3 confirmed. Fresh live native UI: today19.1/10.2/0.1/0kWh; week65.9/44/2.8/0.2; month410.5/367.5/54.9/0.7; year1418.1/1105.7/86/4.9 (production/load/import/export). Totals cover available statistics only, not proof of full-year acquisition nor paid sale. Native export sensor5kWh total,state_classtotal_increasing verified. 00:00 hoveredMoon waning82% and compact inline°C verified; screenshotscaptured. Source sensor spot fetched2026-10-30T13:19:36+01, tomorrow_status OTE zatím nezveřejnilo požadovaný den; no fake tomorrowprice added. UI missingprice copy now distinguishes source not yet supplying requested day;15minpoll remains. No Core restart.



## Home source, manual-off and batteries — 30.10.2026 12:59 UTC

Source 420ab11f6ca5113939c215704df79e0ac1ae5173; both CI runs 41058098878/41058107981 succeeded, laboratory publish on push succeeded. Heating 1.2.0: actual aggregate source rather than high-SOC exception, mixed PV+battery applies equally to both loads. Current measured example PV1108 + discharge2464 + grid8 = load3292 + inverter losses288 W. Native sensor.inverter_power_losses added visibly; timing differences can still affect snapshots.

Home custom module registered /local/jarvis-home-status.js?v=420ab11; www SHA25634d0b75efddb2ea3882722a7cfca1156da08228db3f0c96dda52b97dabecfea5. Generator preserves private dashboard includes/actions; private full dashboard not committed. Door lockedgreen/openorange, jammed/unavailable/unknown or battery<25 red. Device battery overview excludes household storage. Room sensor currently reports0%; warning rendered red (report is not an independent chemical battery measurement).

Deployment home-status-core-prepare-20261030 / home-status-core-apply-20261030 active_verified at12:55:21UTC; Core2026.6.4, both sensor runtimes1.2.0, automation on. Backup51a23085 (659.36MB) created; free space2.5GiB after deployment. One Core restart performed. Deployment lease released verified home-status-release-20261030. Saved before-images support explicit rollback, not exercised on production.

Manual OFF persists to next Europe/Prague midnight or explicit ON. Existing automation runs every15sec so midnight reevaluation is scheduled. Live obývák test: OFF confirmed state off, manual-off icon and label; ON clears hold and becomes manual; set_mode living auto via native developer actions restored automatic source label12:58:40UTC. Original automated mode restored. Midnight/DST behavior simulated, not wall-clock observed. 27 heating engine/adapter tests and8 JS checks pass; peer review no blockers. Delayed contextless auto confirmation retained until acknowledged/overridden; physical off matching outstanding auto off is inherently ambiguous without event provenance. Explicit service commands always override pending target.

Follow-up live state: logbook confirms a separate external OFF at13:58:50CET attributed to Martin, after the test restored auto at13:58:40. Preserve this new override: obývák off/manual_off until midnight; do not undo it. Room battery refreshed from0 to35% at12:58:29UTC, so its low-battery red indication correctly cleared. Initial0% was the actual reported state during verification, not a lasting empty-battery diagnosis.


## Energy chart polish and OTE delivery-date fix — 30.10.2026 13:31 UTC

Source afdf7385e542a880852f25d6d5b0001e9fd97a35 (implementation64569f1, selector-test quoting fixafdf738). Push CI41062521362: all test, energy-chart Chromium, container, backup-dav and laboratory publish jobs success. Original64569f1 browser test failed only on an unquoted numeric CSS selector; product was not deployed until corrected test passed. Local browser runtime download unavailable (zero-byte archive); CI real Chromium interaction test supplied browser verification.

OTE root cause proven by direct primary-source HTTP: date=2026-10-31 returns title30Oct; report_date=2026-10-31 returns31Oct with96 quarter-hour points. New URL helper uses report_date and still validates delivery date, DST interval count and order. Native energy_weather1.0.1 adds runtime version attribute, same15min polling. Not a guessed forecast; published day-ahead market prices without VAT/trader fees, using latest CNB exchange rate. Tomorrow row availability rendered and verified on Green31Oct chart:191 purple SVG line elements (96 intervals+95 connectors), noon readout5.4Kc/kWh. No future battery/PV readings fabricated.

Aggregate charts: full seven-day/month/year calendar, Czech day/month dates, immediate persistent values with selection band/cursor, series toggles, touch pointer and keyboard slider. Missing/future buckets stay null. Bounded24-period stats cache (completed24h only if captured after end; active/incomplete2min), existing14-day memory history cache, request guards. Detailed history no longer fetched while viewing aggregate periods. Old/purged daily series independently use recorded hourly means; explicit interval null boundaries preserve missing hours and disable battery gap interpolation in hourly mode. First uncached request still needs HA database; no universal instant-load promise.

Live acceptance: week86.4/55.8/3.0/0.2kWh, selectedTue27Oct20.1/10/0.3/0.1. September359.2/269.2/10.7/1.5kWh; Czech axis1.9.,4.9.etc, selectedWed2Sep7/4.3/0.3/0.0. NavigateAug/backSep restores cached totals without loading notice. September1daily graph shows recorded hourly fallback (battery82% at selected point). Device temperature-sensor battery confirmed35%; unknown/non-numeric never becomes low-battery red. Home battery warning code unchanged.

Green bundle chart-polish-prepare-20261030 / chart-polish-apply-20261030 active_verified13:27:09UTC, backupae873253, one Core restart2026.6.4; both spot/weather sensor runtime1.0.1 ready, both heating runtimes1.2.0 intact and automationon. Living manual-off hold survived restart. Resource /local/jarvis-power-sun.js?v=afdf738 registered; live JS exact readback SHA2561e5518b8af000facdfe3dd3e71c7342efbcac387e1c49ee153fc30c026b6de8a. Lease releaseverified chart-polish-release-20261030. Disk now1.8GiB, below next backup2GiB preflight; future restart/update must resolve space first, don't retry blindly or delete unapproved backups. Saved deployment before-images available for explicit rollback; rollback not exercised on production.


## Continuous old hourly plots and solar planning — 30.10.2026 15:10 CET

Frontend source3de241052026746fb4b9c199d0692d77d1645846 (implementation1c96996, browser test scrollingfix3de2410). CI push41068433220 all jobs success inclChromium andlaboratory publication. The original new browser assertion failed because added content pushed plot outside viewport; test now scrolls plot into view before pointer events. No product files applied until pass. Peer review no blockers; Node incidence/day/DST/cloudwindow/contiguity tests pass.

Adjacent retained-hour means connect as continuous horizontal+vertical steps. Only actual interval gaps keep nulls; no fabricated measurements/zero fill. Green9Oct2026 checked: each PV/load/grid/battery SVG path has one M segment (all four continuous). Existing detail/hour labeling retained.

Geometric solar peak: SunCalc position at existing Žitenice50.555N14.156E; ownerSE modeled135deg north-based azimuth, tilt45deg. Cosincidence minute search abovehorizon, bounded400-day cache. Daymarker lies on Sun curve/rightdegreesaxis, not on poweraxis. Week/month have independent small golden markers below baseline for each day, selectionreadouttime. Year aggregates months, no misleading daily marker. Computed9Oct10:47CEST altitude27.3deg;30Oct09:44CET altitude20.3deg. This is best geometric incidence, not clear-sky irradiance max or a guaranteed power peak. OwnerSE is nominal, not surveyedexactbearing; obstructions/clouds may shift actual peak.

Visible weather heading Žitenice, forecastcloudcover% added. Existing Open-Meteo shortwave_radiation (horizontalGHI, precedinghourmean) selects planninginterval; display W/m² andcloud%, explicitly not panelkW. No satellite tracking or new API/backend added. Live30Oct best forecastinterval12–13CET372.5W/m²/cloud57%. Historicalforecastabsent remainsabsent. NativeUI proved explicitlocality andalllabels; weeklyDOM7dailygoldendots.

Deployment solar-planning-prepare-v2-20261030 / solar-planning-apply-20261030 verified/file_written; JSexactreadbackSHA2560c7b873cca1047dc0140fddc2ed5cdcf9829c2a9294692b7fd42b4e658e801f6. Lovelace /local/jarvis-power-sun.js?v=3de2410 registered andnewcardrendering observed. Activation none: noCore restart or backup created. Heating/OTE/backendunchanged. Lease solar-planning-release-20261030 verified. Prepared firstplanwasneverapplied; v2referencespassedsource. Beforeimage available for explicit rollback. Free-spacepreflight constraint from priorstep remainsforfutureCorechanges.


## Compact panel information — 30.10.2026

Source b4c2cd73bc7f8abe728f1f8e2baafd4cb8ada0e1; push41076499794 all jobs success. Verified invoice FV6100006049 dated24.03.2026 lists22 DAH DHN-48Z16/DG(BB)460Wp,1762x1134mm:10.12kWp and43.958376m² excluding gaps; earlier450Wp/9.9kWp assumption was wrong. Daily chart solar-planning explanations now behind ⓘ, mouse entry/exit uses native details state, touch/keyboard supported. Corrected Couvající Měsíc to Ubývající Měsíc. Green chart-info-final-prepare-20261030/apply verified/file_written, activation none; exact readback SHA256 b8ea0f4cdbdcaa225855cbe7499489dea9840aeaf43804593334665b122067e4. Native resource /local/jarvis-power-sun.js?v=b4c2cd7 confirmed. Fresh live UI hidden-by-default and keyboard details contents verified, screenshot captured. No Core restart. Other DEYE banner's older assumed450Wp specification is outside this chart edit and still needs correction if present.


## Stable date picker — 30.10.2026

Source f8be9c41b7a78dbd9904b2dca061e193ebfe0881; push41077614293 all jobs success including Chromium input identity under live render and refresh after blur. Root cause: render replaced shadowRoot.innerHTML on live sensor/history/statistics/resize updates while date input focused, closing native date picker. render now defers while input[type=date] is active, retains incoming data, resumes on blur; change captures date and blurs before chooseDay. Shared binding covers day/week/month/year. Node regression failed before fix and passed after. Green calendar-prepare-20261030/apply verified/file_written; exact SHA256 a969b40e522cbbf9fbb25675700fd591cef825e2ff40b52c9ec723409735dbdd. Resource ?v=f8be9c4 confirmed. Live focused date stable across updates, historical selection and return Today verified. Native browser popup itself not exposed by cloud DOM tool; input replacement regression covered in Chromium. No Core restart, lease released verified.


## Committed date and lunar wording correction — 30.10.2026

Source ad7d248674850dd94b239c1183861b9b6782f602, push41079919100 all jobs success. Prior focused-input guard also blocked committed date if native picker retained focus. chooseDay now explicitly forces render without restoring old focus; shared input/change/blur commit handles valid changed dates, retains guard for background refresh. Node failing regression reproduced retained-focus commit then passed. Chromium regression selects2026-08-29 using input event while focused and asserts immediate subtitle and no blocking focus. Green date2-prepare-20261030/apply verified/file_written; exact SHA256329f29cc331f3fa5f4f55d66e5f12eab6dafa65f1a333e95b2c7535aaaf7dcf6. UI resource?v=ad7d248 confirmed. Live direct date fill29Aug immediately changed subtitle and loaded11.9/9.1/.3/.1kWh with hourly fallback; no prev-next workaround. Moon main readout now phase only, numeric lunar illuminated-disk fraction stays clarified in tooltip/info. Live00:00 showed Úplněk without percentage. Recorder configuration has no purge_keep_days override; default10day raw retention, older hourly means. No historic raw measurements fabricated, no retention restart/config change. Server fine-resolution archival remains future work. No Core restart, lease released verified; returned Today.


## Permanent private energy archive — prepared, NOT collecting — 30.10.2026

Approved design:10second graph energy/SOC/charge/discharge/loss and cumulative counters, original weather and spot publications; private permanent own-server archive, durable local queue, authenticated HA graph query. Source b02c8c21be01bf6690fa5dbd8208ecda1403b250 (initial88f9c0a). CI push41083211396 all jobs success incl3 SQLite queue tests, real PHP HTTP auth/idempotence/hash/day/as-of issuance tests, Chromium graph, full suite/containers and Plesk publication. Peer review fixed recorder-failure dependency and forecast issuance selection; focused review no critical/important blockers. Current code/docs in managed_sources/energy_archive, testing/energy-archive, docs/ENERGY-ARCHIVE.md and plan.

Live endpoint https://laborator.odladeni.cz/energy-archive/index.php returns401 with Basic challenge and no data to unauthenticated request. Actual private server SQLite write/read/free space NOT tested yet; no household archive records uploaded. No native code/config files written, no Core restart, no collection begun. Prepared native plan archive-native-prepare-20261030 verified/prepared, revision971debed2ac80e654d6ea0f8c6b612fe9541e9e3d9305ea970c87a8634143c16; sourceb02c8c21, Core2026.6.4, activationcore_restart, check sensor.jarvis_energy_archive ready/version1.0.0. Files three newcustomcomponent files, configCASb70e1e496a02ffa078924fd8f3fe411b864173ca3ae33c9919915c90837455ec and chartCAS329f29cc331f3fa5f4f55d66e5f12eab6dafa65f1a333e95b2c7535aaaf7dcf6. Activation not attempted: fresh storage1.8GiB vs required2GiB backup preflight. Do not bypass protection or retry backup blindly.

Await explicit owner approval to permanently delete only obsolete partial backup4bb0a0c2 (Jarvis before remote administration,2026-10-29T10:46:12.254606Z,631.6MB,unprotected,revision42bdd3e8643b93683b25e8a26fd8d412d68f7cde3569ebbdd8122ec070e4f26d). Preserve latestae873253/51a23085 and protected systemdafb1c61/test2bb62eaf4. Candidate preview is not deletion authorization. Once approved re-read candidate/revision/storage, delete exactslug, verifyabsence/free space, freshlease/revalidateplanCAS, applyprotectedCorebundle, verifyactualserverACK/datareadback/sensor/UI/resourcecacheversion, comparemeasuredburstspace, then release. Existing saved lease released; acquire fresh before apply. Other changes/restarts are not authorized by this approval question.

Outbox64MiB cap pauses capture rather than discarding unacknowledged rows; fullqueue/integrationfault must remain visible. Forecast rows remain predictions, originalissued_at retained, historical day selects latest weather issue before day start (earliest available fallback), shownissuance. Same-server audit batches are not independent disaster backup; server-level independent backup is not verified. Deleted historic raw data cannot be restored and recorder/cloud backfill not implemented. Final completion requires real production append/retry/readback, not code/CI only.


## Voice wake and delivery repair — 30.10.2026

Released3.12.2 source0c377ba8fd88adefb7bd53d5a703baea35591fe5. Native required pipeline fields corrected after3.12.1 failed before mutation; prior unknown voice job was reconciled against unchanged pipeline before a new implementation was used. Final native voice change verified with full readback. Existing private wake weights preserved, sensitivity manifest tuned and OTA compile/upload/reconnect/config-hash match verified. Energetic dryly playful companion source and its recovery copy activated with native runtime verification; terminal idle, unmuted, explicit Jarvis pipeline and default end detection retained. Actual model-backed text recall/continuation/stop test passed.239 addon tests (20 skipped),42 companion tests, manifests and full CI/container builds passed. Local operational receipt is retained on Green. Acoustic wake acceptance and subjective voice/humour acceptance remain owner-side; arbitrary speech barge-in and full duplex remain unavailable. Uncertain voice identity still deliberately limits personal conversational context.


## Anička live preview — 31.10.2026

Owner approved deployment/testing. Feminine Czech persona Anička, feminine fixed
memory/light replies; existing Jarvis backend preserved. Source publication is
not deployment. Pipeline TTS ash→nova and revision-bound activation planned.
43 companion and20 diagnostics tests pass; independent review found no Critical
or Important issue. Minor deferred: name probe is a substring heuristic; inspect
actual live identity answer and prompt hash before confirming persona activation.
No new acoustic wake model or arbitrary speech barge-in is implemented. Use
physical satellite button for preview if existing wake model is unreliable.
Native pipeline label Jarvis remains a technical backend label.


### Anička preview — live reconciliation 31.10.2026 16:20 UTC

Source c90c482c289cfd6eee61d0529eea513cee5fc123 deployed to Green; backup3791071e.
The apply job anicka-preview-apply-20261031 remains failed/runtime_check_failed
and plan activation_failed: one-shot startup check ended16:19:20.434585Z;
HomePod sensor reached configured16:19:21.765894Z. No blind retry/restart.
Independent post-start verification:8/8 source+recovery readbacks match; loaded
persona hash matches; actual model answer `Jsem Anička. Jak ti mohu dnes pomoci?`;
recall/follow-up/stop test passes. Pipeline voice nova verified after restart;
pipeline technical label remains Jarvis. CI41218705751 all jobs success.

This is a live persona/voice preview using existing adapters, NOT deployment of
the new simulation controller. Physical audio/microphone behavior and voice
preference are unverified; use satellite button for first test. Aničko acoustic
model and arbitrary speech barge-in are NOT installed. New approved voiceprint
authorization from simulation is not active; existing permissions unchanged.
Full receipt: docs/evidence/2026-10-31-anicka-preview.json and private local copy
jarvis_workspace/anicka-preview-20261031.json. No recording enabled.


## Enrollment outlier fix —31.10.2026

Owner reports registration cancelled at second sample; policy deleted pending
progress on a single inconsistent embedding. New source rejects that sample and
retains prior accepted samples; thresholds/three-sample requirement/expiry
unchanged. Report version2 includes pending counts/deadlines and last decision,
without names/vectors.23 regression/policy tests pass; independent review found
no Critical/Important issue. Diagnostic snapshot iteration uses copied slots.
Source publication is not deployment; runtime verification follows below.


### Enrollment fix live —31.10.2026 16:47 UTC

Source22ab75d119160496721f323b4959e869fe3e3fa3; applyenrollfix-apply-20261031
verified/active_verified16:47:04.437165Z, backup1f1a5cc3. All6 live+recovery files
read back exact. Running report version2/enrollment_policy
reject_sample_keep_progress_v2, backend/native probe ready; profiles0, pending0
following restart. Local23 tests and full CI41220950606 all jobs success.
No household voiceprint was created by tests. Owner must start enrollment once
again after restart in quiet room,5–8s samples; physical acceptance remains
pending. A rejected outlier now preserves accepted progress, not an accuracy
claim for the household model. Full-duplex/wake model/short-turn context issues
remain separate open work; this fix does not resolve them.


## Conversation/enrollment stability source —31.10.2026

Named enrollment no longer requires a usable initiating embedding; initial
command counts0 and still needs3 consistent long samples. Local partial-name
and voice-status responses prevent invented LLM enrollment success.26 policy
regressions pass. HomePod native abort hook preserves conversation and resumes
once after confirmed stop, with owner/session/mute/shutdown guards;32 local tests
pass, untouched migration test unavailable locally due missing Jinja2. Full CI
required before activation. Independent review no findings. Does not implement
arbitrary acoustic speech detection or the Aničko model. Temporary live settings
verified: primary wake Jarvis→no_wake_word, second already none; sensitivity
Very→Slightly. Physical button begins dialogue. Publication is not deployment.


### Conversation stability live —31.10.2026 17:12 UTC

Sourceab3728f2df6963ca46b59401ca20b40bd22d9f95 applied by
anicka-flow-apply-20261031 verified/active_verified17:12:33.243143Z;
backupaee76900,10/10 live+recovery readbacks exact. Running speaker reportv3
ready, trigger_requires_embedding=false, native model probe passes, profiles0
and pending0. Running output reportv2 configured/native_abort_resume=active;
resumed0/failed0: physical abort/resume has NOT yet been tested. Firmware wake
slots both no_wake_word, sensitivity Slightly; unmuted microphone. Owner uses
physical button to begin. No Aničko acoustic model or arbitrary speech barge-in
is implemented. CI41222892528 all jobs success, including complete test suite
with missing local migration dependency installed. Independent review clean.
Next: single named enrollment command must create pending session0/3; then each
5–8s sample checked in report. No household embedding/profile was fabricated.
Per-turn uncertain identity/context clearing remains separate open work.


## Current HomePod volume and comprehensive audit —31.10.2026

Volume source now snapshots actual HomePod level for every answer instead of forcing legacy speech_volume. Zero/mute skips audio; unknown/invalid level fails without raising volume. Native RAOP priming retained; no end-of-answer setting restore. Output reportv3 exposes follow_homepod policy, observed mute/volume and latest decision.35 local tests pass; migration dependency Jinja2 absent locally, full CI required. Independent review no blockers. Publication is not activation.

Actual model text continuity/name/stop probe passed. Synthetic Piper phrases tested against three STT engines: OpenAI0.577–1.135s with two exact phrases and one Slovak semantic equivalent; local Whisper5.526–6.772s, speech-to-phrase failed to transcribe two of three. This small synthetic probe is not household acoustic accuracy. Self-test call returned unknown gateway outcome, subsequent report proved completed; not replayed. Native speaker model probes pass but household profiles remain0. No microphone turn since17:12 restart; physical abort/resume and voice enrollment unverified. Aničko model/arbitrary-speech barge-in unavailable; anonymous per-turn context restriction remains. Host detailed resources stage unavailable; Core healthy,29 integrations loaded, automatic-backup historical repair warning,3.5GiB free before deployment. No backups deleted, provider switched or recording enabled.


### Volume fix live receipt —31.10.2026 17:36 UTC

Source e95c9e90cf0d6c5b35fdb85ade7d7917511aef31; vol-apply-20261031 verified/active_verified17:36:03.073608Z, backupfc76d3f2.4/4 source/recovery readbacks exact. Runtime outputreportv3, adapteractive, volume_policyfollow_homepod, legacy35%ignored, observed0%, mutepropertyunknown(null); no physical audio test afterrestart. This is actual setting preservation, not acoustic loudness normalization. All38 HomePod tests passed locally after installing missingJinja2; fullCI41224820337/41224826220 success. Pipeline nova unchanged, speakerready/nativeprobe passed but householdprofiles0. Disk2.9GiB; lease releaseverified. No backup deletion or firmware/Core upgrade. Previous provisional claim 'no mic turn since17:12' was a snapshot; predeploymentoutput later recorded one completed run. No acoustic proof inferred from that counter. Remaining limitations above persist. Full machine receipt docs/evidence/2026-10-31-volume-diagnostics.json; owner received detailed private report.


## Authorized voice 1.1.0 — 1.11.2026
Zdrojová implementace oprávnění podle stabilního hlasového ID, jednorázových povelů, oddělených kandidátů, chráněných kotev a automatického provozního manifestu. Nasazení je doloženo samostatnou účtenkou až po ověření běžícího reportu.
Otevřeno: skutečné domácí testy shody; nezávislé negativní/replay vzorky; detekce přehrávky; hotové a fyzicky ověřené akustické modely Aničko/zamkni/odemkni; ověření kapacity firmwaru a zachycení krátkého slova pro identifikaci. Nesmí se hlásit plné probouzení nebo perfektní hlasový otisk. Modely se trénují ve větvi training/anicko-20261101.


### Hlas 1.1.0 — ověřené nasazení 1.11.2026
Čti také jarvis_workspace/voice-deployment-receipt.json. Původní job voice11-apply-20261101 skončil runtime_check_failed při startu, ale následné čerstvé ověření potvrdilo 28/28 souborů, report runtime1.1.0/ready, native_intent_guard=true, jeden autorizovaný profil a zachované kotvy. Žádný zápis nebyl opakován. Neopakovat apply pod novým klíčem. Manifest jarvis_workspace/voice-system-manifest.json se sám obnovuje; jeho hashe popisují soubory na disku, nikoli nezávislý důkaz aktivace. Skutečná domácí přesnost a wake modely zůstávají neověřené; detailní meze a výcvikový běh jsou v účtence.


## Voice matching diagnosis — 1.11.2026, source prepared

Owner's 8.23s voiced turn completed inference but failed `uncertain_windows`: whole-utterance identity recognized; at least one half-utterance failed profile identification. Existing report does not preserve half scores, so acoustic cause and appropriate calibration remain unknown. Do not reduce authorization thresholds or claim improved household recognition from this evidence.

Speaker identity1.1.1 adds anonymous aggregate/window scores and margins, specific quality/matching explanations, and a bounded three-attempt failure response. No identity vectors/audio saved; original anchors,0.75 matching threshold,0.12 margin, window veto and command authorization remain unchanged.56 speaker tests pass. This is diagnostic/feedback repair, not completed voice accuracy repair.

Owner approved local cleanup. Old unprotected backups aee76900 (693.67MB) and1f1a5cc3 (692.48MB) deleted with metadata CAS; both jobs verified. Three latest and protected automatic backup preserved. Laborca backup recoverability not inferred from owner statement. Next: backed-up CAS deployment+restart+source/report readback, followed by one household test with per-window scores.


## Owner calibration1.1.2 — source preparation

Owner requested and authorized fixing the voice-only calibration deadlock. Authenticated admin file_write to jarvis_workspace/speaker_identity/calibration-control.json accepts {request_id:32hex,action:start,profile:existing authorized label,issued_at:current epoch}. Requests must be no more than120s old; accepted IDs are consumed durably. Only the configured satellite can supply five clean active-turn embeddings within600s. Three quality/playback failures pause collection. It never assigns identity or issues device tokens, never changes live templates/anchors/thresholds/permissions, and never labels samples as independent genuine/replay-tested evidence. Samples remain owner_supplied_unreviewed in separate bounded tables. Profile deletion also erases its calibration sessions/samples. Runtime report and generated manifest expose counts, scores, expiry and control path without names/embeddings. Publication/deployment evidence follows separately.

## HomePod cold-start45 — source preparation

Owner explicitly requested45% after cold start. HomePod output1.0.2 primes45% once after HA startup through the existing RAOP Audio takeover (ordinary idle Companion volume calls returned unknown). No boot audio is played, uncertain writes are not retried, and the startup hook cannot reset later manual changes. Answer/report snapshots read the RAOP audio interface for the inactive device, retaining real zero/mute and invalid-level rejection. Active output/initialization reports avoid nested takeover. Runtime startup_volume records pending/setting/applied/unconfirmed with readback; application is not claimed from command acceptance. Household audible playback remains a separate test.44 HomePod tests (including serialized startup/answer takeover),68 speaker,49 companion and239 addon tests pass (20 addon skipped).

## Calibration resume1.1.3 — source preparation

Owner reported last phrase fell back to unverified-voice reply. Evidence: four accepted embeddings remain in expired owner session; last STT began08:04:09UTC before deadline08:04:21, but intent matching began08:04:24 after deadline. Do not ask to repeat the first four. Fresh authenticated control action resume now reopens only the latest unfinished session for the same authorized stable voice_id and fixed satellite, preserving samples and deduplication; completed sessions cannot reopen. Each newly accepted sample refreshes600s inactivity deadline; duplicates/rejects do not. With only five accepted samples, automatic extension remains finite. No identity grant, template/threshold/anchor change or promotion.72 speaker tests pass. One cancelled HomePod playback is recorded, but old output report has no cancellation run/reason; exact cause of reported cut word remains unconfirmed and is not claimed fixed by this timeout change.

## Supervised read-only review1.1.4 — source preparation

Collected5 owner training,5 owner validation and5 owner-attested other-speaker comparison embeddings in separate sessions. Existing template rejects all5 new owner holdouts (scores0.6415–0.74), while comparison person scores0.2082–0.2841; scores are cosine similarities, not probabilities. New review.py consumes the private authenticated review-plan.json with three distinct owner-attested completed sessions for the same stable authorized reference and satellite, rejects utterance overlap, and evaluates one predeclared50:50 immutable-anchor/training-centroid candidate against independent holdouts at unchanged0.75 threshold/0.12 margin. It requires5/5 owner accepts, improvement, and0/5 comparison accepts before recommending a separate window test. No model, anchor or permission writes, no automatic promotion, no waveform or vector exposure. Window/replay validation remains unperformed and is not represented as household accuracy.77 speaker tests,44 HomePod,49 companion,239 addon tests pass (20addon skipped). Runtime result must be read before claiming improvement.

## Supervised multi-reference matching1.1.5 — source preparation

Owner authorized completing recognition after fixed blended candidate accepted3/5 positives and0/5 comparison samples. New predeclared score is the mean of the two best numerically distinct reference matches, using immutable anchors plus only owner training samples. Threshold0.75, margin0.12, model and stable identity/permissions unchanged; one close reference is insufficient. Independent owner/comparison sets remain excluded from templates. Legacy profiles use centroid until explicit authenticated activation. MatchingControl accepts fresh120s unique admin activate/rollback requests in jarvis_workspace/speaker_identity/review-control.json with expected evidence/model revision and acknowledgement of the previously owner-accepted replay limitation. Activation requires5/5 positives, strict improvement and0/5 comparison accepts. All file/DB evidence is rechecked under a SQLite write transaction; before-image, policy, template and idempotency receipt commit atomically. Eight private versions retained; profile deletion erases these templates. Centroid-only adaptive promotion/rollback cannot overwrite a multi-reference model. Automatic live learning and replay detection are not claimed. Runtime window checks still require every segment to identify the same profile and are not removed. Actual acoustic household verification follows any qualifying controlled activation; no physical door actions in testing.90speaker44HomePod49companion239addon tests pass20addon skipped. A regression test fails against legacy blending and passes with multi-reference matching.

Review follow-up: all scoring inputs and the activation fingerprint are read within one SQLite read transaction. Concurrent holdout-write regression reproduced mixed-snapshot revision and now preserves the reviewed snapshot; subsequent changed data rejects activation.

## Calibrated recognition1.1.6 — source preparation

Uncalibrated centroid0.75 accepted0/5 owner heldouts, fixed anchor blend3/5, mean-of-two0.75 accepted2/5. All candidates rejected5/5 comparison utterances. Investigation found0.75 was an engineering default, not a calibrated biometric confidence: official sherpa speaker-identification Python example exposes --threshold and defaults0.6 (illustrative, not authentication guidance). New explicit top_two_mean_calibrated_v1 policy uses0.65 for conversation/lights, requires second distinct reference support>=0.6, unchanged0.12 inter-profile margin,5/5 supervised positives,0/5 comparison accepts andpositive-negative score gap>=0.2 before controlled activation. Report labels household threshold calibration and leaves household_accuracy_verified=false; these five tests are not an unbiased general false-acceptance estimate. Locks and voice-profile deletion retain>=0.75 on whole and every window. Lock check happens after command confirmation and pronunciation alias resolution; unrelated LLM service paths still cannot bind a token. No physical lock actions during tests. Pending short-command challenge now lasts60s to include spoken instructions+capture+inference; one-use executed grants remain15s and target/text/device-bound. Native recognition still needs long enough speech; wake models/full duplex are separate.


## Voice diagnostic retention1.1.7

Live owner identity question at10:26UTC was correctly transcribed but rejected. A subsequent0.2s follow-up replaced last_turn before60s report refresh, destroying numeric evidence; exact match failure remains unknown. Coordinator now retains the last16 completed decisions with numeric match/window scores, capture sequence, UTC timestamp and authorization result, without transcript, vector, voice_id or token. Regression reproduces original loss and tests follow-up isolation/bounded privacy. Recognition policy and thresholds unchanged. New live utterance required after deployment; do not claim acoustic recognition fixed from recorded holdouts.


## Native abort callback1.0.3 and live recognition failure

Owner physical identity utterance11:18UTC was fully transcribed;6.31s audio/5.47s voiced, whole match0.628<0.65 rejected. No threshold or profile change. HomePod started1/completed0/cancelled1; original cancellation source was not recorded, so do not claim cause of cut word proven. Found independent real setup-order bug: esphome subscribes a bound handle_pipeline_stop before late companion hook installation; replacing class method misses that saved callback. Regression reproduces absent resume with prebound callback. Hook now targets synchronous dynamic _abort_pipeline, still target-scoped, stopping before single same-conversation continuation with fresh session checks. Adds native abort count, last playback outcome/elapsed/task cancel count and known native-abort/new-run attribution; no media URL/token/audio. Other cancellations still never restart microphone. Physical post-deploy check required.


## Scoped cancellation cleanup1.0.4

User confirmed silence/no button at native abort. Cause inside firmware remains unproven; wake sensitivity already lowest, no silent weakening of voice policy or mic muting. Independent review found resume incorrectly required exact native/output task equality, and cancellation left native satellite RESPONDING because held TTS-end was never sent. Bind run by bound native event receiver, capture both task layers, await their completion and confirmed HomePod stop, then require same latest run/native task/conversation, no announcement and allowed live target. Call native tts_response_finished and same-run TV cleanup even without eligible continuation; only same-session captured continuation can resume. Tests reproduce distinct task layers, no-continuation cleanup and foreign callback isolation.48 HomePod tests pass. This repairs lifecycle recovery; it is not proof the original acoustic false stop or voice rejection is fixed. Last owner score0.6304<0.65; original model remains unchanged.


## Duration-aware supervised repair1.1.8

Repeated real owner turns score0.50–0.63 while old long heldouts5/5 pass. This disproves claims of operational recognition; duration/channel mismatch is a hypothesis, not proven. Add fresh owner-started repair action:2clean6s+ utterances with two consistent model windows, private SQLite storage/mode migration and bounded retention/deletion. Schema2 review trains only first new utterance+its windows and validates second whole+every window alongside original5owner holdouts and5comparison samples. Require6/6 owners, every repair holdout window,strict improvement,0/5comparison andgap0.2. Recognition0.65/secondref0.6/margin0.12 andlocks/delete0.75 unchanged. Read transaction/evidence CAS bind every mode/window; original anchors, stable identity and permissions unchanged. No automatic activation, no raw audio, no global accuracy/replay claims. Pending owner two actual utterances and truthful attestation before candidate review/activation. HomePod1.0.4 reports2cancel cleanups/1resume, but native false abort persists; firmware trigger unproven and is not fixed by recognition change. VoicePE has2mics/XU316; current mono pipeline provides no DoA measurement.

## Cohort recognition1.2.0, family guide and HomePod1.1.0

Owner requested replacement after another failed real test and no more calibration recordings. Critical operational failure acknowledged: repair collection expired10min before user's two utterances, so zero repair samples were stored; late utterances only numeric evidence remain. Do not ask them to repeat these samples. New cohort_margin_v1 uses existing positive anchors/training and owner-attested other-speaker exclusion references. Whole0.55/window0.50, two distinct positives with second>=0.50, exclusion gap>=0.20 and inter-profile margin0.12; raw whole/every window lock/delete0.75 retained. Schema3 independent owner5holdouts and negative5leave-one-utterance-out folds, no regression and raw separation>=0.2, explicitly owner-authorized policy migration. Manual activation only, complete structured bank CAS/rollback; no new audio or blanket authentication claim. Physical recognition still unproven until ordinary use.

Guided family workflow trigger “Nauč se nového člena rodiny”: recognized full-scope owner, name+consent,5training answers,3independent controls+windows; percent is completion, not identity probability. Persistent private state across restart, safe pause/cancel, bounded attempts, no training actuation, new profile unprivileged. Fresh operator family-control.json authorizes/revokes lights only using validation proof and ide…3215 tokens truncated…dence/2026-11-03-room134-actual-measurement.json.


## One actual room test completed; runtime1.3.5 recovered —3Nov2026

This supersedes pending/error snapshots, not the recorded failed jobs. The SINGLE consented remote test ran once under1.3.4:2945frames/29.4037s native window/30.0007s request watchdog;27.44s paired audio retained only in RAM/peak2239128B. Fixed HomePod text15.09875s completed/no stop/error, current45% preserved, sender firstaudioestimate2350.3ms. No STT/identity/agent/household commands or cloud microphone. Scalar analysis exhausted30.636s budget after22windows and wiped allPCM/retained0; do not widen budgets or re-run capture to obtain a green result. Physical receiver state after test satelliteidle/HomePodoff/TVidle. Actualevidence docs/evidence/2026-11-03-room134-actual-measurement.json.

The135 runtime fix is PUBLIC a57f2619dceb06ad9a4fac3d692e8dc4c0e35081/tree4e2e56a01c73d24015e15e034ae1023f00755012, local9b29e6c exact.265duplex/manifest/diff andCIpush41632182532/PR41632191855 success, lab125904925722 immutablepublishsuccess. Root fixed its own nonexistent APIClient.is_connected assumption using pinned45.3.1 PUBLIC connected_address/api_version (unknown failsclosed); actualshape RED1failure+1AttributeError thenGREEN. Source d98c0d748d5d5ed5c3414889f54c805594a20a57d90ddba7c98502f7ca286f7f.

room135-apply-20261103 was submitted ONCE12:03:11UTC, automatic check FAILED runtime_check_failed12:07:27/backupb77ec1cd/planactivation_failed. Do NOT reapply to repair bookkeeping. Independent fresh exact3files + report afterstartup12:07:57/12:09:12/12:11:03 show1.3.5/configured/adapteractive/source d98/caliboffPCM0/isolationfalse/sessions0; fresh135nonce native77frameVAD/Marin2.8316875s nonsilent/generatedwaveform19.965ms/NumPy760.06ms/corr.999078/constructed1250ms passed. This independently verifies actual activation without renaming failedjob or inventing phase active_verified. Sensorconfigured, satelliteidle/TVidle/HomePodoff/TVintegrationloaded. Fullnativeproof docs/evidence/2026-11-03-room135-native-recovery.json.

Persistedisolationfalse/fresh_native_connection exactrevision4b50e116b314601a7982a9ddab704a7b13b20251226f4f0a7444a22205203bdb. Durable one-shotSTILL consumed same nonce/revision92ec14400d32af3e95cb3ed3df3a3e9f002f880c559d8e74239fd7942acae840; no further remote microphone start authorized. Private combined receipt exactrevisiond1be6ec59a6c96e9491991645b1187e20795d84d1b56828f780a6b47aad9391d (snapshot beforelease release). room134-release verified12:00:26UTC then135acquire12:01UTC; room135-release verified12:19:08UTC/freshlockedfalse/private expiredmeasurement control andtokensremoved. Oldunprotectedcf7385ba and42b6d49d namedCASdeleteverified/newest3+protectedkept, backupready space restored. No repeatedapply, no newmic or firmware/Core/provider/profile changes.

Original acoustic/immediatehumanbarge/1s goal remains OPEN. Actualpartialrawcorrelation0–.496/bandscore.724–.938/coherence.451–.923; band lag380.44–386.13ms is additional to sender estimate, not receiver/physical propagation proof. VAD>=.5 in1399/2744 retainedframes; no measured realASR failures in this diagnostic. Do not claim self-interruption fixed from one fixed playback test.

Read-only hardware-reference feasibility found a digital preDAC/preAMP VoicePE→XMOS reference path, DAC mute preserving reference, GPIO47 separate amp and channel1 AEC-stage capability. Installed firmware stage/version notverified. Stock40ms micdelay/main150ms/shadow75ms filter cannot cover unaligned~380ms offset. No synchronized externalHomePod referencefeeder exists; ordinary two play_media calls are insufficient. Save exact primarysources and boundary in docs/superpowers/specs/2026-11-03-homepod-hardware-reference-feasibility.md. No hardware change or newMic. Numerical helper is separately checking a causal past-trained/frozen FIR subtractor (not the rejected per-window fitted classifier); no productionintegration/eligibility assumed.


## Additional causal subtractor also rejected —3Nov2026

Independent read-only numerical helper tested a genuinely past-trained/frozen future-waveform predictor, not the earlier per-current-window fitted classifier.96fits/2693scalarcases: stable linear future echo attenuation1.34–26.34dB and frozen current-human component preserved; all contaminated/AGC bootstrap cases failopen, so zero echo removal there. Futuregain÷4 and nonlinear gating still amplify error to-5.54/-7.52dB despite energy guard; changed guard decisions add up to17.7× humanenergy artifacts. NO-GO, no productionintegration/livechanges. Fullowned authored-fixture scripts and compressed scalar case results under experiments/rejected-causal-aec-20261103, REPORT/summary/provenance preserve every limit. No actualroomPCM retained or replayed; room nonlinearDSP remainsunknown. Current1.3.5/d98 remains unchanged/lease released.


## Synchronized reference candidate —3Nov2026, not deployed

Native1.3.6/addon3.12.3 candidates add exact owned RAOP sample timing, paired
Sendspin PCM, a silent Voice PE I2S gate and a fixed generated-only native probe.
The probe never opens a microphone or HomePod. Production dialogue is not yet
attached to this reference. Full implementation/limits: docs/superpowers/plans/2026-11-03-reference-bridge.md and experiments/reference-bridge-20261103/README.md.
Both exact ESPHome2026.10.1 minimal fixtures compile; real overlays pass codegen;
UBSAN lease checks pass.312duplex tests and246addon tests(20optional skips) pass.
A single real encrypted240s transport experiment has a preserved FALSE verdict
(clear+end coalescing criterion); separate clear-only test passes. A7.571352s
actual-module SDK integration passes with simulated native counters/ACK only.
Neither experiment proves physical DMA, HomePod alignment, AEC or conversation.

Live baseline remains native1.3.5/d98 andaddon3.12.2, Core2026.6.4 unchanged.
Deployment preflight:1.6GiB free, mandatorybackup threshold2GiB; no newbackup,
firmware change, deployment or microphone use. Retention preview identifies
old unprotected ba75b0ef708.05MB and9edc3711710.38MB; explicit deletion approval
is still missing. Preserve latest3(b77ec1cd/d9346e31/4fb5ba7f) andprotected27122c9a.
Continue from concrete reviewed publication and CI, then approved cleanup,
addon update/safe installed-package metadata, exact target compile and backed-up
CAS activation. Existing consumed room latch remains immutable.
Original stutter/self-answer/barge-in/1s goal remains OPEN.

Review correction: stock_sendspin staging is now explicitly rejected before any
write because its experimental listener replacement silences normal Sendspin
media. Its YAML/fixture remains a build-only experiment, not a deployable profile.
Only legacy staging is allowed, and exact installed-package compatibility remains
a required compile gate. Review also found and corrected zero-progress callback
busy-loop and HA initialization/probe ownership race. Full review/rulings are in
docs/evidence/2026-11-03-reference-bridge-review.json.

Final host checks after the review fixes:314duplex tests10.259s PASS;247addon tests7.562s PASS(20optional skips); manifest and diff checks PASS. No live activation.


## Reference candidate published; physical activation blocked —3Nov2026

Supersedes the publication-pending notes above. Public source
54e9bce5d634e34197528ec565d1ed10b98dd01a/tree746ed1ff5d27a67f0f9dd1547842ef33287c5e06
exactly matches local322a390072d8708f17aa81d3ba1d71071849733f. Push CI41646159996
completed13:43:08UTC; all8jobs passed including both firmware fixtures, both
containers and publish-laboratory125954034069 (immutable package/catalog steps
not skipped). No live update, firmware install or microphone test was performed.

Fresh live report13:39:16UTC: native1.3.5/d98/configured/adapteractive/Core2026.6.4,
no active dialogue and room isolation false. Storage still1.6GiB versus2GiB
mandatory backup minimum. Source/proof and exact proposed two cleanup candidates
are in docs/evidence/2026-11-03-reference-bridge-proof.json. Cleanup authorization
remains missing for ba75b0ef and9edc3711; none deleted. Preserve newest3 and
protected27122c9a. Ask only this concrete destructive scope; existing Git/update
consent persists. After approval recheck retention/CAS/space, delete only named
backups, then update addon3.12.3 to read safe installed-package metadata.
Stock_sendspin is explicitly NOT supported for staging; legacy needs exact
private-target compile before install. Native1.3.6 and silent device probe still
not activated; timed physical alignment and acoustic acceptance remain open.
Do not repeat old room134 consent, old135 apply, or the frozen240s experiment.


Stock compatibility continuation: owner says backups deleted/freehands; fresh6.7GiB/unlocked, no assistantdeletion. Jarvis3.12.3 updatef1471f98971d4b7eb4636dba7065e58a submittedonce andverified, backup0996fed9, freshversion3.12.3connected/storage6.6. Native1.3.5/d98 untouched; nofirmwarewrite/leaseyet.
Actualuploadeddeviceconfig hasofficialURLwithout@ref; optionalrefparser bugfixedRED→GREEN for3.12.4candidate. Officialdefaultdev d4e6fa43 inheritsstock; legacyduplicateplayer reproduced, so do notstagelegacy. Newfirmwarestockrouting fixedpublicreference_server_id atboot, preservesnormalstockcallbacks/codecs/delay/unpairedpolicy/32bitnormalmixer; staticidentity avoidsunarmedreferencebecomingaudible.
Roothostcandidate1.3.6 addsreference_identity control120s (noendpoint/network/mic) tocreate/loadprivatekeyonGreen andreturnpublicid; stage3.12.4 requiresreference_server_id43base64url andsupportsstock. Root317duplex/249addon20skip GREEN; stage7testsGREEN; updatedCIrunsstock_adapter_test.py/hub_config_test.py. Newcriticalgoalproofstillnotperformed.
Agentreference_stock_coexistence ownsfirmwareonly; bothminimalbuildsPASS, fullimmutableofficialpackagebuildrunning; sourcecounterfixafterself-review pendingtoavoidmetadata-callback teardownwaitonownstack (endmustwaitPCM-only; allcallbacksblockarm). Agentreference_stock_review found0Critical/Important ininitialfrozendelta andwillcheckonlynewcounterfix; report .superpowers/sdd/2026-11-03-reference-bridge/stock-integrated-review.md. Fullbuild+finalbuild-proof.json mustcompletebeforepublish.
PublicHEADstill54e9bce (all8CI41646159996passed,labpublished); localHEAD2e7041d containsUNPUBLISHEDdocumentationcheckpoint. Current3.12.4+stock+nativeidentity changesuncommitted. NoextraapprovalneededforGit/update/deploy. Nativepayload /tmp/reference-native-deployment/prepare-call.json fromhelperisSTALE after3hostsourcechanges; preserveitsfreshCASbeforeimages, regeneratefromfinalpublishedsourcebeforeapply. Agentreference_deploy_preflight canrebuildit; nolease acquired. Expectedold8filelist __init__,control,manifest,5reference*.py; oldpostfingerprintdbbe575...NOT currentnewcandidate.
Next: finishcounterfix/fullbuild/targetedreview, finaladdonchecks/manifest/diff, commitallownedchangespluspublicproof, GitCASpublish against54e9bce (exacttree), waitCI; updateaddon3.12.4once/newrequestid andverify. Thennative1.3.6 viaexistinglease/bundle/core_restart andfreshfile/hash/runtime/nativeproof; runreference_identity(nohardware) toobtainPUBLICserverid; freshmetadata/sourceCASstageSTOCKoverlaywithexactpublishedSHA+publicid; compileprivateGreentarget, onlythenbackedupinstall/hashreadback; silentreference_probeonfreshnonce. No oldroommicrophone grant replay/clearing. Acousticmeasurement/fastbarge and1sgoal remainunproved.

Stock compatibility candidate complete for publication:317duplex and249addon(20optional skips) testsPASS. Bothminimalfixtures andFULLimmutableofficialVoicePEpackage compile PASS onfinalsources, includingreentrantcounterfix. All7compiledcomponentfiles byte-match inall3builds. Fullconfig91263d25/RAM149883/flash2847423; finalproofdigestda75271e24914d56a473972dcf245d03bc8bc96f0f6856829d4cf0e01b9833c3. Focusedintegratedreview0Critical/0Important, counterdeltaaccepted; allreviewlimitsretained. New3.12.4/1.3.6 source ready, NOTactiveyet. Nativepublicidentity mustbe preparedbeforestockstage. Existing3123active/0996fed9backup,6.6GiBfree. No furtherdeletionneeded; userfreehandsauthorizationpersists.

## 4 November 2026: owner chooses permanent half duplex

Archive branch archive/homepod-duplex-experiments-20261104 preserves 129149e2.
Native 1.3.7 candidate uses HalfDuplexSession and removes echo observer/classifier
from ordinary dialogue. No firmware changes. Details and failed paths:
docs/experiments/2026-11-04-half-duplex.md. DEPLOYED: half137-apply-20261104 verified/active_verified at 08:15:42 UTC,
backup b74d6651, native 1.3.7. Exact 4 files read back; native probe and16.416s
HomePod output passed, zero stops/errors/cleanup pending. Lease released.
Full proof docs/evidence/2026-11-04-half-duplex.json. CI41797390703 all8jobs
success. Household wake reliability/audibility and provider latency remain
unverified; no remote microphone test performed.

## Spoty preparation — 4 November 2026
Owner approved screen design and TEST OTE pricing, no live operation change.
New preparation view has live house/grid/battery flows and current OTE prices, preserving all previous views. Controls explicitly disabled pending controller implementation; no fake active AI.
Private baseline: jarvis_workspace/spot-baseline-20261104.json (HA-exposed settings only; never publish household settings). Capture verified. Zero export offset confirmed20W. Numeric capacity sensor20kWh differs from owner23.5kWh; do not infer stored kWh without resolving.
OPEN: physical action mapping/tests and rollback, configured export permission/limit, forecast-calibrated plan, interval settlement and week/month totals. Archive status retrying. TEST OTE authorized for simulation; actual contractual price to connect later. Browser QA blocked by missing Chromium download; source tests pass, no claim visual acceptance.


## 80 A charging button live verification — 4 Nov 2026 20:02 Prague
Source79eff534c40d46e661d7b4329e95682fb642bdef deployed via battery80-prepare-20261104 / battery80-apply-20261104. Job verified19:02:36UTC, phase active_verified, runtime sensor idle/version0.3.1; exact3file readbacks match hashes. Backupd6d22db0. Fresh inverter grid charging80 A, maximum charging100 A. Engine requests min(80,inverter max) regardless of previous20/40/80/100 setting, shared80 A report constant. All263local addon tests PASS after installing missing test dependencies;20optional skips. Charging14tests, JS card and day-energy unit tests/manifest checks PASS. GitHub energy-chart job fails at Playwright1.58.2 browser installation on ubuntu26.04 (unsupported runner), before browser tests. No physical test started in this task. Global maximum100→80 action rejected action_not_allowed, remains OPEN; no bypass. Existing10minute/+5SOC/90%/temperature guards retained. Lease release battery80-release-20261104 submitted.


## Voice diagnostics step 1 — 4 November 2026

Owner approved sequential repair plan; this change is diagnostics only. Native1.3.8/diagnostics1.1.3 records bounded actual local conversation timelines (8 runs,48events/run,240chars/transcript) in private0600 report; no raw microphone or response text. Native wake hint is metadata, never acoustic proof. Separate direct-verbs path records16 recent decisions including TV-active refusal and continuation flags. Half-duplex, identity grants, TV policy and command decisions are unchanged. Microphone temporarily muted after owner reported spontaneous TV pauses; preserve mute until controlled household test.

Root of earlier missing logs: native-session wrapper emits only outer start/STT/end; internal TurnBridge and Session were unobserved. Root of short-verb closure remains to verify acoustically: direct verbs are explicitly blocked while TV is active, even when a previous Jarvis activation existed. Local source corroborates this branch; do not call it an accepted household fix.

Independent review found2Important: observer failure can skip cleanup, identity errors misclassified as agent. Reproduced with actual extracted dialogue/bridge, fixed RED→GREEN. Callback and diagnostic snapshots isolated; bridge stage errors carry actual duration/type only; response wrapper tagged response, not agent. Per-turn output startup/TTS facts and separate metadata/cancellation events. No unaddressed critical/important findings. Local330+ and addon263(20optional skips) baseline/verification; final counts in deployment evidence. No real private transcript enters Git. Activation still pending publication and CAS backed-up bundle; no new remote microphone test.


### Diagnostics138 publication blocked by automatic approval
Source commit4e9cb7960a2398a2e4f869c27c4dc98a7cee2937 is LOCAL ONLY.332duplex/33diagnostic/263addon PASS (5/0/20 skips), manifest/diff clean. Auto-review rejected both force-with-lease and normal fast-forward publication as unapproved source disclosure/branch mutation despite verified public repository and matching baseline. No more retry through a connector or alternate route. Exact requested approval: public mlegnavsky/jarvis branch feat/jarvis-addon diagnostic source publication, followed by backed-up CAS activation on existing Green. No lease acquired, no bundle applied, no restart, native stays1.3.7 and diagnostic1.1.2; microphone remains muted. Prepared evidence docs/evidence/2026-11-04-voice-diagnostics-prepared.json. All live baseline revisions and candidate bundle were prepared in the active task; refresh revisions and status before eventual apply.


## Diagnostics step1 activated — 4 November 2026 22:49 Prague

Owner explicitly approved public repository destination and backed-up activation. Source ab32375aed41caecb77f4cdd24b38a2ac11b2bac/tree f06b7749a3a2db2710eab6af01015893c773e190 is published on feat/jarvis-addon (same content as local190699e). voice138-apply-20261104 finished verified/active_verified, backup8f98d4a5. Exact8file readbacks match candidate. Native1.3.8/adapteractive/configured/source56cb4885872ed27d13f7643b144ab8ba8ff6de31db617e1e34cf7a6af844055d and diagnostics1.1.3/directwake7/monitoring observed after restart. Fresh native generated-only readiness probe passed77VADframes/2.8316875s TTSreference, no microphone or audible playback. Lease released verified. Microphone muteon/satelliteidle preserved.

332duplex(5skip),33diagnostic,263addon(20skip) checks PASS. CI bothpush/PR tests, containers, firmwarefixtures andbackupDAV PASS. Energy-chart browser dependency installation fails because Playwright1.58.2 does not support ubuntu26.04; labpublication skipped. No claim allCIgreen or labpublished. This unrelated runner issue is unchanged. Evidence docs/evidence/2026-11-04-voice-diagnostics-active.json. No actual household transcript captured yet; step1 instrumentation deployed, physical acceptance still needs user test. Step2 TV false-trigger handling, normal-paced verbs, followup, audibleHomePod, interruption and latency remain OPEN. Do not unmute until controlled test or step2 mitigation. Do not repeat apply/restart/probe or old room134 capture.


## Wake calibration installed — 5 November 2026
Owner approved additional older unprotected backup cleanup: 71b44763,44658f15,d6d22db0 deleted with CAS/verified jobs; newest and all protected preserved. Free space1.8→4.0GiB. Main Jarvis false wake reproduced in private diagnostics after secondary wake disabled; early TV pause precedes empty STT, no accepted command. Threshold0.8→0.9 using unchanged model; standard UI sensitivity does not control custom model. Compile passed; backed-up install wake90-install-20261105 verified05:13:51UTC, backup6d032ebf, upload57a9aac0955a exit0, device online/hash e4bd82b9 matches expected. Lease released verified. PrimaryJarvis/secondarydisabled/muteon/satelliteidle confirmed. Firmware active, acoustic acceptance OPEN. Keep microphone muted until controlled TV and short-command test; do not repeat install or claim false wakes fixed. Evidence docs/evidence/2026-11-05-wake-threshold.md.


## Charging button 100 A — 5 November 2026
Owner explicitly requested raising current and then changing the button. Grid setting100 A accepted before deployment. Source67f214047774f1243d9759867befa19bdde4cb9a native0.3.2 changes only shared test current80→100 and version; existing temperature/SOC/600s/no-export/recovery guards preserved. charge100-apply-20261105 verified active_verified05:34:29UTC/backup ee41e116, runtime idle0.3.2. Fresh exact3file readbacks and grid100/max100 confirmed05:34:56UTC. No physical100 A test started. Charging14/JS/manifest/diff PASS. Local263test suite has1SDK import error and20skips; remote CI41974263983 tests job and containers/firmware/backup-DAV PASS; energy-chart fails Chromium installation before browser checks. Earlier UI sign/color changes remain local and excluded from this deployment. Full receipt docs/evidence/2026-11-05-charging-button-100a.json.


## Owner-authorized 150 A and narrow permission change — 5 November 2026
Owner explicitly requested fixing permissions from here. Supported self addon_options CAS added ONLY number.inverter_battery_max_charging_current; existing entities retained/services unchanged, job charge150-grant-specific-20261105 verified/hot activation/backup4458baa6. No credential or connection option change. Max and grid settings150 A accepted. Native0.3.3 source4e02af8f972aa1f60dd2ad74888b449108bffda5 requests min(150,inverter max), guard/restoration unchanged. charge150-apply-20261105 verified active_verified06:05:58UTC/backupaf6196a4; fresh3file exact readback, runtimeidle0.3.3 and both150 A settings verified06:06UTC. No physical150 A test initiated. Charging14/JS/manifest/diff pass; local263tests one existing SDK import error20skips; CI41977640690 tests job passes, energy-chart browser installation fails. Proof docs/evidence/2026-11-05-charging-button-150a.json. This supersedes previous100 A setting and missing permission statements.


## Owner-selected charge/discharge 175 A — 5 November 2026
Owner requests175 A for both directions. Existing authority to manage relevant inverter permissions used for supported self addon_options: ONLY number.inverter_battery_max_discharging_current added; no removals/services/credentials changed, verified charge175-grant-discharge-20261105/backupc86411d8. Maxcharge, gridcharge and maxdischarge175 A accepted and independently confirmed after restart06:25UTC. Native0.3.4 source1d37fb166eaf920f7a69a06cb44fa31c1778b07c requests min(175,inverter max), existing guards/timeouts/recovery preserved. charge175-apply-20261105 verified active_verified06:24:56UTC/backup301b8bf3, exact3file readbacks/runtimeidle. No physical175 A test started. Charging14/JS/manifest/diff pass; local263tests existingSDKimport error20skips; CI41979616549 tests job passed, unrelatedenergy-chart browser installation failed. Proof docs/evidence/2026-11-05-charging-discharging-175a.json. Supersedes150/100settings, no automatic trading enabled.

## Energy sales current checkpoint — 5 November15:44local
Read docs/evidence/2026-11-05-pv-sales-commissioning.md and fresh native runtime.
0.4.5/finance/archive1.2.2 active verified; live daily cash and historical backfill
work. 0.4.6 native battery timing commissioning source is published and backed-up
activation is pending (sales-native-window-apply-20261105); do not repeat unknown.
PV500W export/stop physically passed, but later low-sun PV automatic triggered
battery_discharge protection. Production battery_verified=false. Native0Wbias
not confirmed (raw104 still20). Forecast-calibrated battery scheduling remains
OPEN. No full-automation completion claim. Repository-pinned isolated test runtime
plus realPHP:346tests passed, no skips; current native readback/stop/source evidence
required before further activation or any success claim.

## Energy live16:26local — ACTIVE NATIVE TEST, no restart
0.4.7 activeverified15:24:15UTC/backupe0debf77/sourcee4c482b; owner-native-lv-window-
commission-20261105 accepted. NativeWindow1793892335790385341 armed16:30–16:35local,
cap500W/current20A/floor95. Await physical start, native boundary and cleanup.
AutomaticOFF, productionbatteryfalse. Read current sales-runtime.json before any
mutation. No passed test exists yet. Jarvis3.12.5 bootstrap verified, count1000
proved old administration cap; newcap10000/history preserved, writes restored.
Clock sync actualdelta-2.35s; temporaryrulesremoved/original3automationsrestored.
Reusablemobileverification/Stop generator implemented; privateUIalreadywritten.
351localtestsPASSwithpinneddeps+realPHP. Source and evidence remain separate from
physical acceptance. Forecast calibration/house-budget adapter and battery
recurrence protection still OPEN; do not report full automation complete.

## Energy16:50local — first native test failed, safe restoration complete
First nativeWindow1793892335790385341 did not export. Radio/Modbus timeout during
window; all beforeimages/current175A restored at16:35:34local, noactive transaction.
0.4.8second commissioning variant prepared: SolarSellON ONLYwithin native5min
window, ALLsixSOCfloors95untilcleanup, fixed500W/current20A, no productionunlock.
Clock proof requires observed export in last15s before end; never/long-agoexport
cannotpass. Mobile independentstatus timer prevents frozenstoppingdisplay.
Originalstopreason/context retained. Read current runtime before any restart.

## Energy checkpoint 2026-11-05 17:09 Europe/Prague
0.4.8 activeverified; native500W/5min/SOC95 SolarSellON trial1793894870144619394
armed17:10–17:15, not yet measured. Do NOT restart while native transaction active.
0.4.9 source fixes reviewed post-audit normal-sale race and purchase rawcounter
fallback;361tests passed. Must deploy before next ordinaryPV start. Finance card
partial-known label alreadylive. Full production still blocked by native expiry/
recurrence, PV battery-assist and calibrated forecast/house budget. ZeroWtarget
unconfirmed(native20). Verify all restoration with delayed fresh native snapshot;
prior immediate ACK did not persist for slot2SOC/current (corrected+confirmed17:06).

## 17:19local — second native trial failed export, Selling First source prepared
NativeWindow1793894870144619394 ended17:15:40local with deadline/stop_verifiedTRUE,
observedFALSE/native_expiryFALSE/productionFALSE. At17:12:30 independent FC03
confirmed142=2,143=500,145=1,146=255, slots1710/1715, allsixSOC95,173=32.
Across the actual window PV0, grid remainedsmallimport, battery served house;
SolarSellON+ZeroCT does not establish battery sale on this installation. Do not
repeat unsupportedZeroCT variants or weaken health/SOC checks.
Exact manufacturer SM2 manual section5.7 documents SellingFirst+TOU for battery
export, not Sell32 overridingZeroCT:
https://www.deyeinverter.com/deyeinverter/2024/08/13/instructions_sun-3-12k-sg05lp3-eu-sm2_240813_en.pdf

Source0.5.0 adds only a bounded SellingFirst commissioning alternative:500W/5min,
SOC95inside/SOC100outside,20AorlowerBMS, no gridchargeflags, MODE0 onlyafter
actualwindowstartandfresh post-audit checks. Native expiry requires recent actual
export, stoppedgrid AND stoppedbattery discharge<=100W, hardwareclockafterend,
mode0/EN0/nextSOC100 before any HAstopwrite. Protective stopattemptsMODE2first,
thenCAP0/EN0/allflagsindependently. Read-onlyreview's two findings reproducedRED
and fixed;69targeted testsPASS. ProductionalwaysFALSE.
SOC100outside blocks ordinary house battery use; during an HAoutage house falls
back to grid and PVexport maycontinue; dailyrecurrence still unresolved. This is
a diagnostic commissioning alternative, not acceptance of fullautomatic behavior.
Idle nativeprogramnowrefreshes60s to detect settings that didnotpersist after
immediateACK. UI includes explicit Czech gridfallback notice for this variant.

Final pilot hardening: MODE2 is first protective command. Native expiry also
requires battery discharge<=100W, preventing high house demand from masking
continued battery discharge. After restoration, a fresh complete native snapshot
must match every before-image setting (safeCAP9300/MODE2/EN0); otherwise the
transaction remains active for cleanup retry and cannot emit verifiedstop.
Configuration writes settle1s before independentFC03; futurewindow preparation
buffer is3minutes. Additional restoration regression observedRED→GREEN;70targeted
testsPASS. DelayedHAstates showed mixed95/30/current20 after priorcleanup; this
is an observed mismatch, not proof of its cause. Newbootnative snapshot will
separate staleHAstates from persistenthardwareparameters before nextpilot.

## 17:46local — version0.5.1 verified, bounded pilot adapts to currentSOC96
0.5.1activatedverified17:42:18local,backup7674d66f. ExactthreefileSHAreadbacks
matchsourceb4f7263669b5aad74d2cfe2a9b57aed035150059. ClockLASTsnapshot
17:41:56.915 shows17:41:55 (−1.915s), all6SOC30/ordinarytimes/flags0;
healthy/readyTRUE. The originalclockorderingdefect is corrected without
weakening5stolerance. No ExportFirstphysicalpilot has startedyet.
Batteryhasnaturallyfallen96whilepoweringhouse. OwnerapprovedsaleSOCfloor60;
previous95commissioningfloorwasourinternalconservativebound. Source0.5.2
changesONLYSellingFirstpilot tofixed90floor/preflight93, outside100, still
500WGRIDcap/5min/currentmin20A/prior/BMS. ZeroCTvariantskeep95/97. NativeTOU
powerlimitsBATTERYincludinghouse, so SellingFirstactiveTOUpowerismin1000W/
priorhousepowerwhileglobalgridMaxSellstays500W; no increaseofgridexportcap.
UIandruntime showactualminimumSOC. Explicitlyexplainedownerbeforeimplementation.
ObservedRED96start/floor90/battery1000tests→GREEN48targetedtests.
ProductionbatteryverificationstaysFALSEandfullautomationOFF. Nativeclock/
health/price/freshness/expiry/fullrestorationguardsunchanged.

## 18:19local — actual battery export proven; native ramp observation pending
0.5.2source59a846e6b3182a03c6b06aeaa8ec59c6de26ab97/local5497755 activated
17:53:49local,backupca20ba2c. Allnativeguardspreflightpassed; actualwindow
1793897760591554771armed18:00–18:05 with500Wgridcap,1000WbatteryTOUpower
includinghouse,current20A,minSOC90/otherSOC100. Sustainedactualgrid~−501to
−511W withPV0andbattery~613–627W,SOC96. Batteryexportisproven. NativeendNOT
yetproven:18:05:09grid−510/battery627,18:05:15−285/446,18:05:20−120/246;
connectedstopbegan18:05:25beforecompletionwasobserved. ProofobservedTRUE,
native_expiryFALSE,stopverifiedTRUEat18:06:13. Delayednativewholeprogram
18:07all6SOC30/originaltimes/flags0; actualgrid10W/battery264Whouseconfirmed.
No fullproductionclaim. Source0.5.3 allows60s observationafterSellingFirst
boundaryatunchanged500W/SOC90/current20/health/positivepriceguards; other
variantskeep20s. UIexplicitlystates5minslotplusup-to60sdecayobservation.

Addedpureplanning.py/modelv2 withprior-issuedempiricalGHIcalibration,25%house
profilemargin,efficiencies sqrt(.90),unknownchargecap0(noPVstoragecredit),
strictcompletehourlyhistory; counter-onlyfallbackusesconservativerolling24h
envelopeincludingpossibleendsinsidegaps,quantizationandedgeuncertainty.
No fakehourlyloadorPVcreditfromcounter-onlydata. Dailymaximumcacheisrejected.
29plannerregressiontestsPASS. planning_setup.pyreadslastfourcompletearchive
daysandusespreviousdayweatherpublicationfornextdaycalibration; fouradapter
testsPASS. ItsfailureorStore/snapshotfailureisisolatedfromcontrol/reportand
fallsbackrequiredSOC100. ReserveisfedtopolicyandshowninmobileUI.
408fulltestsPASS plusfinal29plannerregressionscheckedseparately; no claimof
liveplannerresultsbeforeactivation/backfill. Nominalcapacity23.5kWhisexplicit
policybasis,notmeasuredSOH. ProductionbatteryverificationstillFALSE; native
productionactuator/outagepolicyandPV-onlybatteryassiststillpending.0Wtarget
remainsunconfirmednative20. No new liveexportstartedwhileworksourcechanges.


## Appliance reading and mobile chart — 5 November 2026
Owner clarified that zero applies only to deliberate grid import, never appliance consumption. Native Deye Load becomes0 in ExportFirst, including the vendor app. Added separate canonical template sensor sensor.jarvis_spotreba_domu with AC-output+external-grid balance in ExportFirst and native Load otherwise; source health/coherence/negative checks and5s heartbeat. Live configuration validated; template reload and canonical nonzero state confirmed without Core restart or inverter writes. Main/Spoty/device views now use canonical sensor. Normal-grid0 policy is unchanged and separate.

Published source and exact liveJS readback: mobile full-width chart, pinch time zoom/pan, reset,+/−, persistent window, canonical history cutover gaps. Source unit and synthetic gesture checks pass; pinned Python suite577testsPASS. Actual iPhone/browser acceptance remains unverified (Chromium launch sandbox and CUA local-file policy blocked preview). A client reload may be needed for the updated static asset. HARecorder and long-term statistics include the new house entity; adding it to the private10s archive IDS remains a separate activation task. Do not fabricate old house readings or claim native vendor-app0 fixed. Batteryautomatic export stayed active/healthy throughout; no Core/OS upgrade or restart.


## 6 November 2026 — sales0.6.5 active, automatic enabled

See docs/evidence/2026-11-06-automatic-sales-enabled.md. Stop/enable race reproduced and fixed without weakening protections;580 tests pass,20skipped. Deployment auto065-apply-20261106 verified active_verified, backup63defc01, Core2026.6.4 unchanged. Runtime automatic=true/inhibited=false/healthy=true/error empty confirmed twice at00:13local. Selected block6November15:45–17:45Europe/Prague, reserve60%. It is waiting, not currently exporting. Future whole-cycle acceptance remains unobserved. Native20W import target remains a separate unresolved issue. Do not rerun an enable or commissioning command unnecessarily; preserve current owner setting and guards.


## 6 November2026 — owner5W experiment deployed, native persistence failed

See docs/evidence/2026-11-06-grid-target-5w.md. Source27f4256, runtime0.6.6, combined deploymentgrid5066-apply-20261106 active_verified, backup263a3f4e. Normal target/restoration/status all5W, ordinary automation on, automatic sales still on. Requested5 was briefly read four times, then native single/bulk/single all returned20; independent delayed snapshot also20. Do not claim5W persists or overwrite it with0. Future investigation must identify the actual reversion mechanism. Full suite580tests passes,20skipped; reserve/physical guards preserved.


## 6 November 2026 — 1W experiment, persistence failed before sale

Owner requested1W target and confirmation across sale/return. Source b1db6c052d9ebb848577faab6e4e5871904d25f1, runtime0.6.7, deployment grid1-apply-20261106 active_verified00:10:18UTC, backup5a64fb3e; seven files exact readback. All shared targets/button/restoration1W; no guard/price/SOC/cap changes. Full580 tests pass20skipped. Guarded probe owner-grid1-native-20261106 at00:10:38UTC returned seven1W reads and immediate verified proof, but independent native snapshot00:11:15UTC returned20 and HA telemetry00:11:25UTC20. grid_target_confirmed correctly becamefalse. Reversion occurred in idle without any sale or mode transition; no export test was started after initial persistence failed. Automatic sales remains enabled/healthy, no active transaction/controller error. Leave owner1W config, do not claim persistence or confirmed sale-cycle. Actual writer/firmware mechanism remains OPEN. Evidence docs/evidence/2026-11-06-grid-target-1w.md.


## 6 November2026 06:28local — wire debug capture completed, source unresolved

Existing Solarman device/services/pysolarman DEBUG enabled in two bounded120s windows through reload-only one-shot automation, sources34978ff/d88bc3f See docs/evidence/2026-11-06-grid104-wire-trace.md for exact commits. Positive control captured real SENT/RECV and FC16 register104=1. First guarded probe timed out before establishing before-image; later normal1W automation independently attempted writes during communication recovery, so do not claim the whole window had no device write. Recovered guarded probe confirmed1W seven times; delayed independent native snapshot05:28:39UTC104=20. No captured20W write identified. Frequent timeouts and connector log omissions prevent complete absence proof. Detailed returned chunks/proofs persisted privately jarvis_workspace/grid104-wire-evidence-20261106.json with exact readback. Timer resets DEBUG towarning; original automations restored via CAS/reload verified; no Core restart. Final idle/healthy/automatictrue. Next: complete filtered transport observer or independent HA-isolated test; no attribution to cloud/firmware/HA yet.


##6 November2026 — solar0.7.0 active; automatic deliberately paused

See docs/evidence/2026-11-06-solar-completion-070.md.15 deployment files exactly read back; independent verification plan finishsolar-v2-runtime-verify-apply-20261106 active_verified (sales0.7.0, finance1.1.0, supervision1.0.0, archive1.2.3). Original restart job timed out upstream while starting; reconciled without replay or second restart. Backup fcb10fc6. Cash/energy cards and fault notifications active; nominal basis23.552kWh from460Ah, not physical47kWh proof. Real500W sale exported, but native deadline FAILED; HA stopped and restored originals. automatic=false/inhibited=true/battery_verified=false; keep paused pending successful native proof. Requested1W still native20W; cause unresolved. Physical near-full PV acceptance not observed.603 tests pass20skip plus archive8. No backup deletion by this work; owner cleaned independently.


## 6 November2026 — HA autonomous solar0.8.0 ACTIVE

Source44370be7904b6a31647bb6258ac20a954e56d58c; solar080-apply-20261106 active_verified08:55:05UTC, backup70dcbfb2, alltenhashesmatched, sales0.8.0/heating1.2.1/Core2026.6.4. See docs/evidence/2026-11-06-ha-autonomous-080.md.638testsPASS20skip +28heatingPASS; independentreviewnoblockers. Existingheatingvalues21/22survivedrestart; sharedchildsensor/bothheaters strictbelow21/above22, existingguardsunchanged.

OneownerON solar080-enable-owner-request-20261106 consumedconfirmed; HA itself startedbiasprobe1793955407940399361, completed09:00:01UTC deadline/observed/sustained/stoppedTRUE/noerrors/conflicts, thenrestoredandresumedautomaticbias withoutanotherchatcommand.09:00:17UTC requestedTRUE/automaticTRUE/inhibitedFALSE/bias_verifiedTRUE/resumeFALSE/healthyTRUE; newbiasawaitingfreshsamples. Exact2W notguaranteed; probe~6–9Wmeanactualexport. Meanacceptance−50..0 alignsunchanged50Wsustainedguard;180snoexportcountssincelastconfirmation, fixinglaterfalse0.7.3stop08:10UTC.

Durableownerintent/requested_automatic survivesinternalpause; ownerOFFcancelsresume. Restartorphanindependentlyauditsnativeordinaryprofile/freshstoppedgrid, adds30mincooldown, neverfabricatesproof. HA autonomouslywaitsPV<=1700stable120s/SOC>=63/positivequotes/healthyfreshdata thenboundedbattery2000W5min60floor, max2attempts/day. Largebattery_verifiedstillFALSE; native-end/fullcycleacceptance NOT yetproven. DoNOT manuallystart/re-enable/retestwhileHAwaits; inspectfreshautonomous_verification andguardreason. Largeproductiongatepreserved; continuousbias30/resume32/PV98positive/battery60/cap9300policyunchanged. Native104still20; workaroundusesExportFirstcap2, registercauseunresolved. Read-onlytodayobserverupdated; nobackupdeletionorPVlimitbypass/Coreupgrade.


Final09:01:07UTC continuousautomaticbias1793955603470585401 phaseRUNNING/observedTRUE, rollingmean−8.9W, requestedTRUE/automaticTRUE/inhibitedFALSE/resumeFALSE/healthyTRUE/error empty. Both physicalboundedtestcompletion and actualautomaticallyresumedcontinuousoperation are now observed. Batteryproof remains waiting. Deploymentlease releasedverified09:00:19UTC.


## 6 November2026 — sales0.8.1 ACTIVE,97%surplus and automatic measurement recovery

Sourceeb1e78c5f09538636cee077a48e90a5e0f447255. See docs/evidence/2026-11-06-surplus-097-081.md. solar097b-apply-20261106 verified/active_verified, backupd46d4096, unchangedCore2026.6.4. Owner explicitly prohibits further physicaltests; only localchecks, deploymentandread-onlystateconfirmation. Automaticcommissioningdisabled atstartup/ownerON. PVstart97/stopbelow97, samepositiveprice/9300W/batteryassistguards. Measurement-onlyconfirmedstop mayresumeownerrequest after60shealth/currentprice/independentnativeidle+stoppedgrid; knowncompletedcleanupretry supported. OwnerOFFwins. Startupmigrationrecoveredexistingdocumentedbiasproof, neverinventedbatteryproof.

Fresh5.3GiB enabledbackupafterownerindependentlyclearedspace; requestedfcb10fc6deletion NOTperformed. HA itselfrestoredafterprevious33sdatagap at10:58:18UTC; laterexternalOFF/ONrespected.10:59:33UTC realautomaticPVexport4442W/PV5168W/SOC99, RUNNING/observedTRUE/automaticTRUE/inhibitedFALSE/error empty; ownerconfirmedseeingexport. No furtherenable/testcommand sent byagent. Native104still20; battery_nativefullcycleproofstillFALSE. Lease released10:57:32UTC. Do not automaticallyruncommissioning orforceanyproofgate. Read-onlytodayobserverupdated accordingly. Spotyredesignimage isproposalonly, notdeployed; day/week/month/yearrequiresrealhistoricalaggregation, notmockdata.


## 6 November2026 —Spoty hub1.0.0 frontend-only deployed

See docs/evidence/2026-11-06-spoty-hub-100.md. Source2926b6107fb8029dfc012918293e5bf7580f11a2, spotui100-apply verified/file_written/activationnone,5exactreadbacks. /local/jarvis-spot-hub.html?v=1.0.0 embeddednativepaneliframe, topcontrols/netprice/actualfinanceperiods/reusedexistingchart+house/collapsedlegacyinformation. MainYAMLbyteidenticalcachetouchverified. NoCore/controllerchange/restart/invertercalls. PureNode+fakeDOMchecksPASS; independentreviewiframe-more-infoforwardingfixedRED→GREEN. ChromiumvisualrunblockedOSsocketpermissions; actualownerbrowseracceptancependingrefresh. Day/week/month/year are realretainedHAhistory, partial/missinglabelled, beyondretentionnotavailable. BackendfinanceAPIprototypeABANDONED/notpublished/deployed; doNOTaccidentallydeployit. Production0.8.1 remainedautomaticTRUE/healthyTRUE/RUNNING11:18:13UTC. No physicaltestsallowed.


## Spoty1.0.1 —originalhouseHUD and iframegraph repair

Ownerreportedmissingoriginalhouseandbottomstatistics. Source2d88372601a5f6cfc71aac4eeccca3ba61b5b32f; hub101-apply verified/file_written/activationnone,4exactcontentreadbacks. iframe now directlyloads existing/local/jarvis-power-sun.js, createsgraphinitsownrealm insteadwaitingforparentregistration. Houseindependentlyresolvesoriginalmedia-sourcehouseimage viaauthorizedHAcallWS, usesoriginalSVGbackgroundwithsame6state-labelpositions(4cornergauges+gridflow/batterypower). Direct4gaugesreadfreshstates; originalpopupclicksforwardparenthass-more-info. GraphkWhstatisticsvisibleagain. No servicesoninactiverender, no backend/HArestart/controlchanges. Cache-busted1.0.1 andbyteidenticalrootcachetouchverified. Pure/DOMRED→GREEN testscoveriframeload+houseindependence/image+indicators. Actualownervisualacceptanceafterreloadremainsneeded; executorChromiumstillblockedbyOS. No physicaltests.


## 6November2026 —continuousPV0.8.2 ACTIVE / Spoty1.0.3temperatureHUD

Source456766613cdb9f9b1f8972a0e72cfce7ebf5acaa, pv082applyverifiedactive_verified/backup6dc651eb/Core2026.6.4 unchanged,8filecontentsmatched. See docs/evidence/2026-11-06-continuous-pv-082.md. Removesregular15minPVstop/reconfigure byeligiblelast60sdeadline renewal+900s withNONATIVEWRITES; positiveprice/healthfresh<30/SOC97/nooverride/notexpired/automaticPVrunning gates, allsubsequenttickguardsretained. Local49controller+37adapter+2bias+NodepureDOMPASS, independentreviewnoblockers. No physicaltests; actualnextquarter/renewalacceptanceawaitsownerobservation. ChartcoincidencewithpriceNOTprovenasdirectpricedifferencebug: preowneroffautoTRUE/inhibitedFALSE; sourceforced15minwindowswereverified. last_sale_stop/recent10proofs/toplast_stop retainedforprecisediagnosis.

ExistingCorestartupcleanupretryedge DIDoccur: finalstopverifiedTRUE/conflictsnone butgenericstop_recoveryinhibitedrequestedauto; oneproductionownerONpv082-restore-owner-auto-20261106 afterfreshhealthyidle restores. ThisedgeisNOTfixedbythetimerpatch; doNOTclaimfullyautomaticbootrecoveryforarbitrarycleanupfailures. 11:48:27UTC0.8.2 actualautomaticPV RUNNING/healthyTRUE/error empty/grid−2584W/PV3497W. No testcommand. No moreCoredeploymentjusttoaddressbootedgeinthiswork.

Spoty1.0.3 small Bat./Měničtemperaturelinesinoriginalbatterybox, originalmediaimage+4gauges retained. Prior1.0.2stable99%timestampfix deployed (freshmatchingbackendtelemetry, stale/mismatchunknown) andlocalregressionPASS. Nativecontrollers/temperaturelimitsunchanged. Coreactivationrefreshescache; ownerCtrlF5loadsnewiframe. No privatearchiveAPIprototype deployed. Lease releasedafteractivation.


## Spoty1.0.4 —compact temperature icons side by side

Source221574bb56d143dbbf4be17e8305d4d14b6e54cd, hub104apply verified/file_written/activationnone,4exactcontentmatches; byteidenticalrootcachetouchverified. Nativebattery/inverterSVGicons replacesBat./Měničvisiblelabels; temperaturesalignedsame34%row at79/91.5% horizontalcentres,9pxdesktop/7.5pxmobile, accessiblefullCzechlabels/tooltips andsamepopupclicks. No controller/backendchanges/restart/physicaltests. NodepureandDOMchecksPASS includingalignment/values/freshSOC/no passivewrites. MobileCSSadjusted andcheckedinDOMmodel. Actual390pxvisualpreview NOTverified: localservernotreachablefromcloudbrowser(ERR_CONNECTION_REFUSED); shared-fileprotocolattemptexplicitlyblockedbybrowserURLpolicy. Stoppedbrowserattempts, no workaround/bypass. CUAcompletionsummarysent. DoNOTclaimmobilevisualacceptance; ownerneedsobserveafterrefresh. Localpreviewserverstopped. Screenshotprovidedbyownerwasduringearlieractivationpause; freshreadonlybeforethischange0.8.2automaticTRUE/inhibitedFALSE/errornone.

## Solar 0.8.3 / Spoty1.0.5 — 6 November 2026 12:13 UTC

Source d261918e02874122f8ec8d170e70c7b3a2490460; pv083-prepare/apply verified active_verified, backup47000a06, Core2026.6.4 unchanged. The exact no_surplus→bias preflight failure under the pre-existing SOC100 profile now leaves automatic PV eligible; cooldown30s. Confirmed normal PV cleanup retries retain original stop reason. HUD telemetry is now actually published in HA sensor attributes and selects fresh numeric reports; house fallback and today's plan15:45–17:45 Prague added. Local38 adapter+49 controller+4 recovery+2 bias tests and pure/DOM UI pass. No device tests or commissioning performed.

At12:13:14 runtime0.8.3 ready/automatic true, inhibited false, error empty; HA itself completed a stop_recovery(original recovery, stop_verified true, no conflicts) after startup and restarted ordinary automatic PV, awaiting fresh export. No assistant ON command required. UI HTML/JS/view readbacks match exactly. Keep battery_verifiedFALSE: large battery production remains blocked pending genuine native end acceptance; the prior SOC100 idle program is preserved and tiny bias is skipped when ineligible. Do not claim full battery operation, exact2W or phone visual acceptance. See docs/evidence/2026-11-06-pv-resume-083.md.


## 2026-11-06 — Energy0.10.0 candidate prepared, NOT INSTALLED

Refactor review branch `refactor/ha-control-cleanup-20261106`; source baseline060501cd69451f9047cb0baac182dc6c463a591c. Read-only profile admission, export-only production boundaries, pure policy, durable completed-plan evidence, strict30s measurement recovery and permanent queryable diagnostics/history. Removed automatic commissioning and duplicate production policy; retained explicit maintenance and old transaction cleanup.746 Python tests run/20 existing skips/0fail;11 Node suites pass; independent review findings fixed. Visual browser acceptance blocked by environment EPERM, and live0.10.0 physical acceptance deferred to explicitly authorized installation. See `docs/ENERGY-REFACTOR-0.10.0.md`. Do not install based solely on this prepared-source note.


## Energy1.0.2 reconciliation — installation authorized

Preflight found concurrently installed1.0.1. Reconciled prepared0.10.0 source with newer20W bias admission, completed-day identities and history API contracts.749 Python tests/20 existing PHP skips/no failures. Read docs/ENERGY-REFACTOR-1.0.2.md and docs/releases/energy-1.0.2-candidate.json. This source note is not an active runtime receipt; consult the private deployment work manifest for actual installation state.

## 9 November 2026 — manual grid heating 1.3.0 prepared
Owner approved hold3s on radiator, optional manual stop or shared CHILD-room24C stop. Existing21/22 automatic settings retained. Read-only grid admission at native reserve (actual request30%, native floors30%); no inverter/BMS setting changes. Above native programme reserve this grid-only exception is explicitly refused, rather than claiming switch-on determines energy source. Loss/staleness of grid/reserve/battery data or discharge>100W terminates the override; independent15s watchdog even when visible solar automation is disabled. No physical sensor values fabricated. All live1.2.3 resource/click/delayed-confirmation fixes preserved despite older1.2.2 public baseline.
46 Python tests and3 JS suites PASS, release manifest and diff checks PASS. Independent review identified stale-data watchdog and delayed gesture error rendering; both fixed with RED→GREEN regression tests. No physical24C test or radiator switching performed by assistant. Deployment pending until exact active runtime receipt. Initial disk0.9GiB blocked preflight; owner independently deleted backups, fresh3.4GiB/backup_ready true confirmed. No assistant backup deletion.


## Manual grid heating1.3.0 ACTIVE — 9 November2026 20:07:45UTC
Source87e0b5f771eec69adff7bd8ce0746e138b83ba89; heat130-apply-20261109 verified/active_verified, Core2026.6.4 retained. Both room runtime sensors1.3.0 and heating UI ready1.3.0 confirmed. Seven deployed file contents matched; final bridge activation independently confirmed hashes. Heating settings revision f74ff1d369b4b74ea5fb120bdb70876c78c1b28435d90e443d64d4d39a89f4d4 retained (21/22C, normal manual battery50%). Allsix native battery floors still30%, grid connected. Owner correction explicitly confirms30% reserve must never be bypassed: grid_manual bypasses only radiator50% gate; requires battery at/below all existing native reserves, never edits inverter settings. At24C child sensor clears exception; off retains existing stop-today lock. 46 Python+3JS suites passed; independent review issues fixed with regressions. No physical radiator activation, artificial sensor values or physical24C test performed. Refresh dashboard to load heat130 resource. Existing AppleTV startup protocol timeouts are unrelated and unchanged.


## Heating plus1000W charging1.3.1 prepared — 9November2026
Explicit click bypasses50% radiator cutoff and adds owned~1000W battery gridcharge, preserving native30% minimum. Shared child24C/manualOFF stop both and CASrestore prior native settings. New current~19A fromvoltage, active-slot target90/Grid (never lowers30), slotrollover, two-room sharing and actualcharge measurement admission. Native charging IO outside heatinglock preserves24C/OFF watchdog. ExternalOFF preventslateON; OFFworks afterfailedsave. Independentreview findings fixedwith RED→GREENregressions. Private heating-runtime.json preserveslaststop/chargephase.778root tests PASS/20existing skips,59heating PASS,4UI PASS;manifest/diffchecks PASS. Isolatedpinnedtestdependencies resolved initialenvironmentfailures. Deployment and physicalacceptance PENDING. See docs/superpowers/plans/2026-11-09-heating-charge.md.


## Heating and owned1kW charge1.3.1 ACTIVE — 9November2026
Source7460274e791b64d31dcac3fcafdb4a39d0730ff3; heat131-apply-20261109 verified/active_verified, bothheatingruntimes1.3.1/UIready1.3.1/chargeridle0.6.7, Core2026.6.4 unchanged. Nineexactlivefilematches. Native physical acceptance confirmed real heater consumption AND simultaneous battery gridcharge below50% withSOC30. Subsequent explicitOFF confirmed heater0W, chargeidle/gridchargeOFF, allsixprogrammeSOC30/Disabled andpriorcurrent175 restored. One-shot acceptanceautomation removed; originalautomations.yaml restored byte-for-byte and reloadverified. Raw operational readings and receipts kept privately in jarvis_workspace/heating-charge-131-receipt.json. No artificialtemperature or physical24C forcing; that boundary verified in offlinecontroller/adaptertests. Tests778rootpass/20skips +59heating +4UI. Temporarycharge target>=90 never lowersnative30% protection and isrestored atstop. BothradiatorsOFF after acceptance; owner canuse newtopení+dobíjení1kW button. No persistenttestactions remain.


## Per-radiator grid charging1.3.2 prepared —10November2026
Owner correction:1000W charge PERmanualgridradiator,2=>2000W,1=>1000W,0=>originalrestore. Sharedsession/currentresize retainsoriginalbeforeimage; deduplicatesrooms, tracksownedmembers+pendingOFF, excludesunrelatedautomaticON. Newtargetrequiresfreshpowerproof.30%nativeprotection/24C unchanged. Tests780rootpass/20skips +63heating +10charge +manifest/diff; independentreview countfindingfixed. Source/deployment/physicalcountacceptance pending. ExistingownerbothON intent mustbe restored after backed-uprestart; temporary startup acceptance stages1/2/1/2 thenremoveexactautomationdefinition.

## Per-radiator charging 1.3.2 ACTIVE — 10 November 2026
Source 5965a9ae6ce52ade29b5de70e631884128bb09da deployed; backed-up Core restart completed, but admin activation HTTP outcome timed out (job unknown/plan activation_failed). No mutation replay. Independently reconciled all six permanent file contents exactly and runtime 1.3.2; owned two-heater charging, actual grid import and battery charging confirmed. Physical acceptance 2→1→2 confirmed corresponding requested 2000→1000→2000W and actual charging about 1.87→0.90→1.87kW. Both heaters left ON under original owner intent. Native reserve and 24C behavior unchanged; no artificial temperature forcing. Original automations.yaml restored byte-for-byte; cleanup active_verified with solar automation ON. Private evidence: jarvis_workspace/per-radiator-charge-132-receipt.json. Tests:780 root pass/20 existing skips,63 heating,10 charge,4 UI, manifest/diff checks. No persistent test actions remain.

## WiFi communication tolerance prepared — 10 November 2026
Owner requested180s tolerance for running grid heaters and standalone charge. Separate unavailable/stale telemetry from known hazards and sale ownership. Running sessions hold existing settings without writes for180s since missing telemetry detection, expiry stops/restores, recovery resets timer; fresh data still required for starts. Grid/link and charge freshness thresholds aligned60s. Known temperature/mode/fault/reserve conflicts, manualOFF and standalonedeadline/target remain immediate. Timer reset across sessions. Independentreview findings addressed. Root/heating regression tests include179/180boundary, recovery, knownfault and confirmed-onlyadmission. Live activationpending; no WiFi intentionally disconnected.

## WiFi tolerance 1.3.3 ACTIVE — 10 November 2026
Source419371f0706f3da0341a462b927463bbe600b554; wifi180-apply verified/active_verified, Core2026.6.4 unchanged. Heating1.3.3/charge0.6.9/UIready confirmed.785root tests PASS/20skips,64heating;manifest/diff pass. Runningmanualgridheat andstandalonecharge tolerate missingtelemetry180s afterdetection (staleness60s); recoveryresets timer. Knownhazards/OFF remainimmediate; native30reserve unchanged. No physicalWiFi disconnect test. Bothheaters restored topriorgrid_manualON with2kWcharge requested/observed; one-shotresume removed, originalautomations restored byte-for-byte and reloadverified. Private receipt jarvis_workspace/wifi180-receipt.json.


## Room panels and lock tap — 12 November 2026
Six room panels deployed with metrics separated from image, compact heating controls, direct swipe/arrow/chip room navigation. Unlocked lock icon sends lock.lock on explicit tap; no tap-to-unlock added. Five targeted Node suites pass. Module and private dashboard CAS writes verified with independent exact readback. Existing frontend resource retained; client reload required. Phone visual/gesture acceptance and physical locking remain unverified. See docs/evidence/2026-11-12-room-layout-swipe-lock.md; preserve card.js + room-panel.js bundling on future module refreshes. No Core restart or heating policy change.


## Owner correction: spatial room UX — 12 November 2026, 19:34 Prague
Supersedes the earlier sequential carousel and readings-above-image layout. Heating controls are above the room image; temperature/humidity share a bottom overlay row inside the picture. Four-way swipes are recognized only on the picture surface, with touch-action:none there and ordinary page scroll elsewhere. Named directional buttons show only real adjacent rooms from the floorplan; walls do not wrap. Home return, room chips and lock tap retained. Five targeted Node suites pass, including actual pointer-handler navigation, excluded controls, pointer cancellation, four direction thresholds and layout order. Both CAS writes room-ux2-module-write-20261112 and room-ux2-dashboard-write-20261112 verified; independent exact readback matched. Module revision aa7cbea06224456f5b0e5c6785106b7cd2b1efc58d3bc44f7f03c8166ca8e144; dashboard62012f0ddf293a09869cbbc48efa8d08bce7ac072a95817bf8dd7567f3dcff6c. Client reload and actual iPhone gesture/visual acceptance remain necessary. No physical device action or Core restart.


## Latest owner UI correction — 12 November 2026, 19:48 Prague
Removed all directional labels/arrows, room chips, duplicate room heading, explanatory hint and duplicate home button inside the room card. Existing native HA top-left arrow now uses explicit back_path=/hlavni-prehled/domov in all six room subviews. Heating controls remain above image. Temperature/humidity are now compact13px normal-weight readings, centered at image bottom in two rows, without visible text labels; accessible names and native more-info remain. Spatial four-direction gestures unchanged. Five targeted Node suites and six back_path/config-preservation checks pass. Live CAS module room-minimal-module-20261112 and dashboard room-minimal-dashboard-20261112 verified with exact readback. No Core restart or physical device action. Client reload required; latest iPhone visual confirmation remains pending.


## Heating status and lock click repair — 12 November 2026, 20:02 Prague
Owner reported missing heating states and lock neither locking nor unlocking by tap. Touch-handler defect: pointerleave after pointerup unconditionally marked the tap held and swallowed synthetic click. Fixed to cancel only an active pointer hold; click propagation stopped at custom button and native lock tap_action set none. Explicit lock-icon tap now sends lock.lock from unlocked or lock.unlock from locked, with duplicate pending guard and no fabricated physical state. Offline/transitional states do not toggle. Long-hold history retained. Tests exercise actual rendered button onclick after touch release/pointerleave, both lock services and offline guard.

Heating actual on/off now appears next to radiator icon in both heated room views and alongside current controller reason below image; main floorplan reason labels now include actual switch state. Real runtime read at18:58UTC showed both off/Čeká na slunce, heating1.3.3. Five focused Node suites pass, YAML includes/back paths retained. Module heat-lock-touch-module-20261112 and dashboard heat-lock-status-dashboard-20261112 verified, independent exact readbacks matched. Source095119bbc64e7323f31d49c7757c20a39a8a6781. Client reload and physical user tap acceptance pending. No actual door/radiator action or Core restart performed.


## HomePod home message input — 12 November 2026, 20:23 Prague
Owner requested tapping living-room bullhorn to speak a message at home. Existing icons already navigate to /hlavni-prehled/vzkaz, but the message card only supported browser SpeechRecognition. Added editable 500-character message field and explicit Přehrát doma action, supporting iPhone keyboard dictation without Web Speech API. Optional browser dictation now fills the draft for review. Existing HomePod/Piper route and unrelated energy/history module code preserved. Blank, length, offline and duplicate-send guards retained; errors keep the draft. No message text is interpreted as a device command.
Source20a61ac40a7133adeaf5715960d1ddc06b59abca. homepod-message-module-write-20261112 verified; independent live read exactly matches www/jarvis-home-message.js revision11bfaa6169760bd2a6d866b35e4083b79d8cde890b6e14cd91034a2b0db632a4. Six focused Node suites pass. No Core restart, actual spoken test or iPhone visual verification. Client reload/cache refresh required to activate updated JavaScript in an existing session. Physical audio acceptance remains pending.


## Direct floorplan voice recording — 12 November 2026, 20:36 Prague
Owner corrected the interaction: tapping the bullhorn must begin recording immediately on the household overview, without navigation, a separate page or keyboard dictation. Both existing floorplan bullhorns (main and living-room view) now use custom:jarvis-home-intercom. Explicit tap directly requests microphone and opens a compact recording dialog over the same floorplan. Odeslat domů stops recording and uploads/plays the actual voice clip on the existing HomePod route; Zrušit discards. Thirty-second cap, single-flight guards, permission/offline/upload errors and cancellation of late microphone grants. iPhone uses MP4/AAC when supported; other clients capture PCM WAV through Web Audio. No speech recognition, LLM or interpretation as a device command. Uploaded clip uses HA authenticated local media and is scheduled for removal after90seconds while the client remains open; closing/reloading the client before cleanup may leave that generated clip in HA media. No general recording retention service was installed.
Source c673505cf7d3463dad9730ce0cc917264ee1fcc3. Build www/jarvis-home-message.js using prepare_intercom.module() (existing home-message.js plus intercom.js); do not overwrite with only one source. prepare_intercom.patch() preserves private YAML and is idempotent. direct-intercom-module-20261112 and direct-intercom-dashboard-20261112 both verified; independent exact readbacks matched module 9a5acb2875991bbce28cc165e6e024e4d550492e9de93c1489cbe725354dc8d7 and dashboard 6bd4f2a3cfc2683c3e2b5c2014aadcb415b05bd737f9a51a5ce744ee7d11d3f3. Seven focused Node suites pass, including MP4/WAV branches and cancellation/errors. Bundle syntax and YAML/size/idempotence checks pass. Browser test intercom-browser.cjs was attempted but Chromium is blocked by the executor socket policy (Operation not permitted); no screenshot, actual microphone recording, iPhone acceptance or physical HomePod playback is claimed. No Core restart or voice/heating controller changes. Client reload required.

## Room metrics and intercom registration — 12 November 2026
Owner screenshot shows an error element at the new bullhorn. Live home-message bundle includes intercom, but configuration still references the unchanged 20261027-3 URL and the home-status resource does not register intercom. The client cache explanation is consistent with this; exact iPhone error text is unavailable. Added intercom registration to the existing floorplan/room bundle so it does not depend on the older extra module. Build using prepare_intercom.status_module(); preserve all three sources. Metrics now have individual dark compact buttons, thermometer/water icons, stacked centrally at picture bottom. Eight focused JS suites pass; syntax/diff checks pass. No Core restart or physical action. Deployment receipt/readback and iPhone acceptance tracked below.

Deployment: room-sensors-module-20261112 verified file_write, independently read back exactly; revision4428979fe44c14b349d1202a9ab45d900d36ab79e120e9dd725e0140a680c42d. No restart. iPhone refresh/visual acceptance and microphone/playback remain unverified. Source local commit32278f7; combined commit/push command was rejected by automatic approval review for missing explicit publication authorization/unverified destination trust. Do not treat source as published. No alternate publication route attempted.

Owner explicitly authorized GitHub publication in the following turn. Publishing verified source through the connected GitHub API; ordinary git push lacks credentials in this workspace.

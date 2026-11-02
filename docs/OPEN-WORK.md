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

Guided family workflow trigger “Nauč se nového člena rodiny”: recognized full-scope owner, name+consent,5training answers,3independent controls+windows; percent is completion, not identity probability. Persistent private state across restart, safe pause/cancel, bounded attempts, no training actuation, new profile unprivileged. Fresh operator family-control.json authorizes/revokes lights only using validation proof and identity-bound revision; never locks, no voice-only permission grant. Library/docs docs/voice/FAMILY-VOICE-GUIDE-CS.md includes light/heat/TV/status phrase examples; this does not add unimplemented heating device actions.

HomePod fix withholds only native terminal TTS-start callback during external output, preserving Core diagnostics/controller, original callback restoration and unrelated routes. Actual HomePod RAOP completion still gates silent terminal end/followup. This avoids arming firmware acoustic stop from the external-speaker TTS stage; physical button stop remains. No claim of arbitrary-speech barge-in or acoustic success before physical use. Tests127speaker51HomePod49companion pass; independent final review Important inter-profile-validation finding fixed with actual whole/window rival comparisons and approval-time revalidation. Local unrelated full addon suite stalled in its official MCP SDK network test and was interrupted; rely on full published CI before declaring overall validation. Deployment pending.

Rollback note: after cohort activation, roll back the live matching bank through MatchingControl before reverting Python to1.1.8, because the old scorer cannot interpret structured positive/exclusion banks. Code-only rollback is insufficient. Family approvals retain independent holdout embeddings privately for current-rival revalidation; these are erased with the subject profile. Progress never implies biometric certainty.


## Completion check — native composition fixture

Correction to earlier diagnosis: the full suite did NOT hang in the official MCP SDK test; that test passes in isolation. Verbose full run identifies tests/test_voice_stack.py. Its fake Pipeline lacked the real Core event_callback, so TTS raised before the test's unbounded playback-start wait. Fixture now models native callback delivery separately from Core diagnostics, verifies withheld native TTS-start in both setup orders, and races playback readiness against task failure with a5s bound. Missing-callback regression now surfaces OutputError immediately. All240addon tests pass20skipped;127speaker51HomePod49companion pass. Independent test-fixture review found no Important/Critical issues. Set tests CI job10min maximum. No deployed Python/runtime/bank change or extra Core restart required. Runtime speaker1.2.0/cohort_margin_v1 active, output1.1.0 configured, anchors1/auth1 preserved. Source d8b2d592a7c3aaec1486b14ff7034edee425a2b9; deployed-bank revisionc18052f5d63d3d9e825e23ab5448442813fe73cdb0d50b3b4763e6b4729a82d4. New full CI pending; ordinary acoustic performance remains unproven until normal use.

## Completion verified2026-11-01

Published test-fix sourcefad4825012b8f33b4b01c18c6440ffb5d16bd330 passes full GitHub CI: pushrun41314032755 and PRrun41314039808. Push publication succeeded; lab catalog lists that exact source and verified packages. All240addon tests pass20skipped,127speaker51HomePod49companion locally pass; native composition4tests pass in both setup orders and on failure/cancel. Earlier SDK diagnosis corrected: actual hang was the missing native callback in the composition-test fixture, now fixed with a5s fail-fast bound; CI tests job max10min. Runtime source code is unchanged fromd8b2d592a7c3aaec1486b14ff7034edee425a2b9: Green speaker1.2.0 ready/cohort_margin_v1 active with bankc18052f5d63d3d9e825e23ab5448442813fe73cdb0d50b3b4763e6b4729a82d4, output1.1.0 configured/native-TTS-start withheld, auth1/anchor1 preserved, family guideidle/ready. No additional calibration requested. Physical ordinary-use accuracy remains unverified; do not turn CI/synthetic success into an acoustic or100% biometric claim. Full source-backed evidence in docs/evidence/2026-11-01-voice-completion-verified.json.

## Real owner test and command-path correction — 2026-11-01

Real owner ordinary-use attempts at14:23:22UTC and14:24:02UTC were recognized AND authorized (whole0.5749/0.7034, exclusion margins0.2907/0.3187). They were not speaker mismatches. Both polite light commands bypassed exact local resolver and reached the LLM, whose device-control tools are deliberately blocked. Their followups produced0/0.4s voiced captures containing exact English STT prompt echoes, wrongly treated as failed speaker verification and spoken about. This explains misleading voice-denial loop. Earlier2.41s command genuinely skipped inference under2.5s minimum; threshold/anchors/bank remain unchanged.

Speaker1.2.1 canonicalizes only finite courtesy wrappers and the exact observed light-command rationale, then issues one-use grants bound to canonical text/action/targets. No arbitrary clause stripping, negated/conditional/multiple action shortcut. Confirmed local actions return empty speech; errors/unverified state remain spoken. Empty speech closes followup before TTS. Exact observed STT prompt echoes end silently before voice/model processing. Tests cover observed transcripts, negative clauses, canonical single-use target grants and actual agent empty-speech/no-followup boundary.

HomePod1.1.0 has3native satellite aborts and2completed playbacks. Abort source cannot distinguish physical button/acoustic/other firmware cause; do not claim full handoff/interruption repaired. Preserve physical button and await RAOP completion; new local silent commands avoid unnecessary playback/followup entirely. No additional owner calibration. Retention approved earlier: deleted exact old backups49a4ece2/798f89b2 with metadataCAS, preserved newest3/protected, free1.4→2.7GiB for required restart backup. Deployment pending; physical post-fix result pending.


### Command-path fix active — 2026-11-01

Source7be6d5645c2a4eda6ccd2d484dc9cd57bcc5b556: local130speaker51companion240addon20skipped pass; CI PR41316559319/push41316553446 all success including lab publication. Independent command-path reviewer found no Important/Critical issues. Apply handoff121-apply-20261101 ended unknown/admin_upstream_outcome_unknown after restart; no replay. Backup31d932a5. Independent postboot6/6exact readback plus runtime1.2.1/ready and command_policy canonical_local_verified_success_silent_v1 confirm activation; auth1/anchor1/bankc18052f5d63d3d9e825e23ab5448442813fe73cdb0d50b3b4763e6b4729a82d4 preserved. Microphone idle/unmuted, HomePod1.1.0configured. Lease release verified. Physical post-fix ordinary-command test pending, native HomePod abort source unresolved; do not claim full acoustic handoff fix. Evidence docs/evidence/2026-11-01-polite-command-active.json.

## Owner changes policy: public commands, optional familiarity —2026-11-01

Explicit owner request removes voice-match prerequisite for ordinary controls and asks passive gradual learning/names; not another calibration cycle. Speaker1.3.0 public_controls enables supported local exposed lights for everyone after activation, preserves one-use exact action/text/target grants and silent verified success, leaves locks/profile administration protected. Public commands do not wait for embeddings: at most2ephemeral background inference tasks may learn a suitable longer utterance. Active family/owner training still cannot actuate. Unknown ordinary conversation no longer speaks voice-denial loops.

Separate bounded private familiarity table:16clusters/12embeddings,30day inactive expiry,quality/no playback/2consistentwindows,6distinct utterances3conversations before optional name question after a conversational answer, once/day; explicit same-current-voice name answer within120s, occasional name only every6conversational turns. No private principal or authorizations from familiarity. Review found recognized but unprivileged legacy profile could otherwise expose private voice context in public mode; red regression reproduced, fixed by personalization_only/no profile or memory_id, guest context. Immutable owner matching bank unchanged. Existing TV/heating actuator capabilities are not expanded by this voice-policy change. Plan docs/superpowers/plans/2026-11-01-open-household-voice.md. Deployment pending.

Familiarity1.3.1 follow-up: normalized-sentence hashes prevent separate recordings of the same sentence from maturing the cluster. Natural short name answers are provisional in-memory only, bound to device/conversation/cluster120s; actual same-cluster voice match on a later suitable turn is required before storing the label. Foreign match clears pending; another conversation cannot attach a name. No private principal/grants. Two regressions for provisional and cross-conversation naming, plus duplicate sentence regression pass.


### Public voice mode1.3.1 active —2026-11-01

Source86a02854bfd256ed83dd9b1cffebd6c2e9b00a73,144speaker54companion240addon20skipped tests pass, PR41320997804/push41320993790 allCI and lab publication success. Independent reviewer: no remaining Important/Critical; unauthorized recognized-profile privacy leak fixed before publication, sentence dedup red/green, provisional short-name label attribution explicitly not identity proof. Apply public130-apply-20261101 and public131-apply-20261101 both unknown after upstream restart timeout, no replay. Backups85f97361/df2a34c6; oldfc76d3f2/bbb7d9bf exactCAS deletion verified, latest3/protected preserved. Postboot runtime1.3.1ready/public_local_lights_silent_v1/public_controls[light],6/6sourcefiles exact, originalauth1/anchor1/bankc18052f5d63d3d9e825e23ab5448442813fe73cdb0d50b3b4763e6b4729a82d4 unchanged. Familiaritypersonalization_only active,0clusters/names/samples initially; no permission grants. WakeJarvis+HeyJarvis both assistantsJarvis, micidle/unmuted; lease release verified. No additional calibration. Physical post-fix ordinary use pending; HomePod native abort remains unresolved. Full evidence docs/evidence/2026-11-01-public-voice-active.json.

## End-to-end voice refactor1.4.0 —2026-11-01

Live audit: real bare and room-specific public lights completed silently, but Zhasni všude bypassed local handler; context:### opened another conversation; independent direct acoustic light detections used obsolete unverified-speaker error. HomePod10/11completed,1native abort; do not invent firmware root cause. Actual child-room light was on, living-room light off; no diagnostic actuation performed. Active STT languagecs-CZ is already correct.

New pure shared Python command contract under custom_components/jarvis_voice_common, used by authorization, room resolver and dialogue policy. Supports selected assistant prefixes/courtesy, explicit light synonyms and explicit all-house exposed lights only. Negative/conditional/multiple/quoted commands do not execute. Finite grammar and one-use canonical text/action/target grants remain; lock strict checks and private identity unchanged. No-op scaffolding including context:### and standalone hesitation ends silently. Local commands release session counters/recent-device state rather than keeping phantom followup. Native RAOP-completion gate/physical cancel unchanged; direct acoustic light commands still blocked outside selected wake then speech flow, with truthful reason.

BackgroundLearning separates max2optional tasks, inference-only8s timeout, Future-compatible HA executor ownership, shutdown drain and safe counters from Coordinator. Public commands still skip voice inference; training priority retained; summary reads move off event loop. Reviewer Important findings reproduced red: quoted all-house action, quoted lock confirmation, quoted owner profile deletion, executor write-after-shutdown and native Future orphan. Fixed raw quote guard at shared parser/confirmation/Coordinator boundary and owned/drained actual executor Future. Final independent review no Important/Critical,27targeted checks passed. Local151speaker54companion51HomePod15diagnostic244addon20skipped tests pass. Spec/plan under docs/superpowers. Source publication/deployment pending; no new calibration.


### Voice refactor1.4.0 active —2026-11-01

Source5943f9f17d2739ba39fa09ef1b95a744200296cb, CI PR41327946519/push41327942512 allsuccess including new fullHomePod/diagnostic jobs and laboratory publication. Local151speaker54companion51HomePod15diagnostic;244addon ran224passed20skipped. Independent final review no Important/Critical after quoted-command/profile/confirmation and native Future/drain regressions. Apply refactor140-apply-20261101 ended unknown/admin_upstream_outcome_unknown after restart, no replay; backup15a42412. Postboot13/13exact source readback, speaker1.4.0ready/sharedcontract1.0.0/public_local_lights_silent_v2, optional worker0pending/0failed/drained, familiar1cluster1sample/0named preserved, auth1/anchor1/ownerbankc18052f5d63d3d9e825e23ab5448442813fe73cdb0d50b3b4763e6b4729a82d4 unchanged. HomePod1.1.0configured. Actual HA synthetic text conversation test complete/passed: continuationtrue,true,false, factual recallpassed; temporary fictional private-memory isolation/restart/forgetpassed; native turn probepassed. No household actuation/audio for native test. WakeJarvis+HeyJarvis with both assistantsJarvis, micidle/unmuted. Lease release verified. Exact old1ce5f3f0 retention deletion verified, newest3/protected retained. Physical post-refactor voice/audio use pending; no arbitrary-speech barge-in or biometric/replay claim. Evidence docs/evidence/2026-11-01-voice-refactor-active.json.


## Fast silent local lighting — 1.11.2026 19:14UTC

Source b5d379ca8f65b6734515815e93acaef42e0b5c4e; CI41340241063 and41340235983 success. Actual STT transcript `Rozsvítit světlo v obýváku.` previously bypassed the imperative-only parser and entered identity/LLM/TTS (15.761s total with7.051s HomePod output). Shared command contract1.0.1 now normalizes exact light infinitives. Diagnostics1.0.3 routes already installed acoustic `rozsviť`/`zhasni` directly into the existing guarded native intent, scoped to exposed lights in the source microphone room, without STT/embedding/LLM. Successful actions retain empty speech. Ordinary Jarvis wake/full named-room commands remain delegated.

Independent review found cancellation cleanup before native start and an unnecessary optional-backend readiness dependency; both fixed with RED/GREEN regressions. Relevant tests:56 companion,152 speaker,51 HomePod,21 diagnostic,244 addon (224passed/20skipped). Actual pinned Core2026.6.4 execute/validate methods plus real grant and room executor passed against a simulated HA boundary; measured simulation time is NOT household latency.

Green speakerfast-plan-20261101/apply verified/active_verified19:14:31.591337UTC; backup43f425d5. All11 deployed source/recovery/manifest files exact; postboot direct statuspublic_light_fast_path/version2, sharedcontract1.0.1, nativeguardtrue, speakerready, nativeprobe passed. New actual-registry probes resolve both STT infinitives to the living-room light. Satelliteidle, muteoff, HomePodconfigured, one profile retained. Lease releaseverified. One old unprotected backup5deec9b6 removed under the accepted preserve-latest-three/protected cleanup; protected/latest snapshots retained. No Core upgrade, firmware change, household recording or physical voice test. Acoustic false triggers and arbitrary-speech barge-in remain unverified/unchanged. Detailed receipt: docs/evidence/2026-11-01-fast-silent-lights-active.json.


## Complete light utterances and television guard — 1.11.2026 19:54UTC

Source 3552622112d5c96e48da1c61ad5a6571a1e37129; PR/push CI41342593814/41342588609 success; all20 changed existing/new Git blobs exact. Acoustic verbs now activate full native STT with0.75s initial continuation; real speech retains native VAD duration. A named child-room suffix is preserved and an explicit transcript verb overrides an acoustic hint. Bare fallback requires actual consumed-audio silence expiry and no native VAD_START; low identification probability/provider no-text cannot establish silence. Accepted local light calls are silent even before delayed device state; bounded dispatch observations are retained. Public exposed-light targeting and protected lock policy preserved. Known TV/media activity blocks standalone acoustic hints; ordinary explicit Jarvis remains available. Suppressed runs cannot pause TV or cancel an owned HomePod answer. Generic Hey Jarvis secondary selector is now no_wake_word.

Independent review found/fixed two P1 defects with RED/GREEN regressions: weak identity VAD mistaken for silence, and downstream routing.activate cancellation despite session suppression.61 companion,154 identity,18 diagnostics,53 HomePod,244 addon tests (224passed/20skipped). Actual pinned native execute/validate/VAD/stream plus real adapters,grants,companion and agent methods passed five whole-flow simulations, including late continued speech and TV suppression. Physical API off/restore probes for living and child lights both verified; state reports arrived140–141ms after service response. This is not microphone recognition proof.

Green natural-utterance-prepare/apply verified/active_verified19:42:30UTC; backup60a8e25e, all27 source/recovery/manifest files exact. Postboot: speaker1.4.1 ready, sharedcontract1.0.2, nativeguardtrue, output1.1.1 configured, directwhole_utterance_lights/v3, six native VAD probes passed, both actual child-room grammar probes resolve light.aqara_wall_switch_eu in area jidelna. Microphoneidle/unmuted, one voice profile retained. No HA Core/OS upgrade.

Selected private Jarvis wake cutoff restored from0.8 to previously tuned0.98 using the same private weights. Native compile d6ca258e9bc8 passed. Backed-up install natural-tv-wake-install verified19:53:34UTC, backup4ef03063; uploadca296c830be1 completed and device online with expected/deployed hash1312060e. Firmware config revision89dab3881e915eab70e46d23ea9e8e1040944ae42444b60058e4e8da06209b3d. This stricter threshold is not independent acoustic validation. Secondaryno_wake_word survives device reboot. Both leases released. Old unprotected9f916d44/8bae64d7 removed under accepted keep-latest-three/protected cleanup; protected/latest backups retained. No new household recording or private weights published. Actual post-update household microphone/TV acceptance remains pending; arbitrary-speech barge-in unavailable. Detailed receipt: docs/evidence/2026-11-01-natural-light-utterances-active.json.


## Loud-room wake regression — owner acceptance still open, 1.11.2026

Owner reports Jarvis/Jarvisi not usable with loud television after the stricter cutoff. Fresh20:00:54UTC read: microphone unmuted, selectedJarvis, secondaryno_wake_word, satelliteidle, private Jarvis cutoff0.98. TVon/AppleTVplaying. One postboot19:57:01 activation was suppressed by the media guard; directhandoffs0/blocked1. No postboot explicit Jarvis STT run observed. This identifies the acoustic activation boundary to investigate, not an exact DSP/model root cause. The previous strict-cutoff deployment is NOT an accepted solution to noisy-room recognition. Do not claim household acoustic success or lower the threshold blindly and reintroduce false TV activations.

Required next evidence: a short owner-coordinated quiet/noisy microphone comparison containing actual Jarvis/Jarvisi; physically press the satellite button for the missed words so they enter a bounded, explicitly armed private capture. No new capture was enabled in this investigation. Compare wake detection and TV-only false triggers before choosing acoustic/model changes. No code, firmware, device state or energy contract changed. Evidence docs/evidence/2026-11-01-noisy-room-wake-diagnosis.json.


## Terminal suppression completion — active locally, publication pending, 1.11.2026 20:15UTC

Owner completed the requested quiet/noisy test and reported the speaker still blinking. No new runs or audio clips were received. Exact ESPHome2026.10.1 RUN_END/STT_VAD_END, stop-loop and set-state bodies reproduce the stuck AWAITING_RESPONSE target when suppressed RUN_START/STT_VAD_END/RUN_END arrives in a batch before the device loop. The adapter now removes unused prepared TTS before RUN_START and relies on native RUN_END to stop capture and targetIDLE; no premature VAD_END. Both new regressions were RED then GREEN;20diagnostic/53HomePod/154identity and244addon (224passed/20skipped) passed. Independent review noP1/P2; five actual pinned Core flow simulations passed. Other silent-run paths and noisy-room accuracy are not declared fixed by this narrow test.

Local Git source fe6e4f8c5d676ddcf99fb2fb3e01029f713ad084 is NOT published: automatic approval review rejected GitHub disclosure and still rejected after authenticated owner/destination verification. Do not retry publication without explicit user authorization or bypass via another publication route. The already-authorized local repair was deployed directly through Jarvis, with this deviation explicitly recorded in private release metadata. Public HEAD remains29c28fbd2dcee44ab1f1a6f634eab6975a92f27e.

Deployment terminal-protocol-prepare/apply verified/active_verified20:15:30UTC, backupa7af12c8. All7source/recovery/metadata hashes exact. New boot20:14:59, diagnostics1.1.1/directv4active, nativeVADprobe passed, HomePod1.1.1configured. Jarvis primary, secondaryno_wake_word, satelliteidle, LEDentityoff. Microphone restored unmuted and readback verified20:15:50. Recordingcapture null/no new clips. Lease releasedverified. No OS/Core version upgrade, no firmware/model threshold change or backup deletion. Owner was asked to try Jarvisi kolik je hodin with TV; physical acceptance pending. Private receipt jarvis_workspace/voice_diagnostics/terminal-protocol-receipt.json and local docs/evidence/2026-11-01-terminal-completion-active.json. Latest public source remains older until authorization.

## Publication approval resolved — 1.11.2026

Owner explicitly approved publication in the next chat turn. Connected GitHub published source 9548ba1b6d9f40501811d11a5df06e830e67a1ce after CLI HTTPS authentication was unavailable. Its tree ecaebbf23b3d69b38b29e8273f45b977c1b85987 exactly matches reviewed local tree e3318c22ebb54787a4d2fdccc018f347ef63d69e, including the deployed source bytes. Public source is now available; the earlier local-only status is historical. PR41346386783 and push41346382128 completed successfully, including tests, container checks, backup-DAV, energy chart and laboratory publication.

CAS metadata-only plan terminal-publication-metadata-prepare/apply verified; recovery release records published_source=9548ba1b6d9f40501811d11a5df06e830e67a1ce, local_patch_source=fe6e4f8c5d676ddcf99fb2fb3e01029f713ad084 and explicit owner authorization. Private terminal receipt updated, lease releasedverified, no restart or new firmware/acoustic change. Physical wake/TV behavior still requires owner confirmation; agreement to Git publication is not voice acceptance.

## Owner-attended wake cutoff comparison — 1.11.2026 20:38UTC

After terminal cleanup owner still reports no Jarvis/Jarvisi response. Three postboot acoustic light hints completed suppression without wedging, but no explicit Jarvis STT run was observed at cutoff0.98. A new physical button sample through the existing local Speech-to-Phrase pipeline successfully captured6.03s (peak−1.43dBFS, RMS−15.31dBFS, clipping0%). Its deliberately non-command phrase yielded no-text in the limited grammar; that is not absent microphone input. Metrics do not establish intelligibility, SNR or wake scores. Raw recording stays private on Green; no audio or private weights were published. Normal Jarvis pipeline was restored and verified.

A single-variable live comparison restored the previously deployed cutoff0.8 using exactly the same private model weights. Configrevision300e51323520226c1dc481243ec8984c6e03ad9bc6e4ff4e63ae8f70d08c1494 matches the previous baseline. No new ASR/intent/HomePod code, Core/OS update or generic Hey Jarvis activation. Compile wake-calibration-compile-080/native752cd28ca5a3 verified. Backed-up install wake-calibration-install-080 verified20:38:47UTC, backup4136623a; uploadf7dfa7f028ec completed, deviceonline with expected/deployedhashcbdb20ba. Fresh native metadata confirmscutoff0.8, primaryJarvis, secondaryno_wake_word, microphoneunmuted, satelliteidle, backend directadapterv4. This is deployment evidence, not acoustic success; owner must now test actual activation and unwanted TV triggers. One old unprotected15a42412 deleted with fresh CAS under accepted keep-newest-three/protected cleanup, freeing needed space. No blanket deletion. Private receipt jarvis_workspace/voice_diagnostics/wake-calibration-receipt.json; public receipt docs/evidence/2026-11-01-wake-cutoff-comparison.json.


## 1.11.2026 — sdílená hlasitost Apple TV/HomePod, ověřeno20:57UTC

- Zdroj199e3f40256caa0c2db740b45100e12e8c91deae; CI41348956150 a41348949775 success. `shared-volume-apply` verified, plán `shared-volume-prepare` active_verified, záloha8eba6f27. HomePod runtime1.1.2/configured, sdílený zdroj media_player.obyvaci_pokoj_obyvaci_pokoj;10/10 souborů/recovery/config přesně odpovídá CAS balíku. Důkaz: docs/evidence/2026-11-01-shared-homepod-volume.json.
- Opraveno doložené přeskočení odpovědi při idle RAOPvolume0: pouze vlastní stále shodná pozastavená TV relace smí použít její čerstvou sdílenou hlasitost. Skutečná nula/explicitní mute zůstávají tiché; přeskočený zvuk se již nevykazuje jako dokončené přehrání.60HomePod,154identity,20diagnostics,244addon(20skip) testů pass; nezávislé review bez zbývajících P1/P2.
- NOVÉ PŘESNÉ POZOROVÁNÍ VLASTNÍKA: v tichu TV Jarvis procitne, při hlasité TV nikoli; po otázce přestává brát odpověď. Tyto dvě závady NEJSOU potvrzené jako opravené hlasitostí. Neměnit znovu naslepo wakecutoff. Firmware zůstává.8/cbdb20ba, micmuteoff, Jarvis/no_wake_word. Nahrávání po restartu neaktivní.
- Další cílený krok: hlasová diagnostika1.1.2 s omezenými top-level fakty jediné privátní firmware konfigurace a příznakem otazníku odpovědi odděleným od continue_conversation. Bez výpisu YAML, lambd, URL, nahrávek nebo soukromých modelů.28diagnostic testů pass, review vyřešilo symlink parent/FIFO/duplicitní YAML klíče. Nasazení této diagnostiky teprve následuje; samo nemění akustické chování. Plán docs/superpowers/plans/2026-11-01-tv-wake-and-followup.md.
- Pro další povinnou zálohu dle dříve schválené retence3+protected smazán pouze starý nechráněný31d932a5, CASjob diag-clean-31d932a5 verified; volno2.5GiB. Poslední3 a chráněná záloha zachovány.


## Local speaker conversation and ordinary-speech interruption — implementation 1.11.2026

Owner approved applying the Voice PE own-speaker route; Apple TV/HomePod remain television output. Native Core2026.6.4 adapter retains HA-owned local microphone streaming throughout generation and native independent announcements. Completed utterances use the existing STT, context-bound speaker coordinator, conversation agent, memory and TTS. No new provider/firmware or continuous cloud stream. Quiet light actions remain silent and full-room grammar includes observed child-room diminutives. Cancellation invalidates old answers; mute/EOS/missing input close capture and owned output. User volume/mute remain authoritative.

Disable the legacy jarvis_homepod_output YAML domain when enabling jarvis_local_duplex to prevent competing routing and startup volume priming; retain its pure TVSession library. Bounded dialogue240s/24turns, utterance30s. Admin probe checks native VAD/WAV without opening microphone; separate fixed output_test verifies native announcement state. Echo gate supplements XMOS AEC but is not television source authentication. Real household overlap/interruption and noisy-room activation are acceptance checks, never inferred from synthetic tests. Plan/spec: docs/superpowers/plans/2026-11-01-local-duplex.md and corresponding specs file. Deployment receipt follows after activation.

Previous diagnostic-only source8794d10107c8725cc9bd52dfab516c35e0b9afa9 was backed-up and activated21:06UTC (tv-followup-diag-apply verified,9/9exact,backup0528c8e3,CI41349730816/41349724633success). A real question run continued and the next native follow-up captured a reply2.187s after the actual output-finished event. That is evidence of one follow-up, not arbitrary-speech interruption or noisy-room acceptance. Held TTS_END retains generation timestamp; use controller/router event time for playback duration. No wake cutoff change.

Fresh whole-change review identified and fixed startup short-speech clipping, cancellation timeout output ownership, validation-error native shutdown and indirect HA target ownership.55duplex/63companion/60HomePod/28diagnostics/154identity tests pass;244addon pass(20skip);manifest/syntax/diff pass. Deployment remains pending below this entry; household acoustic acceptance unverified.

## Local native activation and microVAD warmup correction — 1.11.2026 22:05UTC

Source662f05669544b2be754a5babefef52ec04a7843b passed PR/push CI41354628522/41354622380 including publication. local-duplex-apply-20261101 verified22:02:49UTC,backup6661d4a5,22/22files exact,adapter active/Core2026.6.4/muteoff/localplayeridle. The first live no-mic probe exposed native pymicro-vad1.0.1’s-1 sentinel: its pinned sourcef3857782b2d147634ea591c2fb12a01ca5a74cdc collects74features before a probability. Do not interpret this as ready or a probability. Version1.0.1 now primes only native VAD with synthetic silence (not microphone samples), validates finite0..1 readiness and accepts only the known-1 sentinel as no speech.57duplex tests pass with observed regressions RED→GREEN;manifest/diff passed. Corrected activation/probe receipt follows; household interruption/noisy-room acceptance still unverified.

## Local speaker dialogue active — 1.11.2026 22:11UTC

Corrected source d148c0ee36c202cf3b05cdd6dafef00a6fe779a8; CI41355331959/41355326073 success including laboratory publication. local-duplex-v101-apply verified/active_verified22:10:07UTC,backupd6c86bfa. Final22/22source/recovery/config/metadata files exact. Runtime1.0.1/configured, adapteractive, deployed source_revision9eeed5064e61a2a51c812ddf29853d69de64bb975f5c24b5e2e554b781aa3ee4. Real no-microphone probe passed:77synthetic-silence VAD warmup frames, finite probability0.00439656525850296, WAV reference3.156125s. First native output_test (runtime1.0.0; playback path unchanged by VAD fix) observed1start/1completion, no mic opened, audibility unconfirmed. PrimaryJarvis/secondaryno_wake_word, muteoff, speakeridle/currentvolume1 preserved, satelliteidle/LEDoff. Lease release verified.

No actual duplex conversation observed yet(sessions0); ordinary-speech interruption, echo/noisy-TV rejection and short Czech acoustic reply remain owner acceptance checks. Owner repeated no streaming: no idle/continuous cloud audio enabled; only completed utterances use existing STT. No firmware/Core/OS upgrade or raw microphone recording. Native timer announcement ownership remains a documented interface limitation. For mandatory backups only old unprotecteda7af12c8 and60a8e25e were deleted with fresh CAS under accepted preserve-newest-three/protected policy; both jobsverified. Private receipt jarvis_workspace/local_duplex/deployment-receipt.json; public docs/evidence/2026-11-01-local-duplex-active.json. Next: one actual story→interrupting question without another wake; then short follow-up and loud-TV wake separately.


## Software audio recovery and voice rule audit — 1.11.2026

Source740713d605047bce2693b1af20f6364436df66ee, local duplex1.0.2: software-audio-v102-apply active_verified22:44:35UTC, backupbdcfe0af; native PCM peak−6.37dBFS/RMS−21.61dBFS, VAD ready after77synthetic frames. Exact native software restart observed disconnect/reconnect and fresh state before preserving volume1/unmuted. Post-restart native playback completed; owner still hears neither story nor embedded wake tone. Voice-scoped fixed story probe returned187speech characters, no microphone or sound/actions. These facts do not prove audible output or noisy-room usability. Owner explicitly rejects physical disconnection; continue software investigation.

Rule conflict confirmed: two enabled legacy automations watched terminal playback and set HomePod volume to0.1/0.45; their guards referenced the absent legacy output sensor. Source24c3ff4cf816e74feb5ba0da7e20231863244320, voice-rules-disable-apply active_verified22:57:30UTC; exact YAML readback and both automation entities off; unrelated solar heating stays on. Only initial_state false added, definitions preserved, no Core restart. Audit covered root configuration/includes, automations, empty scripts/scenes, missing groups and active local/disabled legacy output routing. This fixes competing HomePod volume control; it does not establish the cause of inaudible local output.

Next bounded operator audio_audit uses the existing exact native player connection, no microphone: native config dump plus fixed output playback, strict enum/numeric-only audio facts, then restores native logging to HA's current expected level. No raw logs, credentials, source URLs or speech stored. Runtime1.0.3 activation pending; no firmware or wake sensitivity change.


## Conversation starvation and complete speech resources — repair1.0.4 pending

The1.0.3 native audit completed133messages/26audio/0knownaudioerrors with logging restored; validPCM and native completion did not establish audible sound. Independently generic HomePodTTS failed miniaudio.DecodeError in pyatv InternetSource.open. Static media comparison1 was skipped because dialogue was active: owner no-sound result is not failed-output evidence. Comparison2 executed while confirmed idle23:21:24–34UTC: HomePod file-based playback returned normally3.5s, then native announcement dispatched, no new decoder error; acoustic outcome unknown. Temporary automation removed and exact original rules restored by static-audio-cleanup-after-idle-apply, legacy2off/heatingon.

Real240s dialogue01M6CP8CSDHZBY4ZEH4543EGXF showed29interruptions/0completed,1outputstart/0end; response68chars and questiontrue. Preparing output was cancelled by raw speech onsets. Version1.0.4 gates acoustic cancellation on actual owned PLAYING; completed input during preparation queues latest1 for at most5s and cannot execute after a newer correction. Spoken answers retain8s followup even if providerFalse; silent light actions still finish without speech. Truncated candidates cannot cancel output. Capture/mute/limits and identity grants remain intact.

Same synthesized16kPCM/Nova is normalized to a complete private temporaryWAV in configured local media, avoiding the speech-result URL as playback source; native format negotiation preserved. Max4files/600s stale; directory/file0700/0600 and no-follow dirfd; serialized executor operations; success/failure/cancel/stale-owner/creation-cancel release. No microphone recording or firmware/threshold change.86duplex/63companion/62HomePodtests pass; manifest/diffpass. Fresh review2Important fixed in one RED→GREEN pass: discard older pending behind newer direct input; serialize cap/prune/create/release. Source publication/activation receipt follows. No historical verified current-device full rollback baseline found; do not substitute old assistant configured claims for acoustic success.

## HomePod speech is the required output — repair1.1.0 ready, 2.11.2026

Owner correction supersedes the local-speaker routing above: HomePod must speak; Voice PE provides microphone/wake. Version1.0.4 sourcea918bf1b428242fdc307b543e7cef8b1fc55a1dd activated23:36:40UTC, jobconversation-audio-v104-apply active_verified, backup7f9f9dc2,13/13exact and both CI success. VAD/canonicalWAV and native playback completion passed, but owner still heard no sound. Stop audible native-speaker tests and firmware-output investigation. Retain its response-preparation/followup/resource fixes.

Version1.1.0 routes only to the existing exact HomePod native RAOP interface and complete local media WAV; no Voice PE spoken fallback. Existing explicit owner startup45 policy is applied once after a known-ready connection; later current volume/zero/mute is preserved. Native packet position plus latency determines actual playback scheduling. Only the owned file task is cancelled/drained; WAV remains until native teardown ends. The disabled legacy output domain stays disabled; its pure TVSession library pauses/resumes owned TV and abandons ownership on foreign HomePod control. No generic stop, credentials, new provider, Core/firmware upgrade or microphone recording.

Fresh review:0Critical/3Important/0Minor, fixed once with RED→GREEN evidence: pre-write disconnected native interface retries initialization; disowned/cancelled playback drains without repeated cancellation and retains its WAV through timeout; TV abandonment invalidates an in-flight acquisition.97duplex/64HomePod tests and manifest/diff pass. Publication/activation and HomePod acoustic acceptance are pending. Fixed output_test now closes/drains active dialogue and speaks only “Zkouška hlasu na HomePodu.” Never infer audibility, conversational interruption or noisy-TV wake from software completion.

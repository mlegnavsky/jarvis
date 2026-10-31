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

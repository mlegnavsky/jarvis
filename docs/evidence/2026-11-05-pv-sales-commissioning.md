# PV sales commissioning — 5 November 2026

## Active release and observed results

Published native release0.4.0 is running on Green. Source API commit ac9ee3b42159a3104adfbef67526875291d1037f, tree f51c3dc2695f0192ed775d33bf17da5c3a43f1f9 (identical to local599e223).

The first500W/3minute PV-only test began13:33:27 Europe/Prague. Export436–503W was measured while battery continued charging approximately0.8kW, SOC99%, inverter42°C and battery20°C. At13:35:48 export931W triggered the unchanged requested+300W guard. Stop completed13:35:56; subsequent grid12W import. PV commissioning is **not passed** and automatic remains **off/inhibited**. The excursion is not yet attributed to firmware, scaling or transient regulation.

Archive1.1.0 acknowledged measurements and all16initial control events. The source timestamp is retained separately from capture time. Existing historical data is preserved; old missing fields are not fabricated.

The backed-up apply job sales-pv-apply-20261105 ended unknown during the Core restart. Do not reapply that intent with a new key. Activation was independently reconciled from exact file revisions, runtime0.4.0, native entities and physical measured export/stop. Backup e22c7121.

## Release0.4.1 diagnostic change

Installed Solarman number/entity source proves that successful Modbus write is followed by an optimistic HA state update, without an immediate device read. The seller now reads native holding registers143(MaxSellPower),142(WorkMode),145(SolarSell) back through the installed Solarman device API. It refuses to enable export if the native cap differs. This is scoped to this verified deye_p3 installation and refuses ambiguous Solarman entries.

The unchanged export guard records its exact trigger, grid/PV/battery measurements, requested power and source timestamp. Five-second active measurements are journaled. Original abnormal stop reason/context survives retry and restart; a failed stop can never later promote commissioning because the deadline elapsed.

An admin-owned bounded command inbox at jarvis_workspace/sales-command.json permits only start,stop,automatic through existing guarded seller functions. Required JSON keys: id,issued_at,expires_at,action,data. Times are UTCepoch seconds, lifetime at most120s. A durable SQLite unique-ID claim precedes action; old timestamps and reused IDs are ignored. Start/enable rechecks expiry inside the control lock. Inbox failure cannot skip the export guard. This provides remote administration without changing/redacting household allowlists or exposing arbitrary services.

Example shape (generate fresh timestamps):
```json
{"id":"unique-owner-request","issued_at":0,"expires_at":60,"action":"start","data":{"mode":"pv","power_w":500,"duration_minutes":3}}
```
The example timestamps are deliberately expired. Claimed/confirmed refers to command handling; actual running still requires fresh measured export.

## Limits and incomplete activation

Contractual whole-grid reserved export9500W; operating upper bound9300W. Existing battery charge/discharge175A is preserved. Reserve for sale60%, native operational buffer62%. Net sale price is OTE15minute price converted using provided CNB rate less0.30CZK/kWh; purchase stays ČEZ5CZK/kWh. No grid charging for resale is added.

Connected time/price supervision requires functioning HA and inverter communication. PV export can continue under the native cap during a controller outage. This is disclosed in the view. Battery sale remains blocked until native timed expiry and reserve behavior are physically verified. Full forecast-driven battery scheduling and settlement are not yet complete.

Validation0.4.1:49targeted sales tests pass. Full suite is run separately; known unrelated test_official_sdk_can_initialize_list_and_call cannot import ClientSession from the installed MCP SDK. Do not report the full suite green.

## Second physical test and UI correction

Release0.4.1 physically repeated500W/3min at13:58:06local. Native143=500 and145=1 were independently read. Fresh exports typically416–547W, battery continued charging~500W, SOC99%. Deadline shutdown started14:01:11, native143=0/142=2/145=0 readback confirmed, fresh grid19W import by14:01:37. Stop proof recorded14:01:28, reason deadline, sustained=true, stop_verified=true, nofailures. PV commissioning passed; automatic remained deliberately off. The coarse energy counter crossing5.1→5.2kWh does not imply this0.5kWtest sold0.1kWh. Original931Wexcursion remains a captured abnormal event; no threshold was relaxed.

Live HA logs exposed a UI listener running in an executor and calling event-loop-only async_write_ha_state. Release0.4.2 marks all three platform listeners with HAcallback; a real dispatch-semantics test reproduces the old failure and passes the corrected controls. Initial automatic PV output is conservatively capped3000W; contractual9500W and absolute operating upper9300W stay distinct. Native mode/enable baseline is independently checked before enabling. Expiring commands are checked again after the two native reads. Battery automation remains gated.52sales tests pass.

## Live daily CZK and normal PV pauses — release0.4.3

Owner requested daily purchase/sale CZK updated with the inverter, replacing old
placeholder income on Energie and flow text under the Domov house (both desktop
and mobile layouts). Added durable finance ledger, five-second power sampling,
dated quarter-price integration net of0.30CZK/kWh, purchase5CZK/kWh with daily
counter anchors, private archive backfill with overlap/reconciliation and explicit
partial/unknown data. Native counter/source-change timestamps and midnight reset
are retained; a lone noon sample cannot appear as a complete zero day. FX date and
provisional status remain visible. Original art/other views are preserved by a
scoped generator; full YAML roundtrip checked.

The3000W PV test observed export, then a temporary lack of surplus incorrectly
triggered no_export after60s. Release0.4.3 waits for/resumes actual PV surplus
without changing power/price/fault guards or deadlines. Normal market/reserve
pauses keep owner's automatic mode. Automatic recovery first verifies safe stop
and then reevaluates; interrupted manual recovery and abnormal stops stay latched.
Automatic PV returns to charging below98%SOC. Battery automatic sale remains gated.

Owner also explicitly requested native zero-import bias0W, verified initially20W
at register104. Existing voice/control allowlist preserved by the unredacted
permission_map and extended by this one entity through supported admin options;
no credentials or generic services were broadened. Scripts/automations/source
restore lists audited for writers of20W. Start preflight independently reads104=0.

## Actual0.4.3activation and two follow-ups

Native0.4.3/finance1.0.0 is running at14:43local. Daily purchase24.50CZK is calculated from4.9kWh and subsequent measured power; datedCNB05.11.2026rate24.29 is available. Archive backfill remains unconfirmed, so0CZKshownwhileloadingisnotafinaltestrevenueclaim.0.4.4 boundsarchivequerywindowsto15minandretainsactualerrorinformationforverification.

Independentregister104read aftergenericHA0write returned20; a second0writeand1Wprobealso returned20, despiteoptimisticHAstates0/1. Therefore native0WtargetisNOTproven.0.4.3incorrectlyblockedotherwise-safePVsaleonthisnon-safetycondition.0.4.4recordsactualnativebiasseparatelyfromdesired0WwithoutblockingPVsale; strictmode/enable/exportcapreadbacksremainmandatory. Grid-chargeoffwasconfirmedviaHA;nativephysicalflowcurrentlydoesnotshowgridcharging. Usermustnotbetold0Wisphysicallyhelduntilproven.

## Actual finance reconciliation15:31local, and native commissioning0.4.6

Release0.4.5 source84572306d6b8d75b00ad06ba46c647cde5954f02 activated
verified14:30:32UTC, backups4bc59b7a. Archive1.2.2 normalizes historical
PHP empty-map arrays while retaining events. The diagnosed list.get failure is
resolved: finance backfill loaded5247points, history_error empty, datedCNB24.29
05.11.2026, live daily estimate24.8467CZK purchase /0.39473CZK sale with
0.075327kWh integrated export. These are estimates, not settlement. Recorded gaps
5145.9s remain gaps; no interpolation across>30s. New UI supports partial state.
The native diagnostic attempted too early before Solarman runtime_data existed;
0.4.6 retries only after fresh healthy sensor data, with bounded reads.

PV automatic trial15:17local was stopped by unchanged battery_discharge guard:
grid351Wexport, battery298Wdischarge, PV305W, SOC98. Native stop verified. Thus
current SolarSell/ZeroCT alone is not proved to exclude transient battery supply.
Do not describe full PV automatic as accepted or disable its guard. Another UI
configure enabled automatic~15:34; owner test preparatory Stop15:38 returned
verified idle/off before0.4.6 apply. Both actual changes remain in the journal.

0.4.6 adds ONLY fixed low-power native TOU feasibility commissioning. Future5min
slot Sell32,500W cap, SOC95, discharge current min20A/prior/BMS; keep global
ZeroCT/SolarSellOFF and all ordinary house slots' uniform SOC/power. Requires
LV type0500/lithium/Capacity, gridchargeOFF, all prior charging flags0, Week255,
clock delta<=5s, healthy fresh positive-price readings. Native raw FC16 writes
are immediately read back via FC03. No use of register340 as PV production cap.
All original register values persist before writes; cleanup independent commands
clear everySellbit even if cap write fails, fresh post-stop measurement required
before ordinary schedule/current restoration. Restart recovers rather than repeats.
Readback of clock and following slot occurs across the boundary before any stop
write. Command expiry and health are rechecked after slow audit just before arming.
Charging preflight race reproduced and fixed before publication.

Production battery_verified staysFALSE: daily recurrence and next-day offline
behavior are not resolved by this feasibility test. No autonomous expiry claim
or live battery test outcome exists yet. Sourcebcfe6ad9bfdb2d2768390234ef03eca6e69aef03
(tree de998440c3c836f8797d3557170b84e5bc599073), local7f44f22. Prepare
sales-native-window-prepare-20261105 verified; apply newly queued. Both review
findings have watched failing regression tests and focused clean re-review.
82targeted and346full tests PASS with repository-pinned test dependencies in
isolated environment; real PHP archive/WebDAV tests included (no skips). Earlier
base-runtime MCP1.29 import error and newly-unskipped missing aiowebdav2 were
environment mismatches; no production SDK/source changes were made to hide them.

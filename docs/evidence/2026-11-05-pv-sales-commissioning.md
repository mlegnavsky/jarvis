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

## Actual administrative bootstrap and native window armed16:26local

New administration writes stopped before reservation at exactly1000 historical
jobs. Jarvis3.12.5 was installed through the independentUpdater, job
5259b31de04f4cbe8a7607c740852519 verified/backupf3854248. First read, before any
new mutation, returnedtotal1000/limit10000/remaining9000. The exact cause is thus
confirmed; receipts and deduplication were retained. Previously unperformed
cleanup/UI intents were reconciled and then completed under their original keys.

Original inverter clock was~94s behind. Supported datetime.set_value was used in
bounded one-shot HA automations; direct FC03 clock readback was logged, without
exposing credentials. Final native snapshot16:24:10 shows16:24:08, delta-2.35s.
All temporary clock/read-only diagnostic rules were removed and the original
three-rule automations.yaml content restored byte-for-byte; originalSHA256
851e4d072ed07f897f2e809b7f7e5faca8811c22d556ce15bf37a94a17ef5fcb.
The installed Solarman read_holding_registers service uses address-or-register
and mishandles0; do not repeat that unsupported diagnostic request. Native internal
execute(3,0) works. Raw98=1/111=1/130=0 were confirmed16:13:45. The installed
profile maps BOTH5 and0x0500 to LV; the initial exact1280-only preflight falsely
rejected legacy5. Release0.4.7 accepts only those two documented profile values,
keeping all other commissioning guards. Watched failing legacy test passes.

Release0.4.7 sourcee4c482bea457a09f9e96f21e780673c6301a5280/locald8ad0fd,
treebd3b2d4132b32e7f67de995a58991209aff70c99, appliedverified15:24:15UTC via
sales-native-lv-apply-20261105/backupe0debf77. Four exact file readbacks and both
runtime0.4.7 checks passed. Automatic remainsOFF.

NativeWindow1793892335790385341 is now ARMED, NOT passed:16:30–16:35local,
500W globalcap/current20A/nativeSOC95, original ordinary house slots30%/12000W,
SolarSellOFF/ZeroCT. Every write was independently read back, arm register173=32
last at15:25:41UTC. At16:26:21 SOC98%, PV21W, grid8Wimport, battery96W supplying
house, inverter38.3C/battery18C. No claimed battery sale yet; must measure at
start and prove native boundary before any connected stop write. Never restart
while this durable native transaction is active. Production battery remainsgated;
daily recurrence and calibrated forecast planning remain OPEN.

Mobile Spoty now has a live verification card and a direct red native-test Stop;
final file revisioncd625068ba87be7f2b0789ebae46c78893099dfd1323de55a0a8739f899b21b7.
The reusable generator renders armed as waiting rather than claiming measured
export; real Jinja regression and Stop action tests pass.351full local tests
passed with pinned dependencies and realPHP, no skips. No visual mobile-browser
acceptance or full-production claim follows from these tests alone.

## First native-window physical result16:35local
NativeWindow1793892335790385341 did NOT prove export: SolarSellOFF/ZeroCT/Sell32
slot500W produced only ordinary battery-to-house~100–122W, PV~8–21W and small
grid import. No positive battery-sale claim. At16:34:15 Solarman logged a timeout;
measurement freshness was lost during the test. Cleanup eventually completed
16:35:34local with all native settings/current175A restored, MaxSell9300,
SolarSellOFF and no active transaction. Old proof reason saysretry because the
initial stop reason was not retained; this diagnostic defect is fixed in0.4.8.
No native clock-expiry acceptance follows from this unsuccessful test.

0.4.8 adds a second FIXED commissioning variant, not production: optionally
SolarSellON only once the test clock window is open, with all six native SOC
floors95% from preparation until restoration. This bounds battery withdrawal
if communication fails across the boundary. Cap500W/currentmin20A/prior/BMS,
5minute same-day window and all price/health/native acknowledgement guards stay.
Positive enable rechecks health/time after audit and is refused afterend-10s.
Expiry proof requires actual prior battery export including a fresh sample in
last15s before end; old or never-observed export is not a clock proof. Regressions
cover both false-positive cases. Stop retains first reason/context across retry.
A separate serialized5s report callback keeps mobile stopping/health state live
while an actuator acknowledgement is pending. No permanent trading gate is lifted.

Own temporary backupa12886b5 was deletedverified after fresh metadata read under
prior local-cleanup authorization; newer/protected and all remote backups retained.

## 17:09local — version0.4.8 active, second window armed
Source573b5963fcc29da0c49d4802132f36df5f824169 activatedverified16:01:26UTC,
backup58a4546f, Core2026.6.4 unchanged. Independent5sreport works while native
control awaits device I/O. First SolarSellON intent failed BEFORE writing because
clock tolerance did not pass; no test started under that intent. Read-only
one-shot native diagnostic17:06:20 found actual17:06:18 (~2.6s behind), raw
current109=175 and allSOC166..171=30. Diagnostic removed, original three household
rules restored byte-for-byte and reloaded.

Correction to the earlier restoration statement: immediate FC03 acknowledgements
at16:35 did not prove persistence. At17:01 fresh native snapshot still showed
slot2SOC95 and HA current20A. Standard supported number services restored slot2
to30 and current175, then the17:06 direct physical read confirmed both. Do not
claim an enduring cleanup based solely on an immediate write/read acknowledgement.

Second physical intent owner-native-solar-window-after-clock-proof-20261105
armedNativeWindow1793894870144619394 for17:10–17:15local:500W,20AorlowerBMS,
all six SOC95, SolarSell enabled only after actual start. At17:09 still waiting,
not yet export proof. Production battery gate staysFALSE.

Independent whole-branch review found a normal SaleController race after awaited
audit and an unvalidated purchase UI fallback. Source0.4.9 fixes both with
observed RED→GREEN tests;361full tests pass before the version-only bump. This
source fix is not yet active and must be deployed before another normal PV start.
Partial cash cards were updatedverified16:07UTC, parentrevision
d5bef4fb9d436af39d1b0ba6312036ea661c49167e21510bcbcab2d1588c2164.
Known sale amount is explicitly labelled as an incomplete documented part, not
a fabricated complete daily total. Raw purchase fallback is removed.

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

## 17:36local — clock sampling defect reproduced and corrected in0.5.1
0.5.0activatedverified17:28:30local, backup3e805320. Fresh native snapshot
confirmed residualSOC95at slots1/3/6; supported number services restored those
to30 and maxdischarge175. Whole nativeprogram17:29:44 confirmedall6SOC30,
ordinarytimes,allflags0. Both native0.5.0pilotintents were blocked BEFORE any
write by strictclockcheck; no failedclockintent is an actualexporttrial.
Readclock-first followed by other queuedModbusrequests adds theirduration to
clockerror. Reproduced in adapter regression:10sconfigurationdelay made an
accurateclock look10.6s old.0.5.1 readsclockLAST in both diagnostic and trial
snapshots, preservingthe5stolerance and alldeadline/health checks.41targeted
testsPASS after observedRED→GREEN. Clock synchronization attempted through a
boundedone-shot; subsequent directread timedout, so no claimofconfirmedclock
sync underthatintent. Temporary rulewasremoved and originalthree rulesrestored
andreloaded. AutoOFF, productionFALSE; nextpilotmustwaitfor0.5.1runtime/fresh
actualclockconfirmation. Calibratedhouseforecast/productionoutagepolicy remainopen.

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

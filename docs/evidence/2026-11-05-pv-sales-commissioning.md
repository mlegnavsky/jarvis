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

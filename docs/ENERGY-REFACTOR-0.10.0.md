# Energy control0.10.0 — prepared candidate

Status: source prepared and tested; **not installed**. Review branch: `refactor/ha-control-cleanup-20261106`. Baseline: `060501cd69451f9047cb0baac182dc6c463a591c` (energy0.9.3). This document is source evidence, not a live deployment receipt.

## Result and ownership

Production decisions now live in pure `production_policy.py`, while the HA adapter handles serialization, persistence and device acknowledgements. Controllers enforce the permitted writes again at their I/O boundary. New ordinary battery operations use HA control, including manually requested battery sales; they do not create native SOC/time programs. Explicit commissioning, grid charging, clock maintenance and safe cleanup of old saved transactions remain separate maintenance paths. They are never automatically initiated by production flags.

| Priority | Trigger | Operation |
|---|---|---|
| Protection | Invalid/stale measurements, BMS/electrical guard, native profile mismatch or conflicting owner edit | Stop/block; retain cause and independently confirm cleanup |
| Scheduled battery | Current positive quote, inside selected block, SOC above configured sale floor (default60%), no completed plan for that day | HA export bounded by configured cap (default9300W) and existing BMS/current/voltage protections |
| PV surplus | SOC at least97% by default, positive quote, actual PV greater than known house load plus30W | Permit surplus; stop on house support, reserve or other existing guards |
| Small export | No higher-priority operation, known current quote, previously verified mode, SOC at least31% by default | Request20W continuously; stop at HA home floor (default30%) |
| Wait | Other conditions | No new export request |

Native reserve remains30% in every slot, independent of editable HA home thresholds. Production reads and validates it rather than silently correcting it. Each new start checks a fresh native profile, even after earlier admission. A native mismatch blocks operation and exposes expected/actual values.

The20W value is a requested target, not a guarantee of exact physical flow. Negative known prices still allow the owner's small-export policy; missing prices do not. Ordinary HA control depends on a running HA and connection: if these fail, the business stop at60% or the scheduled end cannot be guaranteed by software. The inverter's unchanged native protection and BMS remain the physical fallback. No new physical guarantee is inferred from offline tests.

## Removed and retained code

Removed duplicate legacy battery admission from `SaleController`, the unused alternative price/reserve policy, automatic commissioning admission/coordinator, automatic SOC normalization and generic-error recovery inference. The former candidate module is removed; a small `commissioning_completion.py` retains completion for explicitly requested maintenance tests.

Kept old before-images, ownership conflict checks, pending writes and cleanup of saved transactions. Removing these would strand an installation interrupted during an older version's native write. The legacy YAML commissioning option remains accepted but no longer starts tests automatically.

Repository dependency review covered the energy adapter/controllers, archive/finance/planning, spot views/settings and their Jarvis gateway/maintenance interfaces. Voice, wake/speaker, companion, firmware, heating, archive collection, weather, OAuth and updater behavior is unchanged. Tests across the repository verify these shared contracts; this release does not claim a rewrite of unrelated subsystems.

## Device-write inventory

| Route | Device writes | Production status |
|---|---|---|
| PV/bias `SaleController` new record | Export cap, export enable, working mode | Allowed; program SOC/time/current writes rejected |
| Battery `BatterySaleController` HA record | Registers142/143/145 only | Allowed; native schedule/current writes rejected |
| `engine.py` grid-charge service | Charge control and owned restore | Explicit manual charging only; mutual exclusion retained |
| `native_window.py` / native battery commission | Bounded native test schedule, SOC/current and cleanup | Explicit maintenance only; automatic admission removed |
| `native_clock.py` / zero target | Clock / register104 | Explicit maintenance only |
| Saved legacy records | Only owned before-image restoration with conflict checks | Recovery only; retained for safe upgrade |

## History and diagnostics

No event or command tables are dropped, rewritten or truncated. Existing storage keys, unknown settings fields, before-images, IDs and archive replay cursor survive. New completion state records the selected business day and proof ID, so reaching the sale floor cannot restart a large sale on a small SOC rebound. Older selected blocks acquire a deterministic local day before operation. Historical rate settings remain intact.

The authenticated admin history endpoint retains its old no-query response and adds bounded ascending cursor paging with time, kind and sale correlation filters. Maximum page1000, parameterized SQL; secret values are redacted on export. History read failure returns503 without deleting data. Diagnostics schema1 distinguishes measured export from a requested command, data loss, native mismatch, safety stop and pending recovery. It includes measurement ages, exact health evidence, stop/cleanup/conflicts and archive/report errors. Health transitions are journaled once per changed cause rather than every polling cycle.

Recovery requires a durable pending intent, the same confirmed stop proof, owner intent still ON, exact transient-only measurement evidence and at least30 continuous seconds of fresh health. A later stop, manual/maintenance command, actual fault or owner OFF invalidates that pending intent. Restart never reconstructs permission to resume from an old historical stop.

## Verification

- Full Python discovery:746 tests run;726 passed,20 pre-existing PHP-dependent tests skipped because PHP is unavailable. No new skips.
-11 Node unit/DOM suites passed, including market charts, controls, settings, translated causes and passive UI behavior.
- Release version, manifest, permission and Python syntax checks passed; whitespace checks passed.
- Old-schema journal reopen, stable paging IDs, old command deduplication, partial legacy transaction recovery, report write failure and exact health transitions are covered.
- Independent safety review found3 defects; all reproduced, fixed and regression tested. Review follow-up verified maintenance cancellation/window-stop ordering. No unresolved P1/P2 findings in reviewed changes.
- Chromium screenshot acceptance was attempted and blocked by environment socket/ptrace EPERM. Desktop/mobile visual acceptance and real-device0.10.0 operation are **not yet verified**.

## Later deployment and rollback

Only after the owner's installation command:

1. Read current production Git HEAD, live source/version, pending transactions and latest work manifest; reconcile concurrent edits rather than overwrite them. If the active baseline changed, review the candidate against that baseline first.
2. Check space and create a protected backup of live source, HA storage and private energy database/archive. Do not delete older history or backups to install this candidate. Record backup ID and exact file revisions privately.
3. Stop/quiesce export through the current controller, confirm safe native mode and finish any legacy pending cleanup. This is a maintenance step requiring that installation command, not preparation work.
4. Stage the complete `custom_components/jarvis_spot_control` package from the pinned candidate and verify all SHA256 values in `docs/releases/energy-0.10.0-candidate.json`. Publish the listed frontend files. Regenerate Spoty config/view only from the current live view so custom house/dashboard content survives. Merge the owned recovery automation by ID with CAS if installed; never replace all user automations.
5. Switch source consistently, retaining rollback files. The deleted old `autonomous_verification.py` is not imported by0.10.0; remove only that known owned file after activation, never recursively delete the component. Keep legacy native cleanup modules.
6. Activate Python through the supported maintenance path; newly loaded integration code may require a controlled HA restart. Verify running0.10.0, fresh telemetry, original native30%, service/API contracts, old history IDs/counts and journal/archive progress. Perform the deferred mobile/desktop visual checks.
7. Observe actual requested/confirmed/stopped operations and guards; accepted service requests alone are not success. Record the resulting live receipt separately. No safety bypass or automatic commissioning is part of installation.

Rollback source to the exact backed-up version and restore owned frontend/automation changes with current revision checks; leave the permanent journal/archive in place. Preserve the latest compatible settings/transaction state, including new completion evidence; do not roll the database back and lose events generated after backup. If any transaction is pending, reconcile its native state and use its controller cleanup before another start. HA Core remains2026.6.4.

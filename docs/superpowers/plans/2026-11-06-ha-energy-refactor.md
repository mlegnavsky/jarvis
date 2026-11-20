# HA energy control refactoring implementation plan

Goal: prepare an installable, reviewed refactor without installing or modifying the running household.

Architecture: keep HA entities, service names, storage keys, journal IDs and archive interfaces compatible. Extract pure operational decisions, read-only profile validation and structured diagnostics from the HA adapter. Ordinary operation writes only export controls; legacy native test/recovery code is explicitly isolated and never runs automatically.

Approved requirements: fixed native protections; HA thresholds PV97/sale60/home30/resume31; scheduled sale first, actual surplus second, continuous20W fallback; completed block cannot restart; fresh healthy telemetry and electrical guards win; no installation until owner's explicit command.

## Tasks

- [x] 1. Baseline and inventory of application subsystems; preserve unrelated voice, gateway and archive behavior. Work on a separate branch from current production HEAD.
- [x] 2. Test and extract production_policy.py: deterministic decisions, completed-block identity, read-only home profile checks and no native five-minute startup delay.
- [x] 3. Test and refactor controllers/adapter: no routine SOC/program/current writes, immediate HA-controlled battery plans, continuous bias renewal, durable completed-plan state, unchanged emergency cleanup of legacy saved transactions.
- [x] 4. Test and add structured diagnostics plus filtered cursor journal retrieval: precise stage/reason/evidence, timestamps/age, expected/actual, correlation, read-only authenticated API and existing schema/data preserved.
- [x] 5. Remove redundant legacy production branches, correct UI text and document compatibility/migration/rollback. Retain explicit legacy recovery until no old transaction can require it.
- [x] 6. Run Python and frontend suites, archive/history reopen tests, release checks, inspect whole diff and independent review. Prepare manifest with hashes, base/source commits and explicit not-installed state. Publish only the separate review branch.

## Review focus

- Restart with a partially written old transaction: cleanup remains possible and ownership conflicts are never overwritten.
- Stale/invalid telemetry or missing price: export must stop; zero solar is not missing measurement.
- SOC60 rebounds or owner toggles automation: completed business block remains completed through restart.
- Broken archive or full disk: existing history remains, diagnostics report the failure, no proof is fabricated.
- History pagination/authentication: bounded requests, stable cursors, no secret exposure and no destructive schema changes.

## Execution evidence

Base060501cd69451f9047cb0baac182dc6c463a591c (active0.9.3). Scope decision: complete repository dependency review, focused restructuring of energy application; unrelated voice/gateway subsystems kept compatible. No live writes, restarts, backup deletions or installation in this work.

Implementation decisions: preserve existing explicit grid-charge and commissioning services as maintenance compatibility; do not auto-run them. Retain legacy transaction cleanup, because removing old before-images could prevent safe restoration. Refactor production paths and read-only diagnostics; unrelated voice/gateway/heating modules keep their current behavior. New code will ship only on the separate review branch; no live writes or installation. Native reserve30 is separate from editable HA home floor. Pure policy functions: choose_operation(...), complete_battery_plan(...), house_profile_issues(...). Journal.page() and protected history view retain the old no-query response. diagnostics.snapshot() adds a versioned, bounded read-only projection.

Verification: final full Python suite746 tests,726 passed/20 existing PHP-dependent skips;11 Node unit/DOM suites passed; release metadata/syntax/permissions check passed; git diff whitespace check passed. Independent reviewer reproduced3 defects, each fixed with red/green regression tests; final reviewer has no unresolved P1/P2 findings. Additional window-stop recovery ordering regression passed. Browser screenshot run attempted but Chromium is blocked by socket/ptrace EPERM in this environment; visual/live-device acceptance remains part of the later approved deployment. No claims of physical0.10.0 operation.

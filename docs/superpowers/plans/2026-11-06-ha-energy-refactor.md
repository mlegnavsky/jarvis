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

Base7eba6deae0faaa5ce5f32020da760c16369e1f1f. Scope decision: complete repository dependency review, focused restructuring of energy application; unrelated voice/gateway subsystems kept compatible. No live writes, restarts, backup deletions or installation in this work.

Prepared locally: production boundary, durable completion and original block identity, read-only profile, stable high-water history and authenticated diagnostics implemented. Independent review blockers fixed with regression coverage. No live test or deployment.

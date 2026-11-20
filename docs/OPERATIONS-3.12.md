# Direct operations 3.12.0

## Runtime contract

Admin adds storage (host disk GiB), exact backup metadata/revision, safe backup_delete, retention preview, deployment ownership, prepared bundles, explicit apply/rollback and bounded heating_settings. Same authenticated maintain-scope Jarvis route; no new network port or shell.

Backup deletion: explicit slug+metadata CAS; reject incomplete dates, protected backups and newest backup; then DELETE through supported Supervisor API and verify absence. The three approved backups were removed through this capability after updating;36c1e560 was removed through the already signed-in UI to bootstrap disk space. No other backup deletion was authorized or performed. Retention default preserves latest3 and protected backups, returns candidates only. Automatic purge is intentionally OFF: the owner approved four exact deletions, not unlimited future deletions.

Storage preflight: require reported free space>=2GiB before Admin backup operations. This is a minimum preflight, not a guarantee that every proposed backup will fit. A failed preparatory backup is reported as requested change not started; a backup may itself need reconciliation. Supervisor protections remain enabled.

Deployment lease: client generates a32hex deployment_token, submits deployment_acquire(owner,ttl_seconds,token). Token is not returned in public job/status responses. Every Admin mutation checks ownership; an unrelated chat without matching token fails before side effects. Release explicitly or let TTL expire. This coordinates Admin workflows; independent updater, manual HA UI and other external writers are outside the lock and still require operational coordination/CAS.

Prepared bundle: source_commit, exact core_version, activation none/automations_reload/core_restart, files [{path,content,expected_revision}], checks [{entity_id,state,version}]. Prepare validates syntax/revisions and records private before-images; preview returns file names/hashes/line counts and restart requirement, without exposing config text or credentials. Checks must have a real expectation. Source commit is declared by caller; content hashes bind exact file bytes. The bridge does not independently download/attest arbitrary Git commits.

Apply requires lease and plan revision. Validate current file revisions and Core compatibility; perform CAS writes, check each write and final readback; then activate and check Core plus configured runtime entities/versions. phases prepared/writing/file_written/activation_pending/active_verified/activation_failed are persisted. File_written never means runtime active. An unknown activation needs native state reconciliation; do not replay blindly. Core check_config validates actual installed configuration before restart.

Rollback is explicit, never an untested automatic device rollback. Precheck every file against the saved before-image/new content, restore written files only, confirm final revisions. File restoration does not claim reactivation. Return requires_activation when applicable. External edits block rollback. Before-images can contain secrets and remain private under Admin database0600.

Heating1.1.0 keeps previous default rules and adds configure(settings,expected_revision optional). Validate all settings atomically, lock decision engine, compare revision at mutation, await durable Store save and revert on failure. Admin heating_settings forwards CAS and verifies readback; ordinary parameters no longer require a Core restart. New Python code still needs supported activation, not a promised universal hot reload.

## Test environment and CI

`scripts/simulate_heating.py` executes production policy and adapter against fake device hosts, no production connection, and writes source hashes/result. GitHub Check Jarvis now runs addon tests, release checks, heating simulation, firmware bridge tests and amd64/arm64 container builds/startup smoke checks. CI commit724ec35ad0524d557d37697b32ccec1e92a7eebc passed both recorded runs40860262447/40860252736.

`testing/compose.yaml` is a pinned, loopback-bound separate HA2026.6.4 fixture with blank config and no production devices/credentials. It is PREPARED, not running on Odladeni. Current authenticated Odladeni tool exposes PHP storage/deploy, proc_open=false, no SSH/container management. Prior-context search found no verified separate Docker/VM deployment route. A hosted persistent HA needs an actual accessible container/VM host; a subdomain alone is insufficient.

## Review and validation

Independent reviewer identified token disclosure through job results, unchecked file write/readback, delayed settings persistence, missing backup dates, empty runtime expectations, configure concurrency/CAS and missing manual-backup space preflight. All important findings were addressed. No second review claimed. Latest local suite:203 addon tests +21 heating tests; GitHub CI also includes5 firmware-native tests and container builds. No physical voice/TV acceptance test is implied.

## Live deployment receipts

- Jarvis update fe80a464e071434aa44666c6c80c743c verified3.12.0; backup20e5ace6.
- Exact backup_delete jobs ops312-delete-91ee007c-20261029, ops312-delete-fd90919a-20261029, ops312-delete-e7b028f1-20261029 verified. Original protected backup9659c1f3 and pre-heating94e01687 retained.
- Host free space after cleanup3.8GiB.
- Heating prepared bundle ops312-heating-plan-20261029 binds source b1e4d520d0383b3b9489017b3be04d4a78231afd; activation ops312-heating-apply-20261029, backup4bb0a0c2. Final live status is recorded in OPEN-WORK.md after readback.

- Heating activation verified10:50:55UTC, phase active_verified; both sensors runtime1.1.0.
- Live configure proof300→301→300 verified without restart; original settings revision restored.
- Unrelated writer rejected with deployment_owned_by_another_work.
- Temporary text bundle apply and rollback verified; file absence confirmed afterward.
- Voice status Jarvis/muteoff/satelliteidle confirmed.

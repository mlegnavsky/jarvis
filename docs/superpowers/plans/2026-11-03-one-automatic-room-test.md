# One Automatic Room Test Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans inline; one fresh whole-change review at end, no per-task delegates.

**Goal:** perform the one owner-authorized <=30s automatic paired room measurement and erase microphone PCM.
**Architecture:** fixed admin control, durable one-shot coordinator, native protocol routing before cloud providers, existing RAM collector and scalar analysis.
**Tech Stack:** existing Python/Core2026.6.4/native RAOP, no dependency change.
**Spec:** docs/superpowers/specs/2026-11-03-one-automatic-room-test-design.md

## Global Constraints
One exact satellite/HomePod, one remote start, <=30s/3MiB collector/150s hold,
nonce32hex/120s, current Marin/volume; no generic policy expansion, cloud
microphone, identity/household actions, audio export or firmware/Core change.
Native inline execution and existing publicGit/deploy authorization retained.

## Review Focus
- A late/duplicate diagnostic pipeline cannot reach STT/LLM or restart a consumed test.
- Deadline/mute/HA shutdown closes the actual owned pipeline, not just a Python reader.
- A foreign pipeline or externally changed output must never be stopped/restored as ours.
- Preparation/native-start/source/output/analysis failures erase PCM and release owned generated resources.
- Core diagnostic recording/device audio hooks cannot receive microphone bytes.

### Task1: coordinator and bounded fixed control
Files: room_measurement.py, test_room_measurement.py, control.py, test_control.py.
Interface: RoomMeasurement(calibration,prepare,start_native,stop_native,ready,clock,utc); run(nonce,expires_at), capture(source,enhance), accepts(marker), abort(reason), snapshot().
- [x] RED control rejects unknown action today; add <=120s/noextra fields behavior.
- [x] RED coordinator absent: tests finite duration, source closure, durable one-shot newnonce/restart, preflight denial, prepare/start/output errors, mute/cancel and wipe.
- [x] Implement fixed passage, durable claim, ownership/deadline and existing CalibrationManager integration.
- [x] GREEN focused coordinator/control tests.

### Task2: native adapter and HA binding
Files: adapter.py/__init__.py, test_adapter.py/new test_room_binding.py, manifest version1.3.4.
Interface: install optional operator_handle before validate; native_session optional begin metadata callback; reserved prompt always consumed locally. Integration owns fixed entity START_CONVERSATION and terminal stop, generated silent file, TV/mute/external change subscriptions and HA shutdown cancellation.
- [x] RED operator bypasses provider validate only for fixed bound route, metadata-only start, late marker close, same target constraints.
- [x] RED integration has no provider/mic-disk paths; exact native start/end, current output/TV ownership, cancelled resource cleanup.
- [x] Implement binding;259 duplex and242 addon tests (20 optional skips), manifest/diff GREEN. Additional ownership RED/GREEN: remove only own pending prompt under foreign pipeline; abort TV-acquire preparation before a new human input is dropped.
- [x] Fresh review0Critical/3Important/0Minor. All3 fixed in one RED/GREEN pass,264duplex/242addon20optional skips/manifest/diff GREEN. Durable independent isolation and exact native reconnect added to close the marker-loss boundary; every ruling/exclusion recorded in hostproof.

### Task3: publish, activate, measure once, close
- [ ] Exact public tree/expectedHEAD CI+immutable publication, lease/space/backup/CAS/native1.3.4 activation.
- [ ] Fresh generated-only probe and exactsource verified before one fresh room_test control.
- [ ] One <=30s actual measurement; poll same operation/report, no automatic remote restart. Read on-Green scalar results, verify satellite idle/PCM0/closed tasks and owned restoration.
- [ ] Preserve outcome/limits/rulings in public sanitized evidence and private receipt, release lease, docsclosure. Original acoustic goal stays open unless physical evidence proves it.

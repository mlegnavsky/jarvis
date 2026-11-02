# Household command context Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give Jarvis current device knowledge and Czech light synonyms while preserving television guards and silent local actions.

**Architecture:** Extend the existing shared grammar. Join HA registries/live states into a read-only ephemeral catalogue for model turns. Gate local voice input on the exact TV's verified quiet state.

**Tech Stack:** Python/native HA2026.6.4, existing OpenAI agent, existing unittest suites; no new dependency.

**Spec:** docs/superpowers/specs/2026-11-02-household-command-context-design.md

## Global Constraints

- HomePod-only speech, Marin, gentle sarcasm, silent successful lights.
- Preserve exposure/action permissions, lock authorization and room boundaries.
- No new acoustic words, firmware/provider/Core upgrade, recording or idle cloud stream.
- Catalogue64KiB; total model messages96KiB; latest four user turns retained when pruning.
- Unknown/audible Apple TV input fails closed; acoustic source authentication remains unverified.

## Review Focus

- A quoted, negated, conditional or incidental light noun must not execute.
- Disabled/unavailable devices and entity-room overrides must not be misrepresented.
- Credentials/private attributes/text helpers must not enter model context.
- A large changing catalogue must not erase follow-ups or split tool-call groups.
- TV resuming while STT/authorization awaits must prevent a later command or speech.

---

### Task 0: Prevent generated speech from becoming a user turn

- [x] Reproduce the reported self-reply loop from bounded runtime counters; preserve HomePod speech and ordinary interruption.
- [x] Test own questions/fragments/control words against actual capture/playback intervals, including cancellation cleanup and deferred turns; preserve real yes/no/stop and post-playback replies.
- [x] Add bounded generated-text echo rejection, full400ms reference correlation and negotiated cancellation tail; never retain microphone transcripts/audio.

### Task 1: Finite Czech light synonyms

**Files:** managed_sources/voice_common/__init__.py, manifest.json; tests/test_voice_contract.py; managed_sources/companion/test_room_commands.py.

**Interfaces:** parse_command(text) retains Command(canonical,domain,service,scope,room). Synonyms canonicalize to existing rozsvit/zhasni paths, never toggle.

- [x] Add tests for světlo/světla/světýlko, prosím světlo, světlo v dětském pokojíku, rozsveť/rosviť, udělej světlo and explicit světlo zapnout/vypnout; reject quoted/incidental/negative/conditional/multiple commands.
- [x] Run shared/room tests; expect missing synonyms to fail.
- [x] Implement exact anchored synonyms and bump common1.0.3; preserve existing quote/room/action checks.
- [x] Run shared/room suites; expect all pass; commit.

### Task 2: Fresh read-only household catalogue

**Files:** create managed_sources/companion/catalog.py and test_catalog.py; modify conversation.py, room_commands.py, test_agent_boundary.py.

**Interfaces:** build_catalog(states,entities,devices,areas,exposed_ids) returns bounded typed snapshot; read_catalog(hass,exposed_ids) joins native registries. render_catalog(snapshot) produces compact marked data; bound_messages(messages) removes only complete old user turns above96KiB. native_resolution_probe adds catalogue summary and synonym cases without service calls.

- [x] Add tests: >30 live entities including non-exposed state/units; effective entity room; disabled/missing state; no private attributes/helper values; explicit limits; same-conversation fresh state; model receives latest context and retains earlier turns; local command bypasses catalogue; context bounds preserve tool groups.
- [x] Run tests; expect missing catalogue/boundary behavior to fail.
- [x] Implement bounded catalogue/HA adapter, ephemeral model injection after local shortcut, fresh system state and four-turn pruning; extend native resolution probe.
- [x] Run full companion/shared suites; expect all pass; commit.

### Task 3: Quiet-TV input boundaries and activation

**Files:** managed_sources/homepod_output/tv_session.py and test_tv_session.py; managed_sources/local_duplex/__init__.py, bridge.py, manifest.json, test_bridge.py; docs evidence/OPEN-WORK.

**Interfaces:** TVSession.input_safe() is side-effect-free and true only for paused/off/idle/standby. TurnBridge gains input_allowed callback defaultingTrue; checks before STT, authorization, agent and output. Local dialogue1.1.1 uses predicate and closes on audible TV regardless prior ownership.

- [x] Add quiet/unknown/pause-failure/resume-during-STT/authorization/response tests; expect old behavior to fail.
- [x] Implement minimal guards and version1.1.1; preserve all unrelated behavior.
- [x] Run companion, shared, duplex, HomePod and diagnostics suites plus addon/manifest checks; expect pass.
- [x] Fresh whole-change review; fix Important/Critical once with RED→GREEN, no re-review.
- [ ] Publish source CAS, prepare exact files/recovery/metadata, verify backup space/authorized retention, backed-up activate once.
- [ ] Verify actual versions, complete catalogue counts/readonly aliases/loaded source, fresh native synthesis probe; do not execute household devices during resolution checks. Preserve explicit acoustic acceptance limits and release lease.

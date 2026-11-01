# Local Voice PE Duplex Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Keep microphone capture active during local spoken answers and stop owned output when the human starts another utterance.

**Architecture:** A version-scoped PipelineInput adapter owns one bounded conversation using native enhanced PCM. Pure segmentation/reference gating and a cancellation-safe session orchestrator feed the existing STT, identity coordinator and conversation agent; native local announcement playback supplies XMOS reference.

**Tech Stack:** Python asyncio, HA Core2026.6.4/native ESPHome API, existing microVAD/STT/conversation/TTS. No new provider or firmware.

**Spec:** docs/superpowers/specs/2026-11-01-local-duplex-design.md

## Global Constraints

- Exact pipeline/satellite/player and Core version from spec; user volume/mute remain authoritative.
- Mic local only until completed utterance; no raw recordings or exported secrets; utterance<=30s, session<=240s/24turns.
- Coordinator/context-bound one-use grants remain the control authority; own output cancellation cannot affect a newer response.
- Preserve mute/button/EOS and external TV/player ownership. Synthetic/native checks are not acoustic acceptance.

## Review Focus

- Short Czech yes/no responses and immediate speech after a question retain their first syllable.
- Assistant-only echo does not repeatedly stop/restart the assistant or actuate devices.
- New speech during STT/LLM/TTS preparation cannot release stale output later.
- Mute, native abort, stopped audio source, provider failure and task cancellation always close capture and owned playback.
- External playback/TV changes and unrelated satellites never inherit this session's cancellation or device authority.

### Task1: Bounded speech and echo gate

Files: managed_sources/local_duplex/segmenter.py and test_segmenter.py. Interface feed(audio, probability, timestamp) -> onset/utterance; set_reference(pcm,started_at), clear_reference(); in-memory PCM only.

- [x] Write failing tests for preroll, short answers,30s ceiling, own echo with delay/gain, double-talk and silence; run RED.
- [x] Implement bounded PCM/rms envelopes, validated probabilities and reference correlation; run GREEN.

### Task2: Cancellation-safe conversation session

Files: managed_sources/local_duplex/session.py and test_session.py. Interface Session(transcribe,respond,play,stop,identity,...).run(frames); callbacks preserve generation ownership and capture remains concurrent.

- [x] RED: microphone continues while play blocks; speech cancels generation/output; no stale response; EOS/mute/limits; silent light finish and immediate follow-up.
- [x] Implement and run GREEN; commit tested pure engine.

### Task3: Pinned HA native adapter and local playback

Files: managed_sources/local_duplex/{__init__,adapter,ha_io}.py, manifest.json, tests. Existing room_commands forms test for Dětský pokoj diminutives.

- [x] RED: exact routing/delegation, validate+native start/end with no STT_VAD_END during playback, same context/PCM coordinator, native announcement STOP=true, ownership and provider failures.
- [x] Wire existing providers and native player, report/probe, optional enabled configuration; verify against pinned Core source/protocol and all relevant suites.
- [x] Independent whole-change review and regression fixes.

### Task4: Authorized deployment and physical evidence

- [x] Publish source with expected remote HEAD; inspect live revisions, storage, lease and private configuration. Add domain and recovery copies with CAS, backup/restart and runtime checks.
- [x] Poll same job, read back active hashes/version, mute, source and output. Run bounded native probe. Update OPEN-WORK/evidence and release lease.
- [ ] Owner physical acceptance: actual microphone frames during playback, speech interruption and short answer; noisy-room activation separately. No acoustic success claim until this evidence exists. See docs/evidence/2026-11-01-local-duplex-active.json.

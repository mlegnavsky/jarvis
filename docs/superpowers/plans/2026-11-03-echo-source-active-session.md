# Echo Source and Active Session Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans inline; one fresh whole-change review. Numerical helper is independent/read-only.

**Goal:** prevent false playback turns while preserving human speech and avoid cutting active conversations at240s.
**Architecture:** independently validate acoustic source evidence before integration; accepted-turn activity watchdog replaces absolute session age.
**Tech Stack:** existing Python/NumPy/Core2026.6.4; no new runtime dependency.
**Spec:** docs/superpowers/specs/2026-11-03-echo-source-active-session-design.md

## Global Constraints
Existing software/deploy/public Git authorization; nobodyhome/no automaticmic.
Keep240s rejected-input watchdog,5s source stall,8s idle,30/60/100s provider,
3s stop deadlines and a24 accepted-turn ceiling including interrupted turns.
No input/identity relaxation.
One final independent review, one material RED/GREEN fixpass; record minors.

## Review Focus
- Fresh accepted turn after old wall age must refresh lifetime, including a confirmed interruption.
- Rejected/empty/truncated input must not keep a noisy session alive indefinitely.
- Async source-verification failures must preserve input and clear transient PCM.
-80ms mixed human/shortstop/periodic and same-envelope negatives must never be labeled own echo by the tested candidate.
- Old-reference/clock/decoder/provider errors cannot strand speech or microphone resources.

### Task1: accepted-turn activity lifetime
Files: session.py/test_session.py, manifest/runtime version at final integration.
Interface: Session.activity_at monotonic clock; existing max_seconds becomes
accepted-input inactivity budget, visible in snapshot as budget policy.
- [x] RED: accepted turns at simulated180/239s continue beyond240s; confirmed human interruption also refreshes; empty/truncated input does not refresh.
- [x] Implement activity timestamp after valid text acceptance and refresh condition in consume; remove duplicate absolute async timeout.
- [x] RED accepted-turn ceiling: repeated valid interruptions previously bypassed completed-turn count (3 agent calls with max_turns2). Count accepted inputs and stop at the existing ceiling.
- [x] GREEN42 Session/confirmation tests and237 full duplex tests; addon242 tests (20 optional skips). Source-stall/cancel/provider behavior retained.

### Task2: acoustic evidence eligibility and selected integration
Files: numerical spike under/tmp first; only a validated scorer may become
managed_sources/local_duplex/source_match.py with tests and an async bounded
output/TurnBridge hook. Pin exact scorer/thresholds in this plan after the
numerical decision, before production implementation.
- [x] Measure held-out actual voiced echoes/RIR/filter/drift and independent/same-envelope/shortstop/80–400ms human mixtures, with explicit failures.
- [ ] Select only a candidate preserving every tested human negative; otherwise retain failed evidence and investigate another approach without deploying it.
- [ ] RED/GREEN exact async integration, unknown/error/fresh-reference and human protections; generated-only native self-test must validate the selected runtime path.
- [x] Final300.1915s replay, exactsource183cec10 unchanged:8/8 human turns including275s accepted; no240s cut,0 provider failures, closed workers/readers,256KiB caps. Known acoustic check fails (2 injected own-ASR mismatches still accepted). Full suites/manifest/diff passed. See docs/evidence/2026-11-03-active-session133-host-proof.json.
- [ ] One fresh whole-change review; public expectedHEAD/exacttree/CI, backed-upCAS/nativeproof, receipt/release and honest operational closure.

Numerical decision: reject both log-band and cross-fitFIR candidates for shortmixedhuman safety (271/288 and67/144 falseechoes when covering own echoes). No SourceMatch module/integration is eligible. Real paired room measurement required; currentJarvis policy has neither allowed nor supported assist_satellite.start_conversation. Do not bypass the policy or reinterpret broadsoftwareconsent as new automaticmicrophone permission. Nativecollector is already prepared/defaultoff/30sRAM-only; prepare a concrete one-time automatic roomtest proposal after completing authorized sessionfix, then obtain explicit permission for remote microphone activation.

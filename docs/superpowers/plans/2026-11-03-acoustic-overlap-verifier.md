# Acoustic Overlap Verifier Implementation Plan
> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans inline. One fresh whole-branch review with streaming plan; no repeated reviewers.
**Goal:** reject high-confidence own audio even when STT words differ, before cancelling playback.
**Architecture:** bounded native coarse/fine waveform fit with identical preemphasis and all-block consistency; optional async bridge veto, fail open for uncertain human input.
**Tech Stack:** stdlib and Core's existing audioop-lts kernel; HA executor.
**Spec:** docs/superpowers/specs/2026-11-03-acoustic-overlap-verifier-design.md
## Global Constraints
Existing completed input only; generated reference90s/utterance30s; at most2s uncertain alignment search;150ms cooperative measurement/250ms await deadline. No recording, authority or original RMS gate change; no immediate-human-interruption claim.
## Review Focus
- Any new/short/unknown human voice including mixed speech and quiet stop remains eligible.
- Low energy, repeated tones/periodic ambiguity and same-envelope independent voices never establish positive source evidence.
- Output generation/reference replacement and capture-time queue delays cannot veto a fresh human turn.
- Native kernel absence/errors/timeouts are explicit unknowns and keep existing input semantics.
- Reports remain scalar/bounded and source/mute/external stop cancellation remains immediate.
### Task1: independent acoustic source veto
Files: create acoustic_verifier.py/test_acoustic_verifier.py; modify bridge.py,ha_io.py,__init__.py and existing integration tests.
Interfaces: verify_own_audio(mic:bytes,ref:bytes,played_seconds:float)->scalar dict with own_audio bool; optional async transcript filter awaited by TurnBridge before cancellation and rechecks input safety. HomePod immutable reference snapshot/generation/capture time bound each worker.
- [ ] RED room-filtered/highpass/gain/drift own waveform versus independent/same-envelope/mixed human and short replies; uncertainty, periodicity, timing and CPU caps fail open.
- [ ] Implement minimal2k coarse/16k fine native fit, all short blocks and explicit ambiguity checks. If meaningful human/echo controls fail, reject candidate and record evidence; do not deploy it.
- [ ] RED/GREEN async bridge veto delays no input source, stale reference and late TV/stop cannot reach actions, no transcript/PCM scalar leakage.
- [ ] Relevant/full duplex suites and combined fresh branch review; one RED/GREEN material fix pass.
- [ ] Commit and deploy only a passing candidate with streaming plan's shared Git/CI/native activation checks. Record actual room acceptance as pending until observed.
Expected commands: PYTHONPATH=managed_sources/local_duplex python -m unittest discover -s managed_sources/local_duplex -q; python scripts/check_manifest.py; git diff --check. All pass. A failed viability control is a rejection, not a reason to lower the bar.

## Candidate rejected before activation
Five directsource/control tests firstRED thenGREEN; held-out voicedroom/highpass positives only1/15, humans30/30preserved. Fails intendedcoverage, no thresholdrelaxation. Experiment moved under experiments/rejected-acoustic-verifier-20261103, excludedfromnativebundle and notwired intoBridge. Subsequentasync/deploymentsteps are cancelled for thiscandidate; streaming delivers independently. Physical acoustic goal remainsOPEN, and pairedmicrophone/reference data needs explicitrecordingconsent.

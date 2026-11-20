# Voice refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. Implement inline, then independent review.

**Goal:** Consistent silent local controls and bounded optional learning without dialogue loops.
**Architecture:** Shared pure command/turn contract; separate bounded background worker; existing native HomePod completion ownership preserved.
**Tech Stack:** Python, SQLite, HA2026.6.4.
**Spec:** docs/superpowers/specs/2026-11-01-voice-refactor-design.md

## Global Constraints
Public exposed lights only; locks/profile/private permissions unchanged. No extra calibration, no raw audio persistence, no firmware or HA upgrades, no speculative cancellation suppression. Existing bank revision preserved.

## Review Focus
- Explicit all-house targets never include hidden lights/nonlights.
- Polite commands close local conversations even on error.
- Conditional, quoted and multiple commands never acquire grants.
- Optional worker never delays command or exceeds2tasks.
- Training utterances never act; missing voice pipeline/invalid grant stays blocked.

## Task1 — One command and turn contract
- [x] Reproduce all-house, courtesy/name/synonym drift and context:### bugs.
- [x] Implement shared parse/canonical/noop and reuse in authorization/room/dialogue.
- [x] Add end-to-end grant/target/execution tests and verify protections.

## Task2 — Learning lifecycle and completion
- [x] Add tests for queue bound, timeout, cancellation, no pending raw data after stop.
- [x] Extract BackgroundLearning; preserve optional identity semantics and training priority; expose counters only.
- [x] Clear local command session state; truthful direct-wake blocked reason; preserve audio completion behavior.

## Task3 — Verify and deploy once
- [x] Relevant/full suites, independent review and remote CI passed.
- [x] Publish, preflight storage, CAS bundle/restart, reconcile same job, postboot readback/runtime/wake state, release lease.
- [x] Persist evidence and physical limitations.

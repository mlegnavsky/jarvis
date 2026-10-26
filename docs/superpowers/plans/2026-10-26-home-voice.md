# Home Voice Preparation Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans; inline implementation, one final independent review.

**Goal:** Prepare installable home voice configuration and optional television ducking without pretending to deploy hardware remotely.
**Architecture:** Standard HA voice pipeline and OpenAI integration; blueprint runs in HA, independent of Jarvis app/MCP. No new audio backend.
**Tech Stack:** HA automation blueprint, YAML/Jinja, existing unittest suite.
**Spec:** docs/superpowers/specs/2026-10-26-home-voice-design.md

## Global Constraints
No credentials or real entity inventory. No API spending or deployment. Home voice authorization separate from MCP policy. Default voice control and TV automation disabled. Echo cancellation is not generic TV suppression.

## Review Focus
- Unknown/off/muted/low-volume TV must not be raised or touched.
- Manual volume change must not be overwritten based on stale original volume.
- Timeout/disconnected satellite must not cause late volume increases.
- Repeated listening during one conversation must not overwrite the saved original.
- Pipeline/native exposure configuration must not claim unimplemented shared memory, wake suppression or remote installation.

### Task 1: Television blueprint
- [x] Write tests reading/rendering actual YAML predicates and action data for playing/off/muted/missing/low-volume TV, manual change, timeout and idle debounce.
- [x] Run RED for absent blueprint, implement single-run state-triggered blueprint with safe restore.
- [x] Run tests GREEN and full suite; commit.

### Task 2: Voice deployment bundle
- [x] Add Czech Jarvis prompt, nonsecret profile, exposure/pipeline setup, memory and TV testing/rollback instructions.
- [x] Update prior voice/roadmap docs to selected separate Jarvis design, preserving ChatGPT connector.
- [x] Validate YAML/templates; independent review; fix meaningful findings with RED→GREEN; push existing draft PR and verify CI. Hardware/API/Green acceptance remains pending.

## Result

Prepared native pipeline guide, Czech prompt, nonsecret reference profile, reviewed-memory template, acoustic/operational checklist and optional TV blueprint. No hardware, billing or Green configuration was changed.

54 automated tests passed. [CI run 40353927336](https://github.com/mlegnavsky/jarvis/actions/runs/40353927336) passed tests, arm64/amd64 image builds and both amd64 startup/auth smoke checks on source commit `69bbdc76c45be9789dab84ebefa9668bc86c9800`.

Independent review identified disconnect/reconnect restoration and endpoint-only idle debounce. Both were reproduced and fixed with YAML-driven sequence/predicate tests; suite54/54. No deferred findings. Decision: native HA pipeline rather than custom audio daemon; benefit fewer moving parts, cost initial provider/hardware binding in HA UI. Native Assist exposure is separate from MCP allowlists. Actual HA config validation, voice hardware, room acoustics, response latency, follow-up speech and API usage remain unverified until home acceptance.

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
- [ ] Write tests reading/rendering actual YAML predicates and action data for playing/off/muted/missing/low-volume TV, manual change, timeout and idle debounce.
- [ ] Run RED for absent blueprint, implement single-run state-triggered blueprint with safe restore.
- [ ] Run tests GREEN and full suite; commit.

### Task 2: Voice deployment bundle
- [ ] Add Czech Jarvis prompt, nonsecret profile, exposure/pipeline setup, memory and TV testing/rollback instructions.
- [ ] Update prior voice/roadmap docs to selected separate Jarvis design, preserving ChatGPT connector.
- [ ] Validate YAML/templates; independent review; fix meaningful findings with RED→GREEN; push existing draft PR and verify CI. Hardware/API/Green acceptance remains pending.

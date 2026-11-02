# Fast voice implementation plan

> For agentic workers: execute inline with superpowers:executing-plans, then independent whole-change review.

Goal: reduce measured agent waiting while preserving household authority and disclose unproven acoustic goals.
Architecture: bounded hot-read primary-voice model policy plus fixed read-only model audit; existing native HomePod transport unchanged.
Tech stack: HA2026.6.4, existing OpenAI client, Python.
Spec: docs/superpowers/specs/2026-11-02-fast-voice-design.md

## Global constraints
No new credentials/provider or household service rights. Preserve Marin, own0/mute, silent lights, owner anchors, privacy and all current memory guards. No unsupported1s/AEC claim.

## Review focus
- Invalid/symlink policy cannot choose arbitrary endpoint/model.
- Non-target voice/text requests retain configured model and parameters.
- Model failure returns existing error, no speculative duplicate household execution.
- Time shortcut cannot bypass TV/source/identity preparation.
- EOF remains immediate cleanup, now accurately labelled.

## Task1: fast voice policy and model audit
- [x] RED tests: primary scope, policy bounds/defaults/symlink rejection, actual query request uses selected fast model only on primary, audit fixed text/no tools/no content saved/error sanitization.
- [x] Implement companion/voice_policy.py, integrate conversation.query with exact primary scope and numeric model request diagnostics; shorter default instruction and guarded local time answer.
- [x] Add local_duplex/model_probe.py and fresh model_audit operator action, report safe current model settings/metrics.
- [x] Run companion, duplex and full addon suites; manifest/diff checks; commit.

## Task2: EOF attribution and deployment proof
- [x] RED source-EOF test expects audio_source_ended with elapsed/stage while owned output still cleaned.
- [x] Add explicit EOF evidence, correct client scheduling label while retaining compatibility key as deprecated.
- [ ] Independent review, publish, backed-up CAS deployment, fresh postboot probe and model audit. Select faster valid candidate via policy CAS, then same voice-scoped probe with TV paused/restored, no playback/actions.
- [ ] Verify source/runtime, fixed output, release lease; record measured result and next physical test. Human barge-in/AEC remains pending.

## Review ledger
Fresh review found FIFO open could block forever; O_NONBLOCK regression RED→GREEN fixes it. Regraded fixed512token cap because it could regress configured longer answers; preserve larger configured budget, regression RED→GREEN. Short replies are a prompt choice, never forced truncation. Deferred minor: no direct integration test for operator TV probe wiring; TVSession unit behavior is covered and live pause/restore remains an acceptance check. Benchmark fixed-greeting results alone never establish full-turn speed.

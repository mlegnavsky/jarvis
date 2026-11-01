# Open household controls and gradual familiar voices Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. Steps use checkbox syntax for tracking.

**Goal:** Anyone can use supported local light commands without speaker identification; successful actions stay silent. Learn recurring voices only for occasional names.
**Architecture:** Keep enforce/strict lock checks. Explicit public_controls grants short-lived, text/action/target-bound light-only control tokens before speaker rejection. Separate SQLite familiar clusters never become authorized profiles or private memory principals. Unknown ordinary conversation is allowed without private context.
**Tech Stack:** Existing Python/SQLite/HA2026.6.4, existing local embeddings.
**Spec:** Owner request2026-11-01 in OPEN-WORK.

## Global Constraints
No raw audio, no training execution, no self-granted locks/private access, immutable owner bank, bounded data, exact source/deploymentCAS and fresh runtime verification. Public mode must never let a family-training command actuate. Model outage must not block public lights.

## Review Focus
- Short and missing identity results still allow exposed lights only.
- Family training never acts even in public mode.
- Repeated playback/duplicate utterances never mature a name cluster.
- Different/mixed/ambiguous voices cannot attach a pending name.
- Learned names never select a private voice memory principal.

## Task1 — Public local light controls
- [x] Add regression tests for too-short stranger lights, unavailable model, unknown ordinary conversation, protected locks and training suppression.
- [x] Implement opt-in public_controls in coordinator and runtime; preserve one-use target binding and silent success.
- [x] Run speaker/companion suites.

## Task2 — Familiar voices
- [x] Add tests for bounded private persistence, quality/playback/duplicate rejection, six independent utterances across three conversations, ambiguity, explicit name assignment from same matched voice, expiry/forget and no authorization promotion.
- [x] Implement familiar.py using profiles SQLite; expose only optional name/question to non-command conversation. Leave original profile bank unchanged.
- [x] Integrate optional familiar name without private memory reuse; at most one name question per day/cluster and occasional address every sixth matching conversational turn.
- [x] Run full relevant suites and addon tests; independent review.

## Task3 — Release
- [ ] Publish source, acquire lease, storage preflight, backed-up CAS deploy/restart, poll same job, verify runtime/readback and release.
- [ ] Persist final evidence and limits. No fresh owner calibration required.

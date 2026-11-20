# Owner calibration implementation plan

> **For agentic workers:** Use superpowers:executing-plans for inline implementation.

**Goal:** Allow five supervised calibration samples through existing authenticated administration without requiring prior voice recognition.
**Architecture:** Fresh single-use control file, private bounded SQLite collection, coordinator interception before the authorization gate, periodic report and manifest discovery.
**Tech Stack:** Existing Python/SQLite Home Assistant integration; no new packages.
**Spec:** docs/superpowers/specs/2026-11-01-owner-calibration-design.md

## Global constraints

No live profile/anchor/threshold/authorization change; no raw audio; five samples; ten-minute expiry; configured satellite only; samples unreviewed.

## Review focus

Request replay/restart, profile deletion/recreation, wrong satellite, playback/quality failures, never issuing command grants during calibration.

## Task 1: collection and runtime adapter

- [ ] Write failing tests in speaker_identity/test_owner_calibration.py for single-use request, stable ID, unknown voice collection, five-sample completion, expiry, deduplication, quality/playback, wrong satellite and preserved anchors/authorization.
- [ ] Implement owner_calibration.py with process_control(path), collect(device,item), summary(); integrate before Coordinator._turn_sync authorization and expose runtime report plus manifest control path.
- [ ] Run speaker suite, companion suite, addon suite and release checks. Obtain code review, fix important findings, publish exact Git tree.
- [ ] Read current revisions/storage; prepare/apply backed-up12-or-fewer-file bundle; reconcile runtime after restart, verify hashes and profile. Start a fresh owner session only after activation and verify collecting0/5. Record receipt and explain five-sample procedure.

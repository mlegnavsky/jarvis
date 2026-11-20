# Duration-aware supervised voice repair Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans inline; no implementation delegation.

**Goal:** Repair the owner's representation using one fresh long training utterance and an independent held-out utterance, including short segments, without changing authentication thresholds.

**Architecture:** Keep existing immutable anchors and five supervised training vectors. An owner-started repair session collects exactly two clean utterances with two backend windows each; first utterance and windows may train, second and every window only validate. Existing five owner/other holdouts remain independent; controlled activation still requires strict improvement, zero other accepts and gap>=0.2. No automatic activation, no waveform retention.

**Tech Stack:** Existing Python/SQLite native speaker component, current CAMPPlus model, CAS deployment.

**Spec:** This document is the scoped design and implementation specification; owner requested complete recognition improvement after repeated failed physical tests.

## Global Constraints

Preserve stable voice_id, immutable anchors, permissions, recognition0.65, distinct-second-reference0.6, inter-profile margin0.12, strict lock/delete0.75. Existing schema1 calibration remains compatible. New repair vectors remain private and are erased on forget/retention. Do not represent the two utterances as unbiased household accuracy or replay proof. Do not change firmware interruption policy in this recognition change.

## Review Focus

Training/holdout utterance overlap must reject; every held-out short window must pass; missing/malformed windows reject; model evidence revision includes private windows; same-profile deletion erases windows; schema1 snapshot transaction stays intact.

### Task1: Bounded owner repair collection

Files: owner_calibration.py, policy.py, test_owner_calibration.py.
- [ ] Add red tests: authenticated repair action requires two6s+ utterances and2valid backend windows; no authorization/live write; retention/forget erase windows.
- [ ] Add mode migration(default calibration), separate private window table and dynamic required counts; owner controls remain fresh, stable-ID bound and same-satellite.
- [ ] Run speaker tests and commit.

### Task2: Independent full/window candidate review

Files: review.py, test_review.py, matching_control.py only if compatibility needs it.
- [ ] Add red schema2 four-role repair tests:6/6 positives plus every new holdout window pass,0/5 other, strict improvement and score gap; never train from held-out sample.
- [ ] Read all DB inputs and window evidence under one read transaction; fingerprints and activation rechecks bind all inputs. Keep schema1 unchanged.
- [ ] Run speaker tests and commit.

### Task3: Verify, publish and deploy

Files: __init__.py/manifest.json version1.1.8, OPEN-WORK and evidence receipt.
- [ ] Independent final review, relevant suites and CI; no private vectors in Git.
- [ ] Fresh HEAD/CAS/lease/storage protection; deploy source and recovery copies, verify actual running version and lease release.
- [ ] Start repair collection only when owner can supply the two phrases; inspect actual results and activate only if eligible. Until then report physical recognition unresolved.

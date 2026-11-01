# Cohort voice matching Implementation Plan

> **For agentic workers:** Execute inline with superpowers:executing-plans; independent final review.

**Goal:** Use existing owner and owner-attested other-speaker embeddings to improve noisy household recognition without another recording request.

**Architecture:** New explicit cohort_margin_v1 policy keeps positive and exclusion references in a private structured template. Require two distinct positive references supporting the turn, a positive-to-exclusion score margin, and a separate shorter-window support threshold. Existing matching policies remain unchanged; locks/deletion retain raw whole and every-window0.75. Manual CAS activation/rollback stores the complete private bank atomically. New schema3 review validates existing5independent owner holdouts and negative leave-one-utterance-out folds, so a negative query is never tested against itself in its exclusion cohort.

**Tech Stack:** Python/SQLite native speaker component; current local model, no new audio, no new services.

**Spec:** This document; owner explicitly authorized replacing recognition and requested no additional calibration samples.

## Global Constraints

Whole threshold0.55, window threshold0.50, second positive reference floor0.50, exclusion margin0.20, inter-profile margin0.12. Strict lock/delete threshold0.75 remains. Preserve anchors/stable identity/permissions, before-images and rollback. No global accuracy/replay guarantee; physical ordinary-use verification remains pending. No change to firmware false-abort handling.

## Review Focus

Missing or malformed exclusion bank fails closed; negative holdout never scores against itself; same-speaker window support does not weaken lock checks; candidate evidence binds both reference classes and parameters; migrations must not silently change an existing live policy.

### Task1: Cohort policy

Files: policy.py, coordinator.py, new test_cohort_policy.py.
- [ ] Red tests: noisy positive with two supporting refs and exclusion margin can match; one-close-ref, cohort overlap, malformed/missing bank reject; legacy unchanged.
- [ ] Implement structured bank/evidence and scoped window matching. Raw scores remain available for strict controls.
- [ ] Run speaker tests.

### Task2: Independent review/activation

Files: new cohort_review.py/test_cohort_review.py, review.py snapshot routing, existing matching_control regression coverage.
- [ ] Red tests for independent owner holdouts, negative leave-one-out, cohort rejection, evidence revision and atomic rollback of structured bank.
- [ ] Schema3 explicit non-regressing migration allowed by owner request:5/5owner, no regression,0/5negativeLOO, raw owner/negative gap>=0.2. Report validation scope and no physical proof. No auto activation.
- [ ] Independent final review, tests, CI.

### Task3: Deploy and guarded activation

Files: manifest/init1.1.9, OPEN-WORK/evidence.
- [ ] Fresh remote/CAS/lease/storage, native deploy and actual runtime verification.
- [ ] Replace expired repair plan with schema3 referencing existing attested sessions only. Inspect live review; activate only if qualifying with fresh exact revision and replay acknowledgement.
- [ ] Verify active bank/identity/anchors, release lease. No request to repeat calibration.

### User-requested extension: guided family enrollment

Owner authorized a spoken wizard triggered by “Nauč se nového člena rodiny”. Persistent private workflow asks name and consent, collects5training answers, requires3independent control answers plus short-window tests. Training commands never execute. Progress describes test completion, never biometric probability. Variation learned during validation resets the independent validation sequence. Bound to24attempts and preserves accepted state on pause/restart. Existing names cannot be overwritten. Profiles start with no permissions; fresh authenticated operator control may approve lights only, with stable-identity/bank revision and validation proof. Light-only members cannot enroll others or control locks. Known copied cohort references are erased when their source profile is forgotten.

Files: family_questions.py, family_enrollment.py, family_control.py and tests; coordinator/init wiring; docs/voice/FAMILY-VOICE-GUIDE-CS.md.

### Existing failure correction: external HomePod signaling

Native terminal TTS-start arms firmware acoustic stop handling despite the terminal not rendering the answer or receiving an echo reference for HomePod. Preserve Core event diagnostics but withhold the synchronous terminal callback for routed TTS-start, with finally restoration. Keep actual RAOP completion followed by silent terminal TTS-end and physical-button cancellation. No firmware or microphone mute changes. Test native callback isolation, unrelated routes and button cancellation. Physical ordinary-use confirmation remains pending.

# Authorized Voice and Profile Adaptation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Enforce Martin's voice authorization for Aničko, room lights and the entrance lock, with bounded profile adaptation that cannot overwrite its trusted baseline.

**Architecture:** Retain CAMPPlus and native Assist. Bind permissions to a stable voice_id, enforce one-use utterance evidence before both local and LLM actions, and keep immutable enrollment anchors separate from candidate updates and independent validation samples. Acoustic wake detection only requests verification; it never grants permission.

**Tech Stack:** Python, SQLite, Home Assistant 2026.6.4, ESPHome Voice PE, CAMPPlus, existing microWakeWord training workflow.

**Spec:** docs/superpowers/specs/2026-11-01-authorized-voice-design.md and Martin's approved conversation extension: continuous guarded learning, independent evaluation, rollback, pronunciation learning separate from identity.

## Global Constraints
- Wake phrase Aničko; commands zhasni, rozsviť, zamkni, odemkni.
- Light targets use actual microphone area; entrance lock is lock.vstup_zamek_vchod.
- Never use lock.open. Never operate the real entrance lock during automated testing.
- Unknown, ambiguous, mixed, short, expired or unavailable voice evidence grants no action.
- Pending action confirmation expires after 10 seconds; wake verification window is 6 seconds.
- Keep original enrollment anchors; no automatic threshold relaxation.
- Voice matching is probabilistic; no claim of perfect identity or replay resistance.
- No cloud transfer or permanent storage of raw household audio for learning.
- Profile creation is not permission assignment. Preserve current deliberate-button access while wake verification is incomplete.

## Review Focus
- A household member replaces a deleted profile under the same name: no inherited authorization (Task 1).
- A valid voice result is reused on a different action, room or follow-up: deny (Task 2).
- A noisy but high-scoring sample gradually drifts the profile: original anchors and independent validation reject promotion (Task 3).
- Television or HomePod playback overlaps real speech: no adaptation or unverified action (Tasks 3, 5).
- Firmware model addition exceeds device capability or fails OTA: preserve functioning button path, report unverified rather than success (Task 5).

---

### Task 1: Stable profile authorization and protected enrollment
**Files:** Modify managed_sources/speaker_identity/policy.py, coordinator.py, services.yaml, __init__.py; extend test_policy.py and test_coordinator.py.
**Interfaces:** VoiceProfiles.authorize(voice_id: str) -> dict; VoiceProfiles.is_authorized(voice_id: str) -> bool; VoiceProfiles.profile_summary() -> list[dict].
- [ ] Write failing tests for explicit authorization, missing identity, deletion/recreation under same label, immutable anchor retention and unauthorized enrollment.
- [ ] Run the speaker identity unittest suite and confirm expected failures.
- [ ] Add migration preserving existing vectors as protected anchors. Require authenticated owner-controlled authorization/enrollment operations; do not make every existing profile authorized. Bind Martin's confirmed current profile by stable ID.
- [ ] Report recognized and authorized separately; never expose embeddings in routine diagnostics.
- [ ] Run the suite and commit.

### Task 2: One-use voice evidence and command enforcement
**Files:** Create managed_sources/speaker_identity/authorization.py and test_authorization.py. Modify hooks.py, coordinator.py, managed_sources/companion/runtime.py, conversation.py, room_commands.py and corresponding tests.
**Interfaces:** VoiceGate.issue(evidence: dict) -> str; VoiceGate.consume(token: str, satellite_id: str, text: str, action: dict) -> dict; VoiceGate.confirm(satellite_id: str, action: dict, evidence: dict) -> dict.
- [ ] Write failing tests: expired/reused evidence, changed microphone/text/target/action, speaker switches during follow-up, unavailable model, local action bypass and LLM tool bypass.
- [ ] Verify failures before implementation.
- [ ] Validate per-utterance evidence before any target service call. Never use the terminal's HA account as voice proof. Retain normal signed-in non-voice application policy separately.
- [ ] Add explicit entrance lock resolution for zamkni/odemkni and exact room light resolution. A short pending command needs a new longer utterance explicitly confirming the same action within 10 seconds, from the authorized voice.
- [ ] Exercise lock actions against a fake service host only. Verify all denial cases produce zero service calls.
- [ ] Run speaker and companion suites and commit.

### Task 3: Candidate learning, independent validation and rollback
**Files:** Create managed_sources/speaker_identity/adaptation.py and test_adaptation.py. Modify policy.py, coordinator.py and __init__.py.
**Interfaces:** Adaptation.offer(voice_id: str, evidence: dict) -> dict; Adaptation.evaluate(voice_id: str) -> dict; Adaptation.promote(voice_id: str, expected_revision: str) -> dict; Adaptation.rollback(voice_id: str, expected_revision: str) -> dict.
- [ ] Write failing tests for unchanged anchors, ineligible short/noisy/mixed/playback samples, duplicate samples, candidate corruption, concurrent revision conflicts, failed persistence and rollback.
- [ ] Verify failures.
- [ ] Keep immutable anchors, bounded candidate embeddings, separate holdout embeddings and versioned accepted profiles. Never use the same utterance as both candidate and validation.
- [ ] Reuse existing conservative improvement threshold 0.85 as an initial collection floor, not a calibrated probability. A candidate must match the immutable anchors as well as the current profile. Do not reduce recognition thresholds automatically.
- [ ] Require quality evidence and original-run authorization. If noise/overlap/playback quality evidence is absent, reject adaptation rather than assume clean audio.
- [ ] Keep a maximum of eight diverse candidate embeddings per version; bound update rate to one eligible candidate per completed conversation. These limits are implementation defaults, subject to household validation.
- [ ] Evaluate old/new profiles at the same fixed decision thresholds against independent genuine holdouts and consented impostor/replay tests. Never promote on improved similarity alone. Missing genuine or negative validation evidence means collecting/awaiting_validation, never automatic promotion.
- [ ] Promote only with improved genuine recognition and no additional observed false accepts. Persist an atomic revision and restorable prior version.
- [ ] Run tests and commit. Report statistical limits; passing a finite test does not establish zero error.

### Task 4: Deliberate calibration and pronunciation learning
**Files:** Modify coordinator.py and services.yaml; create managed_sources/companion/pronunciation.py and tests/test_pronunciation.py; extend runtime.py.
**Interfaces:** Pronunciation.propose(voice_id: str, heard: str, canonical: str) -> dict; Pronunciation.confirm(voice_id: str, heard: str, canonical: str) -> dict.
- [ ] Write failing tests: collecting more samples cannot overwrite anchors, holdout contamination is rejected, unauthorized speaker cannot add aliases, alias learning never changes identity/permissions.
- [ ] Verify failures.
- [ ] Add a guided owner-initiated calibration flow for several minutes of varied speech across different sessions/distances. Reserve distinct utterances for validation. Existing three enrollment samples remain the trusted starting set.
- [ ] Keep pronunciation aliases scoped to recognized authorized voice. Confirm a proposed alias before enabling it; preserve exact action and target constraints.
- [ ] Do not silently collect other family members as negative data. Household validation uses explicit participation.
- [ ] Run tests and commit.

### Task 5: Acoustic models and verification capture
**Files:** Modify tools/wake_training/train.py and test_train.py on training/czech-wake-candidates-20261028, .github/workflows/czech-wake-training.yml; modify managed_sources/voice_diagnostics/direct_wake.py, speaker_identity/hooks.py and firmware bridge tests as needed.
**Interfaces:** Existing model manifests and revision-bound firmware installation contract.
- [ ] Inspect deployed firmware configuration privately and verify supported model count, memory, custom-model enable flags and pre-roll availability. Do not print secrets or copy private config to Git.
- [ ] Add failing tests for Aničko target phrases, exact word-to-action mapping, no INTENT jump before verification and rejected short/missing pre-roll.
- [ ] Implement Aničko model training and retain available zhasni/rozsviť/zamkni/odemkni training assets. Training outputs remain candidates until acoustic validation.
- [ ] Preserve captured wake-word audio for identity verification only in bounded transient memory where supported. If the device omits that audio, use the longer confirmation flow; do not identify a preceding short word from unrelated subsequent speech.
- [ ] If adding firmware model IDs is unsupported, extend the existing allowlisted bridge with revision checks, backups and tests before attempting installation.
- [ ] Evaluate available local replay-detection components on genuine speech, TV and recordings of Martin. A random spoken challenge must check both requested words and speaker identity, but is not treated as a guarantee against voice cloning.
- [ ] Do not activate lock-capable wake execution until the evidence gate and replay limitations are tested and accurately reported.
- [ ] Run component tests, firmware compile and CI. Commit candidate code/models with provenance.

### Task 6: Deployment and actual household acceptance
**Files:** Managed release snapshot/manifest, deployment receipts under docs/evidence, diagnostics reporting.
**Interfaces:** Existing deployment_acquire/prepare/apply/release and firmware_install.
- [ ] Run complete repository CI and relevant speaker/companion/wake suites; inspect every failure.
- [ ] Back up, acquire deployment ownership, update runtime and recovery snapshot together, validate Core, activate and verify exact runtime versions.
- [ ] Preserve Martin's current profile and prior rollback version. Do not delete or recreate enrollment.
- [ ] Verify button activation, HomePod output, known/unknown/short speech, TV, model outage, replay and follow-up speaker changes with the user.
- [ ] Test actual lock movement only upon a separate explicit user test request at the door; all earlier tests use a fake lock.
- [ ] Report separately: code deployed, models trained/installed, household profile calibrated, adaptation enabled or awaiting validation, replay detection verified or unsupported. Never call the whole feature complete if a part remains missing.

# Suppressed voice terminal completion implementation plan

> **For agentic workers:** Use superpowers:executing-plans for this single targeted fix.

**Goal:** A suppressed acoustic light hint returns ESPHome to idle and permits the next physical button/wake request.
**Architecture:** Native RUN_END already stops a microphone and targets IDLE. Do not emit STT_VAD_END immediately before it: ESPHome 2026.10.1 leaves the pending STOP_MICROPHONE target at AWAITING_RESPONSE when both arrive before its next loop. Delete unused prepared TTS before RUN_START so no dead streaming URL is advertised.
**Tech Stack:** HA Core2026.6.4, ESPHome2026.10.1, Python unittest, narrow pinned C++ protocol fixture.
**Spec:** Owner requests rapid silent light commands, room suffix capture and reliable operation with TV; this task repairs the newly observed permanently blinking terminal. Acoustic noise accuracy remains a separate acceptance item.

## Constraints
Preserve current light grammar, protected locks, TV media guard, HomePod ownership and firmware weights. No OS/Core version upgrade. No recording by default after restart. Reuse actual Git HEAD, CAS revisions, lease and backed-up deployment.

## Review focus
Back-to-back events before device loop; startup versus streaming states; unused TTS URL; suppressed HomePod cancellation; validation/cancellation cleanup.

## Task1
- [x] Add regression invoking the real adapter and exact pinned C++ state transitions; verify current code ends in AWAITING_RESPONSE.
- [x] Add regression for TTS deletion before native start; verify failure.
- [x] Remove premature VAD_END; clear unused TTS before start; bump diagnostic manifest/report version.
- [x] Run diagnostic and affected HomePod/identity suites, addon suite, manifest and diff checks; review independently.
- [x] Deploy source/recovery/metadata with lease/CAS/backup; verify restarted runtime, mic unmuted, Jarvis selection and capture disabled. See evidence receipt.
- [x] Publish source after explicit owner approval. GitHub connector published equivalent commit 9548ba1b6d9f40501811d11a5df06e830e67a1ce; exact reviewed tree ecaebbf23b3d69b38b29e8273f45b977c1b85987 verified. PR41346386783 and push41346382128 completed successfully. Native recovery metadata now points to the published source; no additional restart. Household acoustic acceptance remains open.

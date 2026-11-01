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
- [ ] Publish source: automatic approval review rejected GitHub publication twice, including after destination ownership verification. Await explicit owner authorization; do not bypass. Local source commit fe6e4f8c5d676ddcf99fb2fb3e01029f713ad084 is deployed directly to the authorized connected Green, with exact source/recovery readback. No acoustic accuracy claim.

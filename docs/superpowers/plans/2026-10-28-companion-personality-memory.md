# Companion personality, memory and awareness completion

Goal: deliver the user-approved first increment, validate the real installation, preserve source and fix review findings.

Architecture: extend the existing HA conversation agent, local bounded SQLite notes for authenticated HA users, in-memory guest sessions, and on-turn exposed-state observations. Keep the existing provider and device permissions. No biometric recognition is implied.

User explicitly requested autonomous implementation and deployment repeatedly; do not reopen design approval.

- [x] Read actual installed source and native report rather than assume the addon version proves feature activation.
- [x] Preserve deployed agent/runtime/memory/awareness/turn-taking sources in this repository.
- [x] Exercise conversation continuity, principal isolation, restart persistence, guest introduction, forget, joke filtering and observation timing.
- [x] Independent review: found guest household writes bypassing session-only policy.
- [x] RED: guest household persistence regression fails on deployed source. GREEN: require verified principal for durable shared notes.
- [x] Run complete 159-test repository suite, 19 companion tests and 6 diagnostic tests.
- [x] Activate the reviewed fix and read fresh native startup report: companion_ready at 14:53 Europe/Prague.
- [x] Prepare source and verification record for synchronization to feat/jarvis-addon.

Limits: no voiceprint database yet, no physical-microphone/subjective humour test. Unverified voice guests cannot retrieve personal durable notes. Observations are conversational only, never automatic announcements. A non-smart stove remains unobservable. Speech barge-in is not implemented.

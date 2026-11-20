# Voice diagnostics implementation plan

Goal: observe the actual local dialogue without changing microphone, TV, identity or command behavior.
Architecture: a bounded per-run diagnostic timeline shared by Session and TurnBridge, written into the existing private 0600 report. Native pipeline events cannot expose internal turns; do not fabricate missing wake-word or acoustic timing.
Scope: approved plan step 1 only. Native 1.3.7 is the live baseline; permanent half duplex remains unchanged in this step.

- [x] Add regressions for per-turn transcripts/timings, empty STT, provider errors, cancellation, bounded memory, observer failure isolation and silence/source termination.
- [x] Implement bounded runtime traces, instrument actual bridge awaits and session capture/output/termination. Record TV acquire/release and known activation metadata. No raw microphone retention, response text or exception messages.
- [x] Run local-duplex and voice-diagnostics suites, source checks and review. Publish exact source against fresh remote HEAD.
- [x] Read fresh live files, compare baseline, acquire deployment lease, prepare backed-up CAS bundle, activate, poll same job, read back files/runtime. Keep microphone muted. Release lease.
- [x] Verify generated-only diagnostic probe locally and on Green; actual household acceptance requires a later explicit test.

Review focus: repeated turns must not reuse timings; unknown wake-word stays unknown; empty STT and errors remain distinguishable; cancellation records termination; observer failures must never affect household actions. Private transcripts never enter Git.

Verification boundary: generated-only native readiness passed; actual acoustic acceptance remains pending. Source/evidence and known unrelated CI runner failure are recorded in docs/evidence/2026-11-04-voice-diagnostics-active.json.

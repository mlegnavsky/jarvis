# Natural complete light utterances

**Goal:** Listen to the complete command, preserve named-room suffixes, never announce pending state for accepted light actions, and ignore standalone command detections while television/audio is active.

**Architecture:** Acoustic verbs become activation hints for native STT with a bounded initial continuation window. Native VAD ends a real utterance; the original verb is supplied only when the captured suffix lacks one. An explicit spoken verb overrides the acoustic hint. A silent continuation window permits the bare hint; ambiguous/failed captured speech never falls back to the current room. Existing local resolution/grants execute the completed command.

**Constraints:** Keep the existing light-only public policy and locks protected. No raw recording or private model publication. Ordinary explicit Jarvis activation remains the path while TV is on; generic Hey Jarvis disabled. Backend states are observations, never a spoken success claim.

- [x] Reproduce silent accepted actions and complete child-room commands with failing regressions; add request politeness forms.
- [x] Replace immediate dispatch with complete-utterance native capture; test bare silence, room suffix, opposite explicit verb, garbled continuation, cancellation and known TV states.
- [x] Prevent suppressed activations from pausing TV or opening follow-up conversations. Retain bounded read-only action observations.
- [x] Run all relevant suites and an independent review, publish with current HEAD, deploy with CAS/private backup, verify loaded code plus real room/service behavior. Preserve latest three/protected backups during necessary one-backup cleanup.

Physical acceptance includes the owner's actual microphone and TV; simulated audio does not prove acoustic discrimination.

Independent review found two P1 defects: weak identity-VAD measurements could incorrectly allow a bare fallback after real native continuation; suppressed events could still cancel an owned HomePod answer through routing.activate. Both were reproduced RED and fixed GREEN. Bare fallback now requires an explicit consumed-audio silence deadline AND no native VAD_START; provider no-text, stream disconnect and low identity probability cannot establish silence. Routing and session ownership both ignore suppressed runs.

Verification:61 companion,154 identity,18 diagnostic,53 HomePod and244 addon tests (224 passed/20 skipped). An additional probe runs actual pinned Core2026.6.4 PipelineInput execute/validate, native VAD and STT stream, custom turn/identity adapters, real Coordinator/VoiceGate/CompanionRuntime and actual agent methods. Fake provider/device boundaries cover full child suffix, conflicting acoustic hint corrected by transcript, bare silence, unintelligible speech and TV-on suppression; every accepted action is silent, no LLM/TTS. Physical API off/restore probes of living and child lights both verified; state confirmation arrived140–141ms after the service response. No microphone recording was enabled. Secondary generic Hey Jarvis selector was disabled with readback; private Jarvis remains enabled.

Activation verified: natural-utterance-apply active_verified,27 exact files, native six-case VAD probe passed, actual child-room resolution passed. Private wake cutoff restored0.8→0.98 using unchanged weights; native firmware install verified with online matching hash1312060e. Secondary generic wake remains disabled. Leases released; post-update acoustic household/TV acceptance remains explicitly pending.

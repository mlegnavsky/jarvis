# Fast silent light commands

> **For agentic workers:** Use superpowers:executing-plans; run the regression tests before and after each change.

**Goal / spec:** Martin requests immediate execution of simple rozsvit/zhasni commands without repeating the task. Existing public-light authorization, room scoping and silent successful replies remain the contract.

**Architecture:** Extend the existing pure parser to recognize STT infinitives. Route the two already installed acoustic light detections into the existing native intent handler, skipping STT. Preserve its single-use grants and exposed-room resolution; never introduce another device executor.

**Tech stack:** Python, HA Core 2026.6.4, native Assist PipelineInput.

**Global constraints:** No Core/OS upgrade, no voice-profile changes, no recording. Only lights may use acoustic direct execution. Keep ordinary wake words and button input delegated. Publish with expected HEAD and deploy with revisions, private backup and one Core restart.

**Review focus:** Quoted/conditional examples must not execute; missing coordinator must fail closed; replayed detections must be suppressed; background learning/training must not become authorization; direct runs must close the microphone and native lifecycle even on errors.

## Task 1: Recognize actual STT light commands

Files: managed_sources/voice_common/__init__.py; managed_sources/companion/test_room_commands.py; managed_sources/speaker_identity/test_public_controls.py.

- [x] Add failing regressions for Rozsvítit světlo v obýváku, Zhasnout světlo and explicit Zapnout/Vypnout světla, retaining rejection of quoted and conditional examples.
- [x] Run both component suites and observe the missing parser behavior.
- [x] Normalize only leading light verbs; preserve target scope and the exact grant contract.
- [x] Run companion and speaker suites; all pass, including bounded optional identity inference.

## Task 2: Restore immediate direct light commands

Files: managed_sources/voice_diagnostics/direct_wake.py and test_direct_wake.py; component manifests/reports and deployment evidence.

- [x] Add failing tests for native intent-only execution, STT input closure, exact light-only scope, training/unavailable guards, duplicate cooldown and errors.
- [x] Route exact matching satellite/pipeline acoustic words through the existing public-light coordinator and native intent stage. Emit the native stop-audio event; preserve run-end and cleanup. Do not use LLM or embedding inference.
- [x] Run diagnostics, companion, identity, HomePod and addon suites plus manifest check.
- [x] Obtain one fresh code review; publish Git changes with expected HEAD. Review found cancellation before native start and optional-backend coupling; both fixed with RED/GREEN regressions (21 diagnostic tests; 56 companion; 152 identity; 51 HomePod; 244 addon tests with20 skipped). Actual pinned Core execute/validate methods plus real grant and room handler also passed in simulation, without STT/inference/TTS. Native intent-guard/adapter identity is required independently of embedding backend health.
- [x] Free only one old unprotected backup under the owner's accepted keep-three/protected cleanup, if needed; acquire lease, prepare/apply a revision-bound bundle, verify runtime/source/native resolution and release lease. Record acoustic acceptance as unmeasured until a real household command.

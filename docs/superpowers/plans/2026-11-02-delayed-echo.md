# Delayed echo stability implementation plan

> For agentic workers: execute inline with superpowers:executing-plans and TDD; one fresh whole-change review.

Goal: reject delayed generated speech across longer conversations while retaining independent human turns.
Architecture: bounded tolerant generated-text fingerprints and consistent completion-tail lifetime; existing acoustic gate, Session confirmation and authority stay in place.
Tech stack: Python, existing HA2026.6.4/HomePod path.
Spec: docs/superpowers/specs/2026-11-02-delayed-echo-design.md

## Global constraints
No failed AEC, new recording, voice/profile/firmware/Core/model/provider/volume change. Do not claim full acoustic resolution or1s. Preserve human Ano/Ne/Stop and negative/quoted commands. Source publication/deployment remain owner-authorized, including named public repository.

## Review focus
- Independent speech-like envelope shapes must not lock simply because broad search finds one similar syllable.
- Clock rollback, changing lag and constant/silent reference remain uncertain, not positive echo.
- Normal output completion preserves a delayed own question without swallowing independent replies.
- ASR variation rejection stays inside generated-speech intervals, with bounded text work and no persisted words.
- Source EOF closes owned output and never automatically starts another microphone capture.

## Task1: acoustic timing and lifetime
- [x] RED: observed+1.25s lag through real PCM, three-window consistency, independent speech-like seed, human mixed/short input, completion tail.
- [x] Reject wider envelope classifier after meaningful independent-speech negative failed; revert it. Keep only consistent completion-tail lifecycle in ha_io.py/homepod_io.py. Original acoustic gate unchanged.
- [x] GREEN full duplex; no simulated acoustic-success claim.

## Task2: transcript variants and attribution
- [x] RED: one ASR insertion/deletion/substitution in generated4+word phrase; human corrections/short replies/post-playback negatives; scalar facts bounded and contain no words.
- [x] Implement text_echo.py and LocalOutput scalar diagnostics without changing voice/service authority.
- [x] GREEN duplex/identity/companion/diagnostics/addon, manifest/diff; one whole-change review and one material RED/GREEN fix pass.

## Task3: reviewed activation
- [ ] Publish with fresh expected public HEAD, verify CI, backed-up CAS activation, fresh source/native probe/output and mic checks, release lease.
- [ ] Record source and runtime proof, keep long-room acceptance and latency open until actual user evidence.

## Ledger
Base local a9a50d8 matches publicf019ac24a33d5e32c2ff68d70da3433ba7763cfe tree8726d73617b2b29d0bb112e29ea5173d56b4b727. Runtime1.2.5/source604e6b84. No product modifications from latency research. Long-conversation failure supersedes earlier short-story acceptance. The last EOF reason is known but its external cause is not: no speculative auto-rearm.

Wider RMS alignment passed random-block fixtures but failed independent speech-like negative; not shipped. Native AEC3 experiment in/tmp/aec3-feasibility-voiced also not deployable: nine3s cases failed,10s near-tail human preservation failed, including matched near-only processor baseline and native8ms delay. No threshold relaxation or backend deployment. Root repair adds first-token-anchored ASR edits, protects negation/control positions, extends current tail policy to normal completion and reports scalar causes. Final169duplex pass so far. Remaining acoustic reliability and10s latency stay open.

Whole-change review: three material issues independently RED/GREEN in one fix pass (opposite command aliases, protected-word DP base cases, repeated32-row telemetry breaking128KiB report). Final172duplex pass independently, no remaining Critical/Important/Minor. Retained turn records now store latest1guard row while top-level output keeps32. Original telemetry composition210496B, corrected36896B in review reproduction. Review also compared bounded DP against full reference without mismatch. Pathological64word/2000reference benchmark median39.1ms/max49.97ms on executor; not a Green CPU claim. Room reliability and latency explicitly remain unverified. No raw recording permission has been found; do not arm recording without explicit owner consent.

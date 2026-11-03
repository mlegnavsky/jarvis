# Waveform Native Kernel Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans inline; fresh review of the new hardware-performance diff only.

**Goal:** produce usable bounded similarity on Green using its existing native audio kernel.
**Architecture:** audioop.findfactor supplies vector dot; preserve Pearson normalization and a Python fallback. No recording or input decision changes.
**Tech Stack:** Python; existing Core2026.6.4 audioop-lts0.2.2, no new dependencies.
**Spec:** docs/superpowers/specs/2026-11-03-waveform-native-kernel-design.md

## Global Constraints
400ms/500Hz/+/-2000ms/2001positions/25ms/1Hz/onepending/eightscalar rows unchanged. Runtime1.2.8. Native short proof is not room/full-search/1s acceptance. Existing owner authorization covers diagnostic software deployment, not recording.

## Review Focus
- Native fit factor must become centered normalized correlation; DC/quiet windows must not become false certainty.
- Missing native kernel must stay a bounded fallback without blocking input.
- PCM quantization/endian/near-limit values must stay valid and not overflow.
- Final deadline and null margin safeguards must survive optimization.
- Generated-reference proof must succeed on Green; host performance alone is insufficient.

### Task 1: native vector dot and target activation
Files: waveform_observer.py/test_waveform_observer.py; __init__.py/manifest.json version; evidence/OPEN-WORK.
Interface measure_waveform unchanged; add scalar kernel name. Existing async observer unchanged.
- [x] RED native-kernel availability, native/fallback parity under gain/DC/inversion and near-limit variation; keep all192existing regressions.
- [x] Implement PCM16 quantized Pearson dot through existing findfactor with bounded Python fallback.
- [ ] GREEN full relevant suites and fresh follow-up review; one material RED/GREEN fix pass if needed.
- [ ] Publish expected HEAD/exact tree, CI; space/retention/lease; backed-up CAS1.2.8; native generated-reference proof, source/fixed output/mic/receipt/release.
- [ ] Record usable native facts; real-room acoustic solution and latency still OPEN.

## Ledger
Base reviewed1.2.7 a91c4a6e875a31bf5ad98243fc5db133c8d9c9a4. Operator wave127-apply verified05:16:12UTC/backupcf7385ba. Native selftest passed, waveform budget exhausted288/25.223ms. Original plan's operator goal remains incomplete pending this follow-up. Core pyproject dependency was read from exact2026.6.4 tag; do not install anything. Execution method and diagnostic scope remain owner-delegated.

195duplex GREEN (3new native/DC/gain/inversion/near-limit regressions first RED), manifest/diff GREEN. Native/fallback are mathematically checked; actual Green result remains mandatory. Follow-up review pending.

Fresh follow-up review a91c4a6..5d37574: Critical0/Important0/Minor0. Independent195GREEN and manifest/diff passed.2500near-limit pairs compared with exact-integer Pearson: maxabsolute deviation1.04e-6. Actual import failure fallback tested to2001positions/1250ms and budget exit. Host20native probes all measured2001positions, median4.2975ms/max6.903ms; still not ARM proof. Root owns native generated-reference/installed-kernel/source/CI/CAS/output/lease verification. Short native proof does not establish full2001worst-case or room separation/clock/latency. No general big-endian hardware claim; current Green target is little-endian. No re-review of prior1.2.7 changes and no new source modifications after this review.

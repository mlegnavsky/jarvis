# Waveform Observation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans inline in the existing isolated worktree. A fresh whole-change reviewer follows the complete implementation.

**Goal:** obtain bounded raw-waveform similarity facts for the owner-confirmed autonomous stops without changing input or saving audio.
**Architecture:** a pure CPU-bounded standard-library probe runs in the HA executor at most1Hz; PlaybackObserver retains scalar results only. Existing Session and acoustic/text decisions remain unchanged.
**Tech Stack:** Python, existing HA2026.6.4/Core executor.
**Spec:** docs/superpowers/specs/2026-11-03-waveform-observation-design.md

## Global Constraints
- Existing source52c151f9/version1.2.6 is not acoustically accepted; owner confirmed3autonomous stops.
-400ms PCM16/16kHz microphone window,500Hz averaged samples, +/-2000ms search,2001offset maximum/400200products,25ms cooperative worker deadline checked every16offsets.
- At most1job/s and1outstanding job;8scalar result rows; no PCM/text in reports or files, no new capture, input decision or authority change.
- Same HomePod/volume/Marin/provider/model/firmware/Core/profile; no failed AEC or wider RMS deployment. Runtime1.2.7 is diagnostic only.

## Review Focus
- Human speech with a similar RMS envelope must not be labeled echo by this measurement.
- Executor delay/errors/cancellation must not block or alter incoming audio.
- Silence, invalid timing, periodic ambiguity and budget expiry must stay explicit, not become positive evidence.
- Reference changes and session close must clear private rolling audio; snapshots stay scalar/bounded.
- Incoming burst boundaries and source exceptions must remain identical to the unobserved stream.

### Task 1: pure waveform measurement
Files: create managed_sources/local_duplex/waveform_observer.py and test_waveform_observer.py; modify segmenter.py to retain only the immutable private reference PCM alongside existing levels.
Interface: measure_waveform(microphone:bytes, reference:bytes, *, played_seconds:float, clock=perf_counter)->dict of scalar facts. Existing EchoReference.is_echo unchanged.
- [x] RED known1250ms PCM delay, independent waveform/same envelope, constant/silent/short, invalid timing, deterministic budget, periodic peak margin, bounded scalar result.
- [x] Implement the exact bounded mean-centered correlation/normalization described in the spec, no acceptance threshold.
- [x] GREEN10probe tests;20host-only probes all measured1250ms, median11.6145ms/max15.967ms/2001comparisons. Not a Green CPU claim.

### Task 2: optional nonblocking integration and activation
Files: modify playback_observer.py, __init__.py, manifest.json, test_playback_observer.py and test_homepod_io.py; native version1.2.7. Add owner-failure attribution to prior evidence and OPEN-WORK.
Interface: PlaybackObserver(read_output, *, clock=monotonic, run_executor=None). Native LocalDialogue supplies hass.async_add_executor_job; existing default observers remain valid without a worker.
- [x] RED actual worker yields delayed match while preserving original chunks; blocked executor does not block reader; worker exceptions/cancel/reference switch close cleanly; scalar retention/report budget and original exceptions. Invalid receive time and native operator waveform proof separately RED/GREEN.
- [x] Integrate private400ms ring, >=1s scheduling and one pending worker; cancellation consumes errors; snapshots never serialize private audio. Optional native probe uses generated reference only with500ms executor wait timeout and cannot fail voice readiness.
- [x] GREEN full duplex/companion/identity/diagnostics/addon, manifest/diff; one fresh whole-change review and targeted fix pass if needed.
- [x] Publish exact reviewed tree with expected public HEAD, check CI; fresh storage/backup/lease preflight; CAS backed-up activation; source/native probe/fixed output; receipt/readback/release. Persist private short lease token outside Git before acquisition.
- [x] Record diagnostic-only runtime proof; ordinary-room waveform evidence and complete acoustic/latency fixes remain OPEN.

## Execution ledger
Existing user authorization covers diagnosis/software deployment, not recording. No raw recording consent inferred. Existing native arm_capture was inspected read-only: native _speech_to_text_stream calls _capture_chunk; local path uses process_enhance_audio directly and bypasses that call. Do not enable a recorder that would miss the relevant stream. Current work selects in-memory scalar observation instead. No new suppression architecture is being approved or deployed in this plan.

Software verification before whole-change review:190duplex/83companion/154identity/30diagnostics/242addon(20skipped) GREEN; manifest/diff GREEN. Companion emitted one asyncio slow-task debug notice under concurrent test load; no test failure. New observer integration tests first failed6missing-executor assertions; invalid-clock bug then separately RED1scheduled versus0expected before finite-clock guard; native probe separately REDmissing waveform_probe before actual measurement/optional-unavailable branch was added. Review and operator activation pending.

Whole-change review completed: Critical0/Important1deadline/Minor1margin. Missing-alternative margin re-graded Important because truthful diagnostic ambiguity is the feature's purpose; misleading certainty risks another wrong acoustic fix. Single RED/GREEN pass fixed final-block deadline (including late rollback/nonfinite clock) and returns null margin/alternative_count0 without a separated candidate. Full192duplex GREEN after the pass; no re-review. No deferred minors. Other local suites passed83/154/30/242(20skipped) before this isolated pure-measurement fix; source CI will re-run everything. Review's withheld acoustic/ARM/full2001worst-case/clock/natural-interruption/latency/activation judgments stay explicitly limited: measurement is not a fix; native short TTS probe is not a full-search or room benchmark; absolute delay is uncalibrated; root verifies actual activation and device/job receipts separately.

Actual1.2.7 activation wave127-apply-20261103 verified05:16:12UTC/backupcf7385ba, but native waveform proof exhausted25ms after288comparisons (25.223ms). Host performance did not transfer; evidence docs/evidence/2026-11-03-wave127-green-budget.json. A bounded follow-up uses Core's existing native audioop kernel without dependency/Core changes: docs/superpowers/plans/2026-11-03-waveform-native-kernel.md. Its separately reviewed1.2.8 activation and target short proof passed,195duplex/sourceCI green, source/fixedoutput/receipt/release verified. This closes the diagnostic deliverable through that follow-up, not a claim that1.2.7 itself met target timing. Latest0frame session was blocked by unavailable Apple TV; isolated integration reload restoredloaded/playing without Core restart. Evidence docs/evidence/2026-11-03-waveform128-native-verification.json. No real1.2.8 acoustic waveform sample yet; owner-confirmed1.2.6 room failure is still authoritative for the unsolved user goal. No microphone recording enabled or input decision changed.

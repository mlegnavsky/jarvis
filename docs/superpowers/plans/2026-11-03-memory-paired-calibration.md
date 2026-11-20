# Memory Paired Calibration Implementation Plan
> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans inline; one fresh whole-change review.
**Goal:** obtain actual paired room source diagnostics without persisting or exporting audio.
**Architecture:** optional existing-source tap; bounded mutable PCM inRAM; generated reference prefixes; on-Green analysis after sessionclose; only scalar report on disk.
**Tech Stack:** Python stdlib/audioop, optional existing NumPy; same HA2026.6.4.
**Spec:** docs/superpowers/specs/2026-11-03-memory-paired-calibration-design.md
## Global Constraints
One fresh120s arm,30s mic/3MiB retainedPCM/150s maximum hold/30s cooperativeanalysis. Defaultoff, durable nonceconsumption/restartoff. No newmic/wake/input/authority/provider/model/volume/firmware/Core change. Runtime1.3.1.
## Review Focus
- Consent nonce replay after restart must never rearm recording.
- Raw/enhanced chunk boundaries, source errors and timing must remain unchanged.
- False barge-ins replacing owned answers must not truncate this diagnostic's evidence.
- Failure/close/expiry/cancel must erase all retained PCM without audio files, exports or backups.
- Analysis ambiguity/lowenergy/budget exhaustion must stay explicit and never gate a human voice.
### Task1: bounded memory capture, analysis and native activation
Files: create calibration.py/calibration_analysis.py and tests; modify playback_observer.py/control.py/__init__.py, small reference-prefix helpers in segmenter.py/speech_stream.py, manifest.json1.3.1 and tests.
Interfaces: CaptureData holds mutable raw/enhanced/ref PCM with reprhidden and wipe(); Recorder.observe_raw/observe_enhanced/finish preserve nominal indices and read-only output snapshots. CalibrationManager.arm(nonce,expires_at),attach()->Recorder|None,finish(recorder),snapshot()/close() own state, expiry, one backgroundanalysis and scalar persistence. analyse_capture(data,clock=perf_counter)->JSON-safe facts with no PCM/complex/spectralarrays.
- [x] RED fixed30s/3MiB limits, phase alignment, outputreplacement, sourceclose, silence/nonfinite timing, snapshotprivacy and mutablebuffer wipe.
- [x] Implement Recorder/CaptureData and safe scalar-only nonce/result store; RED/GREEN defaultoff, oneclaim/expiry/restartreplay, analysisfail/cancel/holdexpiry.
- [x] RED known generated delay/gain/filtered and independent same-envelope diagnostics, FFTfallback parity/coherence, ambiguity/budget; implement pure analyzer with no classification threshold.
- [x] RED/GREEN optional observer taps preserve exact bytes/boundaries/errors and existing audio decisions; fresh <=120s capture controls, no recording by probes/operator playback, native-generated analysis proof.
- [x] Full duplex/affected suites, manifest/diff; one fresh review and one material RED/GREEN fix pass.
- [x] Commit/publicexpectedHEAD/exacttree/CI; short privatelease/space/retention/backed-upCAS; exactsource/nativeVAD/TTS/analysis/idle-state verification; arm once only after proof.
- [ ] Owner normally wakes assistant: quiet first20s of requestedstory, then one human “přestaň”. Read actual private scalar results, verify zero retainedPCM, decide next acoustic change from evidence.
Expected commands: PYTHONPATH=managed_sources/local_duplex python -m unittest discover -s managed_sources/local_duplex -q; python scripts/check_manifest.py; git diff --check. Software pass is not room acceptance.

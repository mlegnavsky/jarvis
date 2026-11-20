# Streamed HomePod Speech Implementation Plan
> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans inline. One fresh whole-branch review also covers the adjacent acoustic verifier plan.
**Goal:** begin the same HomePod answer before whole TTS completes.
**Architecture:** one existing OpenAI MP3 response, bounded blocking IO forks, public RAOP and miniaudio; bounded growing reference and generation-owned cleanup.
**Tech Stack:** existing Core2026.6.4, pyatv0.17.0/miniaudio/AsyncOpenAI; stdlib queues/threads.
**Spec:** docs/superpowers/specs/2026-11-03-streamed-homepod-speech-design.md
## Global Constraints
90s PCM/8MiB compressed/256KiB pending per reader/5s stalls;400ms nonsilent reference before playback. Same provider/model/Marin/prompt/speed and current output/authority/TV controls; no recording or firmware/Core change.
## Review Focus
- Cancellation before first byte/decoder init must unblock every blocking reader and release exact playback.
- Producer failure/oversize/duration/stall must not become a normal EOF or duplicate TTS fallback.
- Reference and actual output use the same compressed response with valid sample-time alignment.
- Delayed former workers cannot mutate a new output or cause speaker busy leaks.
- Deliberate volume0/mute, external playback and TV changes retain current semantics.
### Task1: streamed response and output integration
Files: create speech_stream.py/test_speech_stream.py; modify homepod_io.py,segmenter.py,__init__.py,tests and manifest.json1.3.0.
Interfaces: SpeechStream exposes native IO, reference, duration bound90s, ready waiter and async release; factory(text) is injected into HomePodOutput. Existing fixed self-test synthesize stays unchanged.
- [x] RED bounded blocking read/seek-head, stalled/error/EOF distinction and close wakeup; one response forks to real decoding, ready before producer EOF, complete sample count and cancel before/after init.
- [x] Implement minimal stdlib fork and miniaudio reference decoding in speech_stream.py; generation-owned publicstream_file wrapper and growing EchoReference in HomePodOutput.
- [x] RED/GREEN same official entity/client/options resolution; exactHomePod/volume/busy/cancel integration, no per-sentence reconnection and no raw PCM in report.
- [x] Run full duplex plus affected companion/identity/diagnostics/addon suites, manifest/diff, one fresh whole-branch review/fix pass.
- [x] Commit, expectedHEAD/exacttree public Git and CI; lease/storage/retention/backed-upCAS; native streaming/reference/source/fixedoutput proof, receipt/readback/release.
- [x] Record measured native first-audio/producerEOF facts and remaining room/latency limitations.
Expected commands: PYTHONPATH=managed_sources/local_duplex python -m unittest discover -s managed_sources/local_duplex -q; python scripts/check_manifest.py; git diff --check. All pass before publication. Hardware/physical outcomes require actual target evidence.

Software206duplex/154identity/83companion/30diagnostics/242addon(20skipped)pass; manifest/diffpass. Freshreview Critical0/Important0/Minor1(nonblocking stale cleanup diagnostic flag deferred). Host actual publicnative source843.1ms beforeproducerEOF2470.4ms, reference/nativeexact, readers0. No Green/room success inferred. Acoustic adjacentcandidate was rejected1/15roomfilteredpositives; no acoustic veto is wired. Native publication/activation pending.

Activation closed: public6b94da8f5c1475f0d8a3f1d8e6cc2e87b2483a36/tree3d6d517b1314852f48dc145be8db72a93260eff7 equals local7aa5236; CI41589800453push/41589805119PR/lab125764115706success. stream130-apply-20261103 verified06:32:41UTC/backup9edc3711,4/4freshfilesexact/runtime1.3.0/sourceca5a6fc62ce3ab6f9162da042b059dcf0b330ace19202e9b8e2df91e6fa2a781. FreshnativeVAD/TTSsourceproofpassed. Actual streamedHomePod output1start1complete0stop0skip/noerror/cleanup0,17.376sMP3 decodedreference, firstreference2395.4ms/first-readyawait2405.6ms/nativefirstaudioestimate2062ms/HTTP EOF3728.2ms. Own5%unmuted preserved. No ordinary agent/STT latency or physicalaudibility/room proof inferred. Native sender firstpacket estimate2967.6ms fromTTSstart precedesHTTP EOF; firstaudible senderestimate4467.6ms. TVavailableplaying/micoff-mute/satelliteidle, captureexpiryNone and interruptionsenabled. Receipt exactreadback9ec011e0fcbe538f24bcc1f20a3a09fa8ec2cd65916f02902733135bfdc802af. Leaserelease verified06:39:20UTC/freshlockedfalse/tokenremoved. Evidence docs/evidence/2026-11-03-stream130-native-verification.json. Acoustic fix/calibrationrecording consent remainOPEN; proposal is not an armrequest.

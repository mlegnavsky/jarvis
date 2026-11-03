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
- [ ] Commit, expectedHEAD/exacttree public Git and CI; lease/storage/retention/backed-upCAS; native streaming/reference/source/fixedoutput proof, receipt/readback/release.
- [ ] Record measured native first-audio/producerEOF facts and remaining room/latency limitations.
Expected commands: PYTHONPATH=managed_sources/local_duplex python -m unittest discover -s managed_sources/local_duplex -q; python scripts/check_manifest.py; git diff --check. All pass before publication. Hardware/physical outcomes require actual target evidence.

Software206duplex/154identity/83companion/30diagnostics/242addon(20skipped)pass; manifest/diffpass. Freshreview Critical0/Important0/Minor1(nonblocking stale cleanup diagnostic flag deferred). Host actual publicnative source843.1ms beforeproducerEOF2470.4ms, reference/nativeexact, readers0. No Green/room success inferred. Acoustic adjacentcandidate was rejected1/15roomfilteredpositives; no acoustic veto is wired. Native publication/activation pending.

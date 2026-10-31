# Voice diagnostics implementation plan

Goal: identify STT accuracy/latency independently of microphone capture and preserve bounded local evidence of actual satellite runs.
Architecture: one YAML-loaded HA custom integration, no physical commands, no microphone audio uploads by diagnostics; fixed synthetic references may use the pre-existing OpenAI STT. Use existing local Piper and STT entities for a known-phrase test; inspect HA 2026.6.4 pipeline debug events and native temporary WAV capture. Store bounded sanitized reports outside www.
Tech stack: Python stdlib, installed HA STT/TTS/ffmpeg/assist_pipeline APIs.

- [x] Test-first pure analysis: PCM format/silence/clipping, transcript word error, stage durations, missing-stage/timeout handling.
- [x] Implement native HA adapter: fixed test corpus through local Piper -> PCM -> Whisper/Speech-to-Phrase/OpenAI STT, no conversation execution. Serialize tests; cap 60s/engine and 15s/audio.
- [x] Monitor actual pipeline runs every five seconds; record queue/VAD/STT/intent/TTS and satellite playback times independently. Never label pipeline end as audible playback end.
- [x] Arm native capture for 15 minutes only; retain newest five WAVs/10MB, preserving full duration while bounding signal analysis to first20s and 20 sanitized runs. Fail closed on incompatible HA APIs. Persist report in jarvis_workspace/voice_diagnostics/report.json and summarize in sensor.jarvis_hlas_diagnostika.
- [x] Test full repository, compile sources, deploy revision-checked files, config check and restart Core once. Confirm integration health/report and run internal STT test. Select further fix only from measured evidence; report remaining acoustic test honestly.

Review focus: empty/truncated/unsupported audio; disconnected engine; cached TTS vs generated speech time; a five-minute HA run cannot be called complete prematurely; report contains no auth tokens/URLs or permanent audio recording.

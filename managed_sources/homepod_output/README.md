# Voice PE input, HomePod answer output

Install this directory as `custom_components/jarvis_homepod_output`, enable `jarvis_homepod_output:` and restart HA. Managed target is the existing living-room satellite and `media_player.homepod_obyvak_homepod_obyvak`, not TV/media groups. Guarded for HA 2026.6.4. Existing TTS voice/pronunciation and speaker identity are preserved.

The TTS-end event is held while the native Apple TV integration streams the original media source to HomePod via RAOP. The native entity method is awaited directly, so generic service-call limits cannot be mistaken for playback completion. Only after completion is a fixed 100ms silent WAV sent to the Voice PE. The real reply URL/token never reaches that terminal. Early streaming hints are suppressed. Speaker-only API firmware is rejected; the silent completion requires URL/media-player firmware mode.

Canceling the active pipeline stops the owned HomePod answer. Playback failures become native TextToSpeechError so HA emits its normal error and cleans the TTS stream. Cancellation/failure clears the pending follow-up window. There is no audible terminal fallback. Other pipelines/satellites and synthetic startup probes delegate unchanged. No startup playback, firmware flash, music group or volume changes.

Private report `jarvis_workspace/homepod_output/report.json` and `sensor.jarvis_hlasovy_vystup` show configuration/capabilities and playback counters. `configured` means metadata and routing are installed, not that anyone heard a physical test. The existing voice diagnostic TTS-stage duration now includes HomePod rendering/playback; it is not pure speech-synthesis latency.

## Interruption boundary

Stock Voice PE firmware detects a wake/stop word during replies and can cancel its pipeline; this patch propagates that cancellation to HomePod. Physical wake/stop behavior must be checked at home. Arbitrary human-speech interruption is NOT implemented: external HomePod sound is not in the terminal's acoustic echo-cancellation reference. Plain VAD would also hear Jarvis's own reply. HomePod routing or a prompt cannot fix this. Additional input/reference processing and acoustic tests are required before claiming it works.

The user explicitly deferred all audible/home tests until they say they are home. No announcement is emitted by this integration's setup or checks. Deferred checks: actual HomePod sound with silent terminal, correct follow-up timing, stop/wake-word cancellation, no echo loops and no speaker-identity regression.

Tests cover output scope, completion gating, interruption cleanup, native error conversion, streaming suppression and firmware URL mode. Native capability inspection is read-only. Reference sources: HA core 2026.6.4 assist_pipeline/pipeline.py, esphome/assist_satellite.py and apple_tv/media_player.py; stock esphome/home-assistant-voice-pe voice_assistant and micro_wake_word configuration.

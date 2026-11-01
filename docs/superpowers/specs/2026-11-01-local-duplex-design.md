# Local Voice PE speech interruption

The owner explicitly requested ordinary-speech interruption while the assistant speaks, asked for working prior art, and approved applying the proposed Voice PE speaker route. TV remains Apple TV/HomePod. This is a reversible targeted deployment, not a claim of perfected noisy-room activation.

## Evidence and approach

ramzes642/voice-pe-elevenlabs at22ec5c3690521a8bb1aad7a59408202f25401d92 documents real Voice PE microphone streaming throughout native media-player playback and about1.1s speech interruption. Its API-ownership firmware patches serve a second subscriber. Here HA already owns the connection: intercept only the configured PipelineInput.execute, retain its native audio iterator, and do not send STT_VAD_END/STT_END during the active dialogue. Independent announcements provide local XMOS playback reference. This needs a pinned-Core adapter, not a new subscriber or a blind firmware change.

Alternatives reviewed: Pipecat va_pipecat supplies simultaneous PCM but replaces provider/authorization paths; generic esphome-aec needs different reference hardware/Core changes; Tristan realtime currently disables ordinary-speech interruption. External AirPlay lacks a proven synchronized echo reference. Our call: preserve the existing STT, conversation agent, memory and authorization, and render its existing TTS locally.

## Boundaries

- HA Core2026.6.4; existing ESPHome2026.10.1 unchanged. Only Jarvis pipeline01kw4sat65taw1y72xzrv2xyj4 and satelliteassist_satellite.home_assistant_voice_0a8bde_assist_satellite.
- Outputmedia_player.home_assistant_voice_0a8bde_media_player; no automatic fixed-volume or mute changes. Use native announcement STOP, including announcement=true, only for owned output.
- One active session; mic streams locally to HA while active. Existing cloud STT receives only completed human-candidate utterances. No new cloud provider, API credential export or24/7 cloud stream. No stored microphone audio; in-memory utterance<=30s plus bounded preroll.
- Local native microVAD stays running during generation/playback. On qualified speech onset cancel/drain the old response and stop owned playback while capture continues. No stale generated output may play afterward.
- Native local AEC supplies initial cleanup. A bounded envelope-reference correlation gate rejects own-playback candidates; synthetic echo/double-talk checks prove code behavior, not household acoustics. Report rejection/interruption timing without claiming TV rejection is guaranteed.
- Fresh STT PCM goes through existing speaker coordinator complete(context_id) and existing conversation.extended_openai_conversation with the same device/context. Public silent lights, protected lock/profile operations and private memory remain authoritative. No direct LLM-to-service path.
- Whole utterances preserve room suffix; add observed child-room diminutives only against the registered Dětský pokoj name.
- Preserve physical mute/button and EOS cancellation. Owned TV pause uses existing fingerprint policy; user-changed TV is never resumed. Session cap240s/24turns, bounded empty follow-up after actual playback ends; continued speech can interrupt at any time.
- Other pipelines, synthetic probes and standalone light acoustic hints delegate unchanged. Unsupported interfaces fail closed to original behavior before any new session starts.

## Verification and activation

TDD for speech preroll/short answers/echo and double-talk, cancellation races, mute/EOS, bounded memory, target scoping, real agent context and announcement STOP. Characterize pinned native protocol (no VAD_END means microphone stays streaming during independent playback) before deploying. Test callback wiring against actual pinned Core on Green without physical actions. Publish with expected HEAD, CAS/backed-up deployment and runtime version check. Then report actual overlapping microphone/playback observations and a physical interruption test; never infer audibility/acoustic acceptance from unit tests.

Rollback is the deployment before-image plus disabling/removing this domain; all legacy hooks remain installed and delegate normally for unrelated runs. No Core/OS upgrade or firmware replacement.

Activation removes the previous jarvis_homepod_output YAML block, preventing competing routing and startup volume priming; its pure TVSession library remains installed. The fixed admin-only probe validates native VAD and synthesized reference format without opening a microphone. A separate fixed output_test speaks “Zkouška místního hlasu.” and verifies native playback state; audibility and acoustic interruption still need household observation. A stalled native audio source closes after five seconds.

Live1.0.1 integration: Core pins pymicro-vad1.0.1, which returns-1 until74feature frames are available. Prime only its VAD with bounded synthetic silence before consuming actual input, require finite0..1 readiness in the probe, and preserve the known sentinel as no speech. Initial reference gating retains original PCM/VAD frames rather than dropping them; short-speech onset remains80ms. Native device-local timers expose no announcement ownership ID: HA service targets are resolved, but timer replacement can still receive an owned STOP. Physical acceptance remains explicit.

# Voice PE microphone with HomePod speech

Binding owner correction2November2026: **HomePod speaks; Voice PE supplies microphone/wake.** This supersedes the earlier proposed Voice PE speaker route. No selected dialogue or fixed audible test may fall back to Voice PE speech. Keep the legacy jarvis_homepod_output domain and its two fixed-volume automations disabled; reuse only the pure TVSession library.

## Conversation

HA owns the existing Voice PE connection. Only pipeline01kw4sat65taw1y72xzrv2xyj4 and satelliteassist_satellite.home_assistant_voice_0a8bde_assist_satellite retain local microphone input throughout generation and HomePod playback. Completed utterances use existing STT, context-bound speaker coordinator, conversation.extended_openai_conversation, memory and TTS/Nova. No new provider or credentials, no idle cloud microphone stream, no raw microphone recordings. Utterance30s; session240s/24turns;8s followup after actual audio end. Silent light actions finish without speech. Existing public/control/profile/lock authority remains unchanged.

Unverified VAD onset cannot cancel STT/LLM/synthesis. During preparation keep at most latest1 completed utterance for5s; newer direct input erases older pending input. Truncated candidates never cancel output. Actual-playback speech onset cancels/drains old answer while microphone stays open; mute/EOS close owned work. Synthetic tests prove code behavior, not household source rejection.

## HomePod output

Exact targetmedia_player.homepod_obyvak_homepod_obyvak, using its existing HA AppleTV/pyatv0.17.0 connection. Decode the existing provider's16kmono16bit PCM, write a canonical complete local WAV in HA-configured local media and pass its local media-source URI to native AppleTV playback. Core resolves local media to a filesystem path, avoiding reproduced miniaudio InternetSource TTS decode failure. Generated-speech files only:4max/600s stale/0700directory/0600file, dirfd/no-follow, synchronized IO, release after success/failure/cancel/supersession and drain cancelled creation.

Restore the owner's existing startup45% policy once per HA startup through exact native RAOP Audio; then follow current owned shared-TV volume or native RAOP volume per answer. Later zero/mute remain silent; no end-of-answer restore and no fixed10%/45% automations. Busy native playback is not overwritten. Startup initialization is coalesced before eager task execution, including busy pre-write retries.

Own one native file-play task, await its full end and observe packets/context position plus negotiated latency. Scheduled playback start = monotonic clock - native position + latency/sample_rate. Preparation and AirPlay buffering do not count as audible playback or microphone overlap. The same PCM envelope reference supplies software echo gating; external HomePod does not supply a proven hardware AEC reference. Acoustic interruption and loud-TV wake require actual household evidence, never promise them from task completion.

Cancel/drain only the owned native file task: its RTSP cleanup addresses its own session. Never send a generic Stop to another protocol. Foreign HA playback relinquishes output and TV resume ownership. Pause only the current TV content for dialogue, resume only the same owned paused content, and respect external changes. This avoids coupled TV/HomePod volume rules and preserves programme position. Fixed HomePod output test closes/drains an active dialogue before running, rather than silently skipping it.

## Activation and verification

Core2026.6.4 and existing firmware/cutoff remain unchanged. New component Python requires CAS/backed-up activation. Verify targetHomePod and startup policy from live runtime, prime native VAD with bounded synthetic silence, and validate actual complete-file PCM. Then one HomePod utterance, ordinary question/followup and actual speech interruption; record physical results separately. No further native-speaker sound tests. Unsupported selected-route preparation closes through native RUN_END without local spoken fallback. Other pipelines and existing silent acoustic light hints retain their existing handling.

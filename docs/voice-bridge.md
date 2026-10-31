# Voice bridge (3.9.0)

Voice maintenance uses the existing Jarvis OAuth connection and maintain scope. No browser login, device encryption key, arbitrary URL, shell, or raw microphone stream is added.

Use the dedicated `jarvis_voice` tool with `request_id` and `data`. Existing clients can use `jarvis_action` with `service=jarvis.voice`, `entity_id=jarvis.system`, the same `request_id`, and the same `data`.

Read operations:

- `{"action":"status"}` returns fresh allowed voice entities, state, available options, numeric ranges and player volume.
- `{"action":"diagnostics"}` returns bounded timing summaries, capture expiry and output status without transcripts/audio. Missing reports return partial availability.
- `{"action":"pipelines"}` returns configured speech providers/pipelines.

Changes use `{"action":"change","entity_id":"...","service":"...","data":{...}}`:

- `select.select_option`: `option` must be in the target's current options. Covers pipeline selection, wake words, sensitivity and finished-speaking detection.
- `number.set_value`: `value` must match the current finite device range and step.
- `switch.turn_on` / `switch.turn_off`: empty data; only explicitly listed targets such as microphone mute or wake sound.
- `media_player.volume_set`: finite `volume_level` from 0 to 0.8. HomePod automatic speech volume remains persisted in `jarvis_homepod_output.speech_volume` via existing config/restart maintenance; immediate player volume does not change that persistent setting.
- `media_player.media_stop`: empty data.
- `tts.speak`: short `message` (1–200 characters) and separately allowed `media_player_entity_id`, using an explicitly allowed TTS entity. Satellite `announce` is also supported but not enabled in the household allowlist: normal speech remains on HomePod.
- Target `jarvis_voice_diagnostics.system` can invoke `jarvis_voice_diagnostics.run_self_test` or `run_companion_test` with empty data, only when requested.
- `jarvis_voice_diagnostics.arm_capture` additionally requires `{"confirm_recording":true}` and explicit user authorization. The installed diagnostics component limits local recordings to 15 minutes, five clips and 10 MiB. Reading status never records audio. No recording files are exposed by this voice endpoint.

Both target and service must be present in the existing explicit allowlists; no wildcard permissions are added. `jarvis_voice_diagnostics.*` requires maintain scope even through the generic action route.

Each change reserves its durable idempotency key before side effects. Reuse the same request ID after an uncertain result. `accepted` is not a physical result; `target_state_verified` checks a fresh observed setting and `replayed=true` describes historical verification. Announcements and diagnostic jobs are accepted without claiming audible completion or successful recognition.

Provider/model/voice changes continue to use the existing native integration options/subentry flows. They expose supported forms while protecting connection credentials. No Core/OS or Voice PE firmware update is needed for this bridge release.

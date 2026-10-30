# Jarvis Speaker — laboratory policy modules

Status: **not an installed voice assistant**. No changes to Home Assistant
Green. Run tests from repo root:

```
python -m unittest discover -s lab/jarvis_speaker -v
```

Implemented: selected wake phrase Jarvisi; 3s follow-up **silence** window;
separate 30s speech capture bound; interruption signal; per-utterance approved
profile permission; one-use command proof; stale identity/playback callback
rejection; TV volume snapshot/duck/restore with partial-error retry.

## Mandatory adapter contract before activation

- Only a trusted acoustic pipeline may call `wake`, `speech_started` and
  `voice_identity`. `source='human'` is an input assertion, not an implemented
  detector. Never expose these methods directly as public event endpoints.
- At speech onset call `speech_started` and retain `utterance_id`. Bind captured
  audio, identity verification and command to that ID. Pass it to
  `voice_identity` and `authorize_command`. Do not label late results with the
  controller's current ID. Only a True authorization allows dispatch.
- `approved_speakers` starts empty. Add IDs only after owner-approved local
  enrollment. Saying a name changes neither registry nor permissions.
- For each response, call `response_started`, retain `playback_id` and
  `session_id`, and pass the retained values to `response_finished` only after
  the output confirms playback ended. An interrupted output must really be
  stopped by the output adapter; the boolean alone does not stop HomePod.
- Start `VolumeGuard` once per conversation, not once per sentence; targets are
  actual TV/Apple TV audio sinks. End it on idle/error/cancel; retry failures.
  Persist pending snapshots in a runtime supervisor for restart recovery.
- Runtime callbacks must be serialized; add bounded processing/playback
  watchdogs. Keep TV ducked during follow-up; never pause video.
- Keep unknown-speaker chat separate from any device-enabled conversation
  agent. Emit `unknown_speaker_prompt` without executing or caching a command.
- Resolve default light room from trusted microphone mapping, never the
  claimed speaker identity. Add action audit records at actual dispatch.

## Remaining blockers

No microphone transport, wake acoustic model, echo cancellation, voiceprint
model/enrollment, STT/TTS runtime, HA/HomePod transport or room dispatcher is
implemented in this branch. No <500ms measurement exists. Text Jarvis does
not prove Czech-J pronunciation; verify with recorded TTS output. TV filtering
must pass an acoustic test, not just a source-tag unit test.

The public laboratory site is a release portal and explicitly says it runs
no full test Home Assistant. Available Jarvis connector currently exposes
status/inventory/actions/update, without lab shell, file deployment or voice
pipeline administration. Need an authenticated lab runtime and accessible
microphone/output test paths before implementation can be integrated and
reported as a working Speaker.

## Acceptance run on hardware

Use enrolled and unknown voices, mid-dialogue speaker changes, delayed
verification, TV words similar to Jarvisi, loud TV, HomePod echo, barge-in,
longer commands, follow-up on either side of 3 seconds, output errors and
restart during ducking. Record wake latency, identity latency (including audio
collection), stop latency and restoration of original volume. Unknown voice
must never execute an action, including after introducing itself.

# Anička — laboratory Speaker simulation

Status: **runnable offline simulation, not an installed voice assistant**. No changes to Home Assistant
Green. Run tests from repo root:

```
python -m unittest discover -s lab/jarvis_speaker -v
```

Implemented: selected wake phrase Aničko; 3s follow-up **silence** window;
separate 30s speech capture bound; interruption signal; per-utterance approved
profile permission; one-use command proof; stale identity/playback callback
rejection; TV volume snapshot/duck/restore with partial-error retry.

## Run Anička now in simulation

```
python lab/jarvis_speaker/simulation.py --demo
python lab/jarvis_speaker/simulation.py --persona
```

`--demo` runs six complete conversations and returns a JSON result and nonzero
exit code on failure. `--persona` exports the Czech feminine style prompt and
voice requirements for a future LLM/TTS adapter. The exact ChatGPT voice and
conversation memory are not transferred. The simulated replies are deterministic
fixtures, not a connected conversational model. Nothing is sent to Home Assistant.

The new default wake is **Aničko**, display name **Anička**. Jarvis remains the
backend name. Synthetic `fixture-owner` is solely a test identity; it cannot be
used as a voiceprint or approval on hardware. The registry still needs real local
enrollment and owner approval at integration time. No household identity data is
bundled in the persona. User-supplied names never enroll a speaker.

The simulator ties together real policy and VolumeGuard with in-memory lights,
TV volume, playback stop/completion, microphone-room mapping and a manual clock.
It models output/stop/volume failures, retries restoration, prevents stale callback
and transcript dispatch, and bounds simulated playback at 30s and sessions at 120s.
Those limits are lab defaults, not measured hardware latency. Error switches are
`output_available`, `stop_available`, and `volume_available`. No restart durability
is claimed. Only event types/IDs are traced, no raw audio or transcripts.

See [HOME_TEST.md](HOME_TEST.md) for the later hardware acceptance run.

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

The public laboratory site is a release portal, not a copy of Green. The offline
simulation does not require a running laboratory Home Assistant. Available Jarvis connector currently exposes
status/inventory/actions/update, without lab shell, file deployment or voice
pipeline administration. The remaining integration requires actual microphone/output paths and the
conversation/TTS/voice verification adapters before this can be reported as a
working Speaker. This is not evidence that existing access permissions are missing.

## Acceptance run on hardware

Use enrolled and unknown voices, mid-dialogue speaker changes, delayed
verification, TV words similar to Aničko, loud TV, HomePod echo, barge-in,
longer commands, follow-up on either side of 3 seconds, output errors and
restart during ducking. Record wake latency, identity latency (including audio
collection), stop latency and restoration of original volume. Unknown voice
must never execute an action, including after introducing itself.


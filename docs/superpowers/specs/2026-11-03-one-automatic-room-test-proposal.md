# One automatic room measurement — owner authorized

Status: owner explicitly approved one remote <=30s measurement on3Nov2026
(latest request5d44e702 “Ano souhlasim”). Implementation/native activation
is being verified; no microphone activation has occurred yet.
Existing30s RAM-only capture is ready for an already-open normal dialogue;
the newly approved fixed operator route supplies this one remote run.

## Exact proposed scope

- One exact satellite: assist_satellite.home_assistant_voice_0a8bde_assist_satellite.
- One fresh, durable, consumed32hex nonce;120s activation window; restart off.
- Record at most30s of16k mono microphone PCM and corresponding generated
  HomePod reference only in bounded RAM;3MiB retainedPCM/150s hold unchanged.
- Existing HomePod/current volume/Marin generates one fixed calibration
  passage. TV quieting/restore uses existing ownership rules. No agent,
  household commands, speaker enrollment or identity/authority changes.
- Use Core2026.6.4's supported AssistSatellite START_CONVERSATION protocol
  with a short generated silent announcement to start the existing native
  audio pipeline. Do not synthesize a wake word or use a hidden service proxy.
- A dedicated fixed operator capability must be implemented and reviewed
  through the normal managed-source/API path before activation. Current
  Jarvis policy neither supports nor allows assist_satellite.start_conversation;
  no policy workaround or general service allowance is authorized by this file.
- Stop the native stream/playback at the test deadline, on mute, external
  ownership change, HA stop or error; restore only owned state.
- Analyze on Green; no microphone audio export/cloud analysis/backup/Git.
  Wipe PCM after analysis/cancel/expiry. Persist scalar source/delay/error
  facts only. Any later room-model retention is a separate reviewed design.

## Why needed

Blind room-independent spectral matching accepted271/288 short human
mixtures as echo when covering own echoes; cross-fit FIR still accepted67/144.
Those methods remain undeployed. Actual paired room data is needed to
measure the path and evaluate a calibrated source model with held-out/mixed
controls, rather than raising a threshold that suppresses a person.

## What is already available

The bounded recorder, durable nonce guard, automatic on-device scalar
analysis, erasure and default-off lifecycle are deployed in local_duplex.
The exact Core2026.6.4 satellite implementation and service schema were read.
The missing scope is explicit owner permission and a fixed remote-start
operator route, not a request for the owner to be physically at home.

## Scope approved after authorized session fix was complete

Owner approved this one remotely initiated30s room test for this repair, with the
limits above. This is not permission for a persistent microphone listener,
general start_conversation proxy or recurring recording.

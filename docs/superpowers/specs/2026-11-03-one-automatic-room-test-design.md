# One automatic room measurement

Owner explicitly authorizes one remotely initiated <=30s room measurement
(3Nov2026 requests1f045f59 and5d44e702, latest “Ano souhlasim”). Nobodyhome;
software/publicGit/deploy authorization and inline execution persist.

Use fixed target assist_satellite.home_assistant_voice_0a8bde_assist_satellite,
Core2026.6.4 native START_CONVERSATION with generated200ms silent media.
No generic service proxy or policy allowlist expansion. A new fixed operator
control room_test accepts only action/nonce/expiry, <=120s; a durable global
one-shot claim blocks any second remote start, including new nonce/restart.
Prepare fixed Marin story and generated-only files before microphone start.
Use the existing private speech files and current HomePod volume.

A reserved per-nonce extra prompt binds the exact native pipeline. The
adapter's fixed target checks still apply. Operator runs are intercepted
before provider preparation; stale/unknown reserved prompts close locally.
No STT/LLM/identity/enrollment/household command from microphone. For this
operator path emit native RUN_START metadata without Core debug-recording
startup; existing native RUN_END closes the device, no PCM capture hooks.

The coordinator bounds start-to-close to30s, source stalls5s, preparation30s,
cleanup3s per owned stage. Capture raw/enhanced/generated-reference in the
existing3MiB collector, <=30s PCM and150s hold; analyse on Green when idle,
wipe on completion/error/cancel/expiry. No microphone audio serialization or
export. Stop on mute, externalHomePod/TV changes, HA stop and timeout. Stop
only the pipeline/task and playback owned by this measurement, clear prompt,
stop owned silent announcement, send native terminal event even on failure.

Existing dialogue behavior, input/identity gate, latency, Core/firmware,
provider/model/voice/profile remain unchanged. Measurement is not the echo
repair itself; scalar evidence determines the next eligible acoustic step.

Approaches: a generic start_conversation allowance would authorize unrelated
listening and is rejected. Synthesizing a wake word supplies no explicit
operator ownership and is rejected. Chosen fixed one-shot native operator
route matches the now explicit owner scope and stays off except that attempt.

Review amendment: routing before fallback applies to any pipeline for the
exact HA/satellite. Require exact active wrapper identity and Core before
start. Durable passive isolation is written before native transmission and
blocks all ambiguous/duplicate/late inputs independent of the consumed prompt.
It survives restart and remains until a fresh native entity is idle and its
original API client is disconnected. After this one test reload only that
satellite ESPHome config entry (<=30s cleanup, no new microphone start) to
flush old callbacks/audio before releasing isolation. This may locally close
a human activation during the finite test; a failed reset keeps privacy
isolation on until verified reconnection. TV release remains in finally.

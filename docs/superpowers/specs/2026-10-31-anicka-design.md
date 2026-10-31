# Domácí Anička — simulation scope

Approved in the 31 October conversation: prepare the assistant in simulation,
name Anička, wake phrase Aničko, warm feminine Czech speech. Jarvis remains the
home-control backend. No claim to transfer this ChatGPT session, its memory or
its exact voice. Preserve per-utterance approved profiles, immediate interruption,
three-second follow-up, and TV duck/restore. Hardware acceptance happens at home.

Implementation choice: extend existing Python controller, provide a standalone
deterministic simulator (no network or production transports), and export a
provider-neutral persona prompt for a future conversation/TTS adapter. The
simulator's canned replies demonstrate lifecycle, not general intelligence.
Simulated identities are explicit test fixtures, never enrolled voiceprints.

No Lab runtime is required to execute the simulation locally or in CI. Publishing
the branch is preparation for integration, not installing a voice assistant.
Use in-memory lights, volume, playback and a manually advanced monotonic clock.
Never pass unknown speaker transcripts to a device-capable agent. Never log raw
audio or full transcripts; simulation traces carry event types and decision IDs.

Acceptance: recognized Aničko activation, rejected old/default wake and playback,
approved light control in microphone room, unknown speaker/introduction denial,
follow-up verification, barge-in with real simulated playback cancellation,
stale completion rejection, exact volume recovery, error and timeout cleanup.

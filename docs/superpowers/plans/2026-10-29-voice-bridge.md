# Voice bridge 3.9.0

User authorized extending and deploying the existing bridge, without another design round.

1. Add bounded select, number, media volume/stop and satellite announcement action schemas; verify observed state and preserve durable idempotency.
2. Add voice status and diagnostic commands using the existing maintain scope and compatibility jarvis_action service=jarvis.voice. Expose no raw audio or transcript by default. Recording requires explicit confirm_recording=true, never runs on startup.
3. Reuse existing explicit entity/service allowlists; enable only the active Voice PE configuration entities, HomePod, and diagnostic system target. No arbitrary HA proxy or microphone stream.
4. Test rejected values, absent permissions, stale outcomes, retries, recording consent, diagnostic privacy and gateway compatibility.
5. Release via existing feat/jarvis-addon source and supervised updater with backup. Verify version, live voice state, a reversible same-value end-detection update, and no armed recording.

Pipeline STT/TTS provider settings remain managed by existing native integration options flows; pipeline selection is exposed through the satellite assistant select entities. HomePod persistent speech volume is updated through the existing configuration file and Core activation workflow, with immediate player volume available through the new action.

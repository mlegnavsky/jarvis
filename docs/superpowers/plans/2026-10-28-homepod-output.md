# HomePod answer output

Goal: living-room Voice PE remains the microphone; HomePod Obývák speaks Jarvis answers. User deferred audible/home tests until they say they are home.

Architecture: version-scoped TTS-end handoff to native Apple TV/RAOP playback. Hold the native satellite's TTS completion until HomePod finishes; then release only a fixed silent completion clip, preventing duplicate speech and premature follow-up listening. Native pipeline cancellation must stop only this routed answer. No firmware flashes, music/TV group changes or startup audible tests.

- [x] Test first: only managed satellite/pipeline routes, real audio URL/token never goes to Voice PE, HomePod completion precedes follow-up, cancellation stops owned playback, failures remain silent, synthetic startup probes do not play audio.
- [x] Implement HA component + private diagnostics. Require native StreamFile capability for blocking RAOP completion and preserve the existing phonetic TTS boundary.
- [x] Review, all 217 tests and deployment/config checks. Native metadata confirms HomePod RAOP and satellite URL firmware support. Actual sound and physical interruption tests remain deferred until user home.

Interruption boundary: stock Voice PE supports wake/stop-word cancellation during responses. Arbitrary speech interruption is not implemented/verified: external HomePod audio is not the Voice PE's acoustic echo-cancellation reference, so merely applying VAD would detect Jarvis's own voice. Do not claim that a prompt or HomePod route solves this hardware/acoustic issue.

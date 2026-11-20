# HomePod routing verification

User intent: the spherical HomePod Obývák speaks Jarvis's answers; Voice PE remains the input terminal. User deferred physical/audible testing until home. Arbitrary speech should eventually stop the answer; do not falsely claim current stock hardware supports this.

All 217 tests pass: 159 repository, 24 companion, 6 voice diagnostics, 20 speaker identity, 2 speaker backend, 6 HomePod route. Compileall/diff checks pass. Scope, silent terminal completion after awaited HomePod output, cancellation, native error conversion, streaming-hint suppression and compatible URL firmware mode are covered.

Independent review found raw playback exceptions bypassing native PipelineError cleanup. Regression test now requires a typed output failure; implementation injects native TextToSpeechError and preserves CancelledError. Native pipeline source confirms the normal error event/TTS-stream cleanup path. Pending native follow-up is cleared on failures/cancellation.

Component/config writes were revision-checked and verified before activation `homepod-output-activate-v1`. It verified Core 2026.6.4 RUNNING at 16:38:20 Europe/Prague, with valid configuration and backup `1dd23da7`. Fresh native report at 16:38:30: adapter active, status configured, actual HomePod entity available, native RAOP StreamFile supported and actual satellite URL/media-player firmware mode supported. Playback started/completed/failed counters are all zero, confirming no announcement was emitted. No audio test is permitted during this away-from-home phase.

Same-boot regression reports: companion_ready, Róza recall/stop test passed, native turn-taking probe passed; local speaker identification ready and its native HTTP/model/profile probe passed.

Limits remain explicit: metadata does not prove actual audible output, HomePod timing or physical wake/stop cancellation. Arbitrary speech interruption is not implemented because HomePod output has no acoustic echo reference in stock Voice PE. These are deferred/unsolved, not passing test claims.

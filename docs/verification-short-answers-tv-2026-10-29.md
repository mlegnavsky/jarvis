# Short requests and TV restoration

Incident: a correctly transcribed time question at 06:00:17Z took 1.121s in the conversation provider and then left continue_conversation=true. Subsequent microphone runs transcribed `context:` and unrelated phrases, producing multiple answers until06:02:29Z. The end-detection adapter also forced1.5s silence, overriding the native aggressive selection. Existing HomePod output had no AppleTV pause/restoration lifecycle.

Changes:

- Exact Czech time queries use Home Assistant local time before conversation-model/enrollment work and return one answer with continue_conversation=false. Known bare STT artifacts (context:, punctuation/empty) return silence and close, without a model call. General companion discussion continues normally; exact short light commands close after acknowledgement.
- Preserve native VAD finished-speaking setting while retaining the deliberate long-utterance ceiling.
- Scoped TVSession targets the confirmed AppleTV entity media_player.obyvaci_pokoj_obyvaci_pokoj. Pause only initiallyplaying content; claim only confirmedpaused state. Hold ownership across followups; restore only owned unchangedpaused content, and verifyplaying. No power/toggle/seek/volume commands. Externalstate/contentchanges discard ownership. Prepare overlapsinput processing; finalanswer/error/idle releases ownership. Old run cleanup cannot mutate a newer run's lifecycle; watchdog never resumes during active speech/pipeline processing.
- Existing HomePod RAOP volume fix and persistent35% remain.

Validation:162repository,42companion,12diagnostic and29HomePod/session/hook tests passed (245total). Red/green regressions cover localtime withoutAI, silent artifacts, preservednativeVAD, TVprepaused/contentchange/doublerelease/unconfirmedpause/resume, and interleavedold/new run cleanup. Independentreview found stale-run eventmutation; reproduced by two tests and fixed before deployment. No household TV pause/play was used as a test.

Deployment: all11live/recovery/manifest file writes verified under short-answer-tv-file-0..10-20261029. Core activation short-answer-tv-activate-20261029 verified, backup52f4cd4f, CoreRUNNING2026.6.4. Same-boot report confirms nativeVAD probe passed, native finished-speaking setting preserved, HomePodrouteconfigured at35%, TVSession loaded with noownedpause/householdactions afterstartup, capturedisabled. No postdeployment physical voice test has occurred. Physical response-start latency and shared HomePod/AppleTV audio restoration require a new household test; do not claim measured acoustic improvement from unit tests or a reset playback counter.

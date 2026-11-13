# Voice repairs and room commands

Authorized request: fix/deploy audited collisions and support Czech light commands using the microphone room unless a room is named explicitly. Keep Green, Voice PE input and HomePod output.

## Behavior

- Existing guarded legacy volume automations are retained; they cannot duck/restore the HomePod during the active managed output route. Missing diagnostic services metadata was already deployed and is preserved.
- Diagnostics no longer changes prefer_local_intents, starts automatic cloud conversation tests, or presents a never-started self-test as pending. Explicit run_companion_test and run_self_test services remain available. The current Jarvis pipeline keeps its intentional local-intent interception disabled, with exact light handling inside the companion agent so conversation continuity and stop phrases are not intercepted elsewhere.
- Exact rozsviť/zhasni, optionally to/světlo/světla, resolves to the real source microphone area. An explicit room overrides it. Entity room assignments take precedence over device room assignments. Only exposed light entities can be addressed. Missing/ambiguous rooms or rooms without exposed lights cannot fall back to the living room or whole house. The HA context is preserved; delayed/unavailable state changes are described as submission, never verified physical success.
- A matching new activation invalidates old output from TTS generation through queued/active HomePod playback. Unrelated pipelines and native synthetic probes never cancel or route household audio.

## Validation

248 tests pass: 162 repository, 37 companion, 11 diagnostics, 20 speaker identity, 2 backend, 12 HomePod/migration, 4 energy/weather. Compileall and diff checks pass. Independent review caught late cancellation ownership; regression reproduced obsolete playback during TTS generation before the fix and passed afterward. A separate bounded-session regression reproduced local-only counter growth and passed after the fix.

## Physical boundaries

Rozsviť/zhasni are command intents after Hey Jarvis or in follow-up listening. They are not new acoustic activation models. Official microWakeWord requires trained model assets for new wake words; no such Czech model has been invented or installed. Arbitrary-speech interruption and acoustic echo cancellation for an external HomePod are still not implemented. No voices are enrolled remotely; household voice accuracy needs three real enrollment samples per person. Core remains 2026.6.4 because the existing stream adapters are version scoped; compatibility with a newer Core is not claimed. No audible test or real household light action is used for deployment verification.

Deployment verification is recorded below after activation.

## Live deployment evidence

Full system backup 7fb291f1 completed before changes. All seven file writes verified and contents were read back byte-for-byte. Activation voice-room-repairs-activate-20261028-v1 created additional HA backup 7638de7f, passed native configuration validation, and verified Core RUNNING 2026.6.4 at 18:11:15 Europe/Prague.

Same-boot diagnostics started 18:10:51: native turn-taking/pronunciation probe passed, no automatic cloud companion test ran, pipeline_configuration_changed=false, and the existing preferred Jarvis/OpenAI STT/Onyx configuration remained unchanged. Real registry resolution (no service invocation) resolved bare rozsviť/zhasni to light.aqara_wall_switch_eu_2 in Obývák, and explicit chodbička to light.aqara_wall_switch_eu_3 and light.aqara_wall_switch_eu_4 in Vstupní chodba. Koupelna + WC exists as an area but has no exposed light: this is reported as no_exposed_lights, never redirected elsewhere. No bathroom-named controllable entity appeared in the current state inventory.

Same-boot HomePod adapter active/configured, real RAOP capability and satellite URL mode available, playback counters all zero. Speaker identity adapter active/ready, actual local model/native persistence probe passed; household profiles and captured turns remain zero. Jarvis MCP stream connected. New boot logs contain no managed voice integration failure; pre-existing Apple Companion/app-list, Cast and disconnected legacy terminal warnings remain. These do not constitute a verified acoustic test.

Source commit 8165a49 exists locally. Source publication was blocked by automatic approval review, even after connector verification of the user's owned mlegnavsky/jarvis repository and a credential-free changed-source scan; public GitHub publication needs explicit separate approval. Deployment to the authorized home system succeeded independently. No further push attempts are made.

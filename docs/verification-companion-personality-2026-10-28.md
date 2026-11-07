# Companion personality/memory/awareness verification

## Scope and evidence

Read actual deployed integration files and the private native startup report; the Jarvis addon version alone is not evidence of companion activation. Existing installation already contained personality, SQLite memory, guest session storage, joke filtering and on-turn appliance awareness. This continuation independently verified and preserved those sources, added local boundary tests and fixed the review finding below.

## Review and regression

Independent read-only review found one P2: `zapamatuj si pro domácnost` bypassed guest session-only storage. A new test reproduced persistent household data from an unverified satellite guest (RED). Runtime now requires a verified HA account for persistent household writes; unverified guests store only session notes with an accurate acknowledgment (GREEN).

## Local validation

- Complete repository command: `PYTHONPATH=jarvis:jarvis_updater python -m unittest discover -s tests -t . -q` — 159 passed.
- `python -m unittest discover -s managed_sources/companion -p 'test_*.py' -q` — 19 passed.
- `python -m unittest discover -s managed_sources/voice_diagnostics -p 'test_*.py' -q` — 6 passed.
- `git diff --check`, compileall for both managed components — clean.
- Tests cover real runtime + SQLite restart persistence, principal isolation, no private access via spoken introduction, guest change/history reset, forget, shared-note guest restriction, episode delay/refusal/repetition and original agent methods with API boundaries isolated.

## Deployment

Reviewed runtime installed via revision-checked administrative file write `companion-guest-memory-fix-1028`, verified revision `8c17d4b386edd4810cb1786bc1603b7f43fb5e2c93aa22e28cc687ab7f037070`. Activation job `companion-final-activation-1028` creates a HA backup, checks configuration and restarts Core. Final activation result and fresh native report are recorded below after completion.

Activation verified 2026-10-28 14:52:12 Europe/Prague: Core RUNNING, version 2026.6.4, backup `a46e4f9d`. Configuration check valid. Revision readback confirms the verified-principal guard is present.

Fresh native report: boot started 14:52:00, report updated 14:53:12 Europe/Prague, status `companion_ready`. Actual text conversation remembered fictional blue dragon Róza across two turns, continued listening, and stopped at `Děkuji, konec.`. Fictional-profile persistence/isolation/forget and joke filter checks all passed. Fictional-device first-observation delay, one offer per episode and no automatic announcement checks passed. Identity returned written `Jarvis` and targeted TTS input `Džárvis`. Native synthetic-PCM turn-taking probe passed. No physical household commands or audio were emitted by these tests.

## Practical limits

Voice guests have session notes, not durable authenticated personal memory. Voiceprint enrollment/recognition is not implemented. Phone/Wi-Fi presence does not identify the speaker. Granular spoken note correction is not implemented; explicit notes and full-principal forget are supported. No non-smart stove detection, automatic device announcements, acoustic barge-in or ChatGPT shared memory. Native tests use text or synthetic PCM and fictional states; they do not prove physical microphone acoustics, subjective humour quality or actual speech pronunciation.

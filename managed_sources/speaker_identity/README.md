# Jarvis local speaker identity

Install this component directory as `custom_components/jarvis_speaker_identity` and enable `jarvis_speaker_identity:` in configuration.yaml. It depends on the managed voice diagnostics/turn-taking component and the installed Extended OpenAI Conversation runtime patch. Core stream hooks are guarded for HA 2026.6.4 and the existing Jarvis living-room satellite only.

## First enrollment

Say `Hey Jarvis, nauč se můj hlas. Jsem Martin.` Replace the name for every person, e.g. Šarlota, Iris, Petr or Dana. The system explicitly requests three further, different, clear utterances of at least three voiced seconds each. Complete enrollment within five minutes. It rejects short, clipped, quiet, inconsistent or uncertain samples and refuses to overwrite an existing name. `Zruš učení hlasu` or the normal conversation stop cancels enrollment.

No household voice is pre-enrolled by the deployment, the public reference fixtures or a text-only test. Every person must supply their own real microphone samples. State `sensor.jarvis_rozpoznavani_hlasu` and private `jarvis_workspace/speaker_identity/report.json` expose readiness, profile count, capture counts and timings without publishing voiceprints or audio.

## Recognition and memory

Only actual active-turn PCM is considered; no background listener or audio archive is created. Up to 12 seconds of 16kHz mono signed-16 audio is held in RAM, sent to the local stateless model and discarded in a finally block. Too-long utterances are not assigned from just their first speaker. Very short/noisy speech can remain unknown. Long samples get a two-window consistency check; this is conservative rejection, not guaranteed overlap diarization.

Known voices require cosine similarity at least 0.75 and a 0.12 lead over the next profile; each available window must identify the same profile. Recognition is probabilistic personalization, never HA authentication or new permissions. Authenticated HA private notes remain in a separate namespace. Voice-specific conversational notes use a random per-enrollment memory ID; deleting/re-enrolling the same name cannot revive old notes. Unknown/uncertain turns clear personal guest context and do not save new personal notes. This deliberately sacrifices anonymous continuity when identity cannot be established.

`Zapamatuj si: …` stores a note for a recognized voice. `Zapomeň moje poznámky` clears notes/topics. `Vylepši můj hlasový profil` adds an explicit high-confidence sample; profiles never adapt from guesses. `Smaž můj hlasový profil` requires a currently recognized voice and removes its active profile and conversational memory. A logged-in HA administrator can recover an ambiguous/incorrect profile with the native `jarvis_speaker_identity.forget_profile` service and the profile name. Re-enrollment then requires three new samples.

## Validation

Policy/coordinator/hook tests exercise explicit enrollment, consistency, expiry, ambiguity, short audio, one-shot transcript/device binding, backend failure, scope guards, raw-buffer release, privilege checks, deletion and fresh memory identity after re-enrollment. Companion tests cover context isolation and cancellation of enrollment on conversation end.

The backend's four public upstream speech fixtures and the HA HTTP-to-model/temporary-profile startup probe validate installation and model operation. They do not establish accuracy for Czech household members, children, reverberation, TV playback, illness or replayed voices. Household accuracy requires enrollment and physical tests; the report explicitly retains `household_accuracy_verified:false` until those exist.

## Open household controls1.3.0

Owner-selected public_controls permits exposed local light commands from any activated speaker, including short speech and embedding outage. Identity inference is optional and deferred for commands, never a prerequisite. Existing native pipeline guard and one-use text/action/target binding remain. A family/owner training session consumes utterances without actions. Locks/profile administration retain their existing authorization and strict identity checks. Unsupported actuator routes are not invented by this change.

Recurring unfamiliar speech can create private familiar_voices records in the existing mode0600 SQLite database: max16clusters/12embeddings each; inactive clusters expire after30days. Only active captured speech>=3s, backend qualityok,rms>=.004,clipped<=.02,no detected playback and>=2consistent windows qualify. Duplicate PCM hashes are ignored; repeated normalized sentence hashes do not add training samples. Similarity heuristics require six distinct utterances across three conversations before a name question; this is familiarity, never biometric certainty or replay protection. Commands stay silent and never ask names. One name question per cluster/day may be appended after an ordinary conversational answer. Name assignment requires the same currently matched cluster and an explicit Jsem/Jmenuji se answer within120s; short answers without sufficient voice evidence do not attach a name. Familiar names decorate guest context occasionally, never a voice/private principal or permissions. Existing recognized but unprivileged profiles likewise expose only occasional name, no private context. Authenticated administrator forget_profile removes matching familiar names too. No raw audio or transcripts are retained for learning. Existing owner anchors and matching bank stay unchanged.

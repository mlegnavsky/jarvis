# Voice pipeline refactor

Owner explicitly requests end-to-end refactoring after public-control policy change. Preserve public exposed lights, silent success, optional familiarity, protected lock/profile/private routes, immutable owner bank, wakeJarvis/HeyJarvis. No more owner calibration.

Observed production evidence: public named-room and bare commands completed silently; all-house Zhasni všude fell through to LLM; context:### produced another dialogue; independent direct acoustic light detections still hit old speaker-authorization error despite public-light policy. HomePod completed10/11playbacks; native abort source remains unknown, so no speculative firmware change.

Approach: one pure shared command contract deployed as Python library custom_components/jarvis_voice_common, used by grant authorization, local room resolution, dialogue completion. Explicit all-house lights limited to exposed entities. Courtesy/name prefixes and light synonyms canonicalize once; quoted/negative/conditional/multi-action requests never become actions. Public vs protected domain remains explicit. Keep native HomePod completion adapter and physical cancellation.

Extract optional learning task lifecycle from coordinator into bounded BackgroundLearning with timeout/cancellation/diagnostic counters. Training authority wins over shortcuts. Pure turn policy owns no-op artifacts and conversation closure. Local command outcomes release temporary chat sessions immediately, including polite commands and empty successful replies. Direct acoustic light detections remain disabled outside selected wake-word flow, with truthful error scope rather than obsolete voice-match explanation.

Verification: red/green tests reproducing all-house command and scaffolding artifacts; same parser tested end-to-end through gate, target binding and local execution; state/authorization/unknown room/conditional/multi-action guards; background queue cancellation/errors/timeout; actual composition tests in both setup orders. Full relevant suites, CI, independent review, one backed-up CAS deployment and postboot file/runtime verification. Physical acoustic success not inferred from CI.

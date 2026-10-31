# Anička live preview deployment

User approved live deployment/testing after offline simulation. Implement the
smallest working preview through the existing OpenAI STT/conversation/TTS and
HomePod adapters. Preserve home-control backend, memory namespaces and device
permissions. Native firmware wake models lack Aničko; do not relabel Jarvis
weights. Existing production adapters do not provide arbitrary speech barge-in.
These two features remain integration work, not deployment results.

Changes: feminine Czech Anička personality and local responses; diagnostic
identity expectation Anička included in overall pass gate. Set existing pipeline
voice ash→nova with revision-bound API. No new voice enrollment or recordings.
Code and recovery copies must match, preserve current revisions, prepare a bundle
with source commit/Core 2026.6.4, backup and restart. Acquire lease before changes;
poll durable jobs and reconcile unknown outcomes. Verify current file hashes,
pipeline voice, actual identity and recall/stop probe; test HomePod playback.

Local verification: 43 companion +20 diagnostic tests pass; Python compile pass.
Independent review requested. Live verification and receipt follow deployment.

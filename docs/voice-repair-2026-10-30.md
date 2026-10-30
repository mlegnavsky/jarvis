# Wake tuning and voice delivery repair

Adds narrow revision-checked operations for tuning an already installed local private wake model and changing a native OpenAI TTS pipeline voice. Weights, recordings, credentials and live household settings are not included in this release.

Model tuning reuses existing validated install and rollback paths and preserves byte-identical weights. Pipeline changes serialize Jarvis writers, update only tts_voice, and verify the entire pipeline after native update. Independent external writers remain outside this local lock. Tuning is not evidence of acoustic accuracy or false activation rate.

The Czech companion prompt requests energetic, naturally playful delivery while preserving joke repetition limits and serious-topic and privacy boundaries. Existing bounded follow-up remains turn based rather than full duplex.

Validation:239 addon tests passed,20 skipped;42 companion tests passed. Regression checks cover private weight preservation, unchanged unrelated configuration, stale revisions, invalid cutoff no mutation, native partial update/full readback and concurrent writers. Release manifest and whitespace checks passed. Live deployment and acoustic acceptance are separate from these software tests.

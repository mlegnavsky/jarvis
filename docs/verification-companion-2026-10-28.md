# Companion conversation verification

Deployed through revision-checked writes, backup237dd883 and verified native core_restart job companion-activation-restart. Core2026.6.4 RUNNING; Supervisor configuration check valid. No household actions or audio playback were executed by the scripted test.

Tests:159 repository tests +9 companion tests (including execution of actual agent methods at isolated HA/API boundaries) +6 voice diagnostic tests =174 passing. Independent review findings fixed: preserve explicit conversation IDs; maintain turn counts independently of truncated model history.

Native async_converse test against installed conversation.extended_openai_conversation:
1. Supplied fictional blue dragon Róza. Agent confirmed, continue_conversation=true.
2. Asked name/color without restating facts. Agent answered Róza and blue, continue_conversation=true.
3. Děkuji, konec. Agent answered Dobře, končíme., continue_conversation=false, stop branch bypassed model/tools.
Diagnostic report companion_test.passed=true, status=companion_ready.

Readback of preferred Jarvis pipeline: OpenAI STT/cs-CZ -> Extended OpenAI Conversation -> OpenAI TTS/Onyx; prefer_local_intents=false, so conversation/stop bypass neither context nor the managed agent. Same-device memory fallback only when no explicit conversation ID is supplied. Existing device permissions remain unchanged.

Limit: this is native turn-based follow-up listening, not a new full-duplex Realtime implementation. No arbitrary spoken interruption or acoustic satellite follow-up was remotely verified. Native silence/timeout still ends the listening turn; short-term context can resume on the same device. Hardware microphone test is required before claiming the user's complete voice experience matches ChatGPT Voice.

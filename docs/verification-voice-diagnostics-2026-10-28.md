# Voice diagnostics and active pipeline correction

165 tests pass (159 repository +6 diagnostic regression tests). Independent review fixed loss of >20-second captures and clarified the15-minute admission window: existing native recordings can finish later, under HA's five-minute pipeline timeout. HA configuration check clean after first integration startup. Installed custom files were revision-checked and verified. Actual HA Core2026.6.4 executed the adapter and produced its private report.

A first reference test was invalid because Wyoming/Piper ignores language unless a concrete voice is supplied. Those results are excluded. Final reference explicitly used cs_CZ-jirka-medium. Each identical PCM sample was sent directly to installed STT entities, never to a conversation agent or physical device.

| Reference | Whisper base-int8 | Speech-to-Phrase | Existing OpenAI STT |
|---|---|---|---|
| Kolik je hodin? |4.846s; Kolyky je hodin. |0.945s; correct |1.362s; Koľko je hodín? |
| Jaká je teplota v obýváku? |5.328s; understood text |2.134s; no text |0.985s; exact |
| Zhasni v obýváku. |4.815s; Zásně v obýváku |1.376s; no text |0.922s; exact |

`all_exact` correctly remains false. OpenAI's first result is Slovak wording with the same meaning, not a verbatim Czech transcript. Synthetic tests do not establish room/microphone intelligibility or end-to-end audible latency. Speech-to-Phrase's limited command grammar/exposed-device vocabulary differs from open-ended STT; its no-text result is not evidence of a microphone defect.

Native preferred Jarvis pipeline was changed through HA UI and read back independently:
- STT stt.openai_stt, cs-CZ (pre-existing configured OpenAI integration, as selected in original home_voice architecture).
- prefer_local_intents=true.
- Extended OpenAI Conversation and OpenAI TTS/onyx retained.
- Functional satellite remains on preferred pipeline.

Private diagnostic report: jarvis_workspace/voice_diagnostics/report.json. Sensor: sensor.jarvis_hlas_diagnostika, excluded from Recorder. Native temporary WAV capture stays outside www. No microphone recordings were uploaded by diagnostics; three fixed synthetic reference samples were sent to the existing OpenAI service for comparison. The selected primary pipeline now sends post-wake speech to that provider. Existing API billing applies, independently of ChatGPT subscription.

A final physical microphone test remains explicitly unverified. It is the only test the remote implementation cannot simulate faithfully. The next attempt will have native pipeline events, microphone signal metrics, and separate satellite/player transitions instead of guesswork.

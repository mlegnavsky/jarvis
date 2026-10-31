# Integration management acceptance — 2026-10-27

Main3.7.0 is deployed, connected to HA through gateway1.0.0. Scope and remaining boundaries are in plugin-management.md.

-153 unit/integration tests passed, including native forms, revision conflicts, owned subentry routing, credential projection, nested schema filtering, foreign-flow rejection and durable request replay.
-Manifest/release and diff checks passed. GitHub Actions40479573408 (3.6.0) and40480303877 (3.7.0) had successful tests and both container build/startup jobs.
-Update c0b9008991cd41da97651f42fa0d909d to3.6.0 verified; backup4e14f330.
-Update211eb22fa27b4ef882cda703766055a7 to3.7.0 verified; backup0835cff1.
-Live inventory:28 integration entries;11 expose classic options flows. Native OpenAI integration has4 subentries: conversation, ai_task_data, stt, tts.
-Actual preferred voice pipeline read through native API: Czech Jarvis, faster_whisper → extended_openai_conversation → openai_tts, onyx. Pipeline configuration was not changed.
-live-integration-options-open-20261027 verified native Solarman form retrieval after backup e41ddaf6. Separate readback of its owned flow confirmed the same form revision. No configuration submitted.
-native-openai-settings-proof-20261027 verified native TTS subentry form retrieval after backup cfab9329, fields prompt and tts_speed. No configuration submitted.

Submission and reload paths were tested against controlled fixtures; settings were not arbitrarily changed on the household merely to demonstrate capability. Loading a form is not a completed configuration change, and a native create_entry result is not an independent physical or acoustic test. No device actuation or paid model inference was requested by these acceptance checks.

Unproven areas remain explicit: credentials reauth/general reconfigure, initial device pairing, firmware upload, local Jarvis Core source access and custom builds of every third-party app. This release does not claim unrestricted control of every binary/plugin.

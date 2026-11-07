# Local speaker identity implementation plan

Goal: opt-in voice profile enrollment and probabilistic speaker recognition, connected to actual Assist PCM before the conversation agent.

Architecture: extend existing local Jarvis Core with a stateless internal-only speaker embedding endpoint using sherpa-onnx CAMPPlus. HA keeps bounded local voiceprint profiles, handles explicit consent/enrollment/deletion and consumes one result per active satellite turn. No raw voice archives. Existing status endpoint and credentials remain unchanged.

User authorized autonomous implementation, overcoming obstacles and deployment; implement inline without reopening design approval.

- [x] Tests first: rejection of short/noisy audio, isolated profile storage, minimum three consistent enrollment samples, ambiguous/unknown/mixed voices, deletion, overwrite protection, no automatic learning from guesses.
- [x] Build CPU single-thread embedding service in existing local Jarvis Core, keep status port 8765 and bind inference to internal container port 8766 without a host mapping.
- [x] Add HA speaker identity coordinator: bounded active-turn PCM, asynchronous inference, one-shot device result, consented enrollment and accurate fallback. No background microphone or raw audio retention.
- [x] Integrate recognized address/profile label with conversation. Voice recognition is not HA authentication and does not unlock authenticated private notes or sensitive actions.
- [x] Independent code review and all 211 tests; backend real model probe passed, HA version 1.0.1 active, native HTTP/model/profile persistence-deletion probe passed at 16:00 Europe/Prague; preserve source in repository.

Thresholds are conservative starting values, not claimed household accuracy. Family members must each enroll their own voice; no profiles are invented from names or Wi-Fi presence. Multiple-speaker/low-quality/uncertain results remain unknown. Existing authenticated personal records are not exposed based on biometric estimates.

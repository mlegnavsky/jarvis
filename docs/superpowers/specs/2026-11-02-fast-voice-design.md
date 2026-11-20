# Fast voice first stage

Owner wants fluid HomePod conversation, human interruption without self-echo, and one-second first response. Measured current agent11.8s/TTS3.7s/HomePod2.3s. One second is an acceptance target, not proven HomePod hardware limit or current capability.

This bounded stage removes avoidable model waiting before implementing a new audio transport. Preserve HomePod/native local WAV, Marin, own volume/mute, TV ownership, principal memory, local silent lights and lock guards. Use existing configured API client; benchmark configured model and two explicitly bounded fast candidates with fixed non-household text, no microphone, services or memory. Select a supported faster candidate through CAS-written model-only voice policy; no automatic promotion and no fallback retry after unknown provider result. Policy applies only to designated microphone/satellite, text clients retain configured model. Invalid/missing policy uses configured model; disclose status. Shorter default replies, fuller detail on request. Time questions shortcut only after native identity/input guards. No fabricated one-second gain.

Approaches: changing only VAD cannot affect measured model11.8s; private pyatv buffer monkeypatch risks ownership/timing and is deferred. Realtime/AEC is the later architecture; this stage first proves model improvement using same account and output.

Record source EOF as audio_source_ended with elapsed time/stage so it cannot masquerade as voice interruption. Do not drain playback after input loss or rearm after a user stop. Correct scheduling-delay terminology: context.latency is client-side default, not negotiated receiver minimum. Echo/AEC and persistent transport remain open and cannot be called fixed by these changes.

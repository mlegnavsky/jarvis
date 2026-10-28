# Local speaker identity verification

## Implementation and tests

Existing local Jarvis Core hosts a stateless ARM speaker-embedding service with pinned multilingual CAMPPlus weights, sherpa-onnx 2.0.1 and one CPU inference thread. Existing status UI/options remain; inference is on container-only port 8766. Native startup discrimination probe passed: same A 0.8088, same B 0.6664, maximum cross 0.3279. An English-only candidate failed discrimination and was rejected before deployment.

HA consumes bounded PCM only from the active managed satellite's Assist run, submits it locally, binds the result to device/transcript and consumes it once. Explicit three-sample enrollment, consistency/quality checks, profile deletion and admin recovery are implemented. No raw archive, automatic guessed-profile adaptation, Wi-Fi identity assumptions or new HA permissions.

All 211 tests pass: 159 repository, 24 companion, 6 diagnostics, 20 speaker identity, 2 backend quality. Compileall and diff checks pass. Full repository command: `PYTHONPATH=jarvis:jarvis_updater python -m unittest discover -s tests -t . -q`. Managed sources use separate unittest discover invocations.

## Review and regressions

Independent review reproduced guest personal context crossing an unknown-speaker change. RED test captured it; GREEN clears guest personal context whenever voice is uncertain. Voice notes stay separate from authenticated HA notes. Per-enrollment random memory IDs prevent notes reviving when a name is re-enrolled. Tests cover admin-only recovery and cancellation of enrollment on conversation end.

The initial native bridge test caught a partial-body read of its public reference WAV. A single aiohttp read(n) need not return a whole file. New bounded-read tests cover repeated short reads and size rejection; the probe joins to EOF and checks SHA256. Diagnostics include failed stage/reason; ready requires the native bridge probe to pass.

## Deployment

Backend fingerprint `92bc9147b555b09811985c95f5634179f57f2d670eb7ccb481943057768dcc6f`; build `speaker-backend-build-v1` verified, original-addon backup `1283c884`. First HA activation `speaker-identity-activation-v1` verified Core RUNNING/config valid, backup `33516533`, then detected the probe failure. Completion was withheld. Component 1.0.1 fixes bounded download/readiness; writes verified before activation `speaker-identity-activation-v2`.

Second activation `speaker-identity-activation-v2` verified Core RUNNING 2026.6.4 at 15:59:51 Europe/Prague, backup `23564f5f`, configuration valid. Fresh speaker report booted 15:59:07, updated 16:00:07 Europe/Prague: adapter active, status ready, backend reference probe passed, native HA HTTP -> local model -> temporary profile persistence/deletion probe passed, 192-dimensional embeddings, measured single-reference inference 1502.2ms. Household profile count zero and captured microphone turns zero: no household acoustic accuracy is claimed.

Fresh companion report from the same reboot: actual Róza recall/stop conversation passed; personality memory, device awareness and native synthetic turn-taking probes passed. Jarvis connector stream remained connected. This confirms integration and regressions without issuing household commands or playing audio.

## Limits

No household person is pre-enrolled from text or public fixtures. Each must provide three real microphone utterances. Reference/model/temporary-profile tests demonstrate installation, not household accuracy; `household_accuracy_verified:false` remains explicit. Short/noisy/mixed/overlong audio can stay unknown. Uncertain anonymous continuity is sacrificed to avoid personal-context leakage. Voice personalization is not secure authentication, liveness detection or acoustic barge-in.

# Combined stack audit — 28 October 2026

Scope: previously deployed energy/weather/Sun cards, companion conversation and scoped memory, microphone diagnostics, local speaker identification and HomePod output. No audible or household voice tests: the user deferred those until home.

## Corrections

- Two legacy automations (1783328533537 and 1783328867435) ducked/restored the HomePod volume based on the Voice PE player. Silent terminal completion in the new output route could trigger these at the wrong time. Revision-checked migration guards both automation entry and each volume action while the HomePod adapter is active, including a fresh check after the ten-second delay. Unrelated automations are preserved. Reload verified.
- Reconciled the diagnostics source snapshot with the deployed merge/history and outcome reporting. The old repository snapshot lacked merge_runs despite its caller importing it.
- HomePod TTS-end occurs after awaited output: diagnostics now labels this duration synthesis plus HomePod output rather than generation alone. Added missing service descriptions.

## Evidence

230 automated tests passed: repository 162, companion 24, diagnostics 9, speaker identity 20, speaker backend 2, HomePod output/migration 9, energy/weather 4. Compileall and git diff checks passed. Independent read-only review found no important or critical defect.

Combined adapter tests exercise both valid initialization orders, single microphone capture, phonetic output, awaited HomePod completion and terminal silence, cancellation cleanup and synthetic-probe exclusion. They use Core-like doubles; they do not prove physical acoustics.

Live managed source comparison before corrections: 22 of 23 managed files matched; the sole difference was the diagnostics snapshot corrected above. Solar/weather JavaScript matched. The active local speaker backend source fingerprint remained 92bc9147b555b09811985c95f5634179f57f2d670eb7ccb481943057768dcc6f. OTE/FX and Žitenice weather were fresh during the audit; unavailable legacy weather.forecast_domov is not referenced by the relevant dashboard. Market prices remain distinct from an unconfigured export contract.

## Remaining limits

- Physical HomePod audio, volume behaviour and wake/stop cancellation await the user's home test. Arbitrary speech interruption is not implemented: stock Voice PE lacks an acoustic echo reference for external HomePod output.
- No household voice profiles are enrolled; speaker accuracy is not yet verified on family members.
- Logs include Apple Companion/app-list communication warnings and unrelated unavailable legacy devices. These are not evidence of a failed RAOP audio stream; no stream was emitted in this audit.
- Backup retention preserves the latest successful local Home Assistant/database/add-on backup and keeps newer working partial backups until a suitable newer system copy exists. The audit observed multiple backups, not one; it does not claim that temporary copies have already been pruned. The admin system backup includes Home Assistant and installed add-ons, not all optional folders.

Activation `voice-audit-activate-v1` verified Core 2026.6.4 RUNNING at 17:33:03 Europe/Prague, with valid configuration and pre-change backup e22b124a. Fresh same-boot reports show HomePod adapter active/configured with zero playback starts, speaker recognition active/ready with native model/persistence probe passed, and native turn-taking probe passed. New boot logs no longer contain the missing diagnostics services.yaml error; Apple Companion/app-list and legacy-device warnings remain as described above. The modified diagnostics source and service metadata were read back and matched the repository files.

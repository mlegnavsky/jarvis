# Czech wake models and direct light commands — 2026-10-29

The owner requested reliable Džarvis/Džarvisi activation plus standalone rozsviť and zhasni. Other command wake words remain paused.

## Direct light commands

The Core 2026.6.4 adapter in `managed_sources/voice_diagnostics/direct_wake.py` accepts only those two exact wake phrases from the configured living-room Voice PE and pipeline. It starts native intent processing with the recognized word, without cloud STT or waiting for a second instruction. Native exposed-light and microphone-area resolution remains authoritative. Named-room commands continue through Jarvis followed by the full instruction; suffix speech after bare light wakes is not collected.

The adapter preserves native shared wake cooldown, emits microphone-stop after native run-start, restores per-run state on cancellation, and delegates STT-only question runs unchanged. It adds no ESPHome Home Assistant action permission or microphone recording.

Eight adapter tests, 20 diagnostic tests, 42 companion tests and 162 repository tests pass. An independent review found the cooldown, microphone-stop and STT-only issues; all were corrected and re-reviewed. Runtime activation `direct-light-final-activate-20261029` is verified, Core RUNNING 2026.6.4, backup `c4c02cc8`.

Firmware 2026.10.1 containing the light models installed successfully at 08:03 Prague time. The terminal reconnected and completed its stable-boot period. Logs confirm model loading and subsequent native direct-command processing, including microphone stop before intent. Two rozsviť detections reached the living-room light handler in roughly 0.05 seconds; the immediate state confirmation was not available, so the spoken response correctly did not claim physical success. The owner has not confirmed acoustic or physical acceptance.

The synthetic light assets originated in Actions run 40748837603:

| Model | Artifact | SHA256 | Five-window cutoff |
| --- | --- | --- | --- |
| rozsviť | 12843279366 | 8ba6f4e6741263f8329b913c84fcba3bffe145f2254160d876393f49f0653a63 | 0.34 |
| zhasni | 12845771427 | 5f1a0cd8531f00e5627a054e20c19ae1b6991ba3254b01593d3673b7e6ad4995 | 0.28 |

Both are 60,968 bytes. Their original synthetic ROC reported zero false accepts in its evaluated ambient material at these cutoffs; this is not a household guarantee. The models are internal to the firmware and enabled by a boot action, preserving the Jarvis selector.

## Džarvis/Džarvisi

The previous Jarvis model used plain Jarvis/Jarvisi synthetic text. Actions run 40831194617 (training commit `7d7e07821b8c4da98fb5d818cdc0cb6fa369aa4e`) added explicit Czech Džarvis, Džarvisi, Džárvis and Džárvisi variants, retaining the previous forms. That synthetic-only candidate was rejected after local evaluation against the owner's existing recording.

A private local adaptation used eight of its ten repetitions for training. Two repetitions, one of each form, were excluded from training. The base model's last two convolution blocks and classifier were adapted; early layers and batch-normalization statistics stayed frozen. Public synthetic positives, confusers and dinner-party negatives were retained. The selected checkpoint was step 550 of 601, chosen using validation results.

The exported quantized streaming model was evaluated using ESPHome's integer frontend quantization, three-frame stride and five-prediction average:

- All ten recorded repetitions were detected at gains 0.5, 1, 2 and 4; the two training-excluded repetitions were also detected.
- 96 synthetic confuser clips produced no detections at the selected threshold; their maximum post-warmup average was 0.211.
- 5.3347 hours of public ambient tracks produced zero detections at the selected 0.98 threshold. Some windows from these tracks were used for checkpoint validation, and the threshold was selected using the same evaluation. This is tuning evidence, not an independent estimate of household false-activation rate.

Private model SHA256: `8e2b5d19041e7f865e0c7a7c3078732b017dee824484971a9e606b2ec1d6056c` (60,912 bytes). A private checkpoint containing weights, scripts and receipts is verified on Green; its archive SHA256 is `5b4af63c5c41cab18187180c3e3cf768b182b9c8c5302c6fea6c4bddff56dc8f`. Household audio and adapted weights are not published in this repository.

The private manifest and model are stored in the ESPHome configuration directory. The final firmware compiled and installed successfully (configuration hash `0xea92653f`, build time 08:28:59 Prague; total build/install 4m46s, encrypted OTA transfer 41.60s). Logs at 08:34 confirm the new Jarvis cutoff 0.98 and retained light-model cutoffs 0.34/0.28; the terminal completed its stable-boot period at 08:35. Fresh Home Assistant state confirms Jarvis selected, microphone unmuted and satellite idle. Output diagnostics remain configured at 0.35, with two completed HomePod outputs and two confirmed TV pause/resume pairs since the backend restart, zero failures. Physical in-room recognition of the final model remains unverified; the owner must perform the acoustic acceptance test.

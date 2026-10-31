# Firmware bridge — Jarvis 3.11.1

Uses the existing authenticated `jarvis_action` route: service `jarvis.admin`, entity `jarvis.system`. Existing maintenance/write gates and maintain OAuth scope apply. No dashboard browser sign-in, no disabled authentication, no shell or arbitrary URL proxy.

Enable explicit `firmware_targets` filenames in addon options. Only those configurations under the mounted ESPHome directory are managed. Secrets are neither returned nor changed by model operations.

Reads: `{action:read,query:firmware_devices}` returns current online/config/deployed hashes; `firmware_config` target filename returns revision and model IDs without source/credentials; `firmware_jobs` target filename lists bounded native tasks; `firmware_job` target native task ID returns sanitized state.

Changes use durable Admin request IDs. `firmware_compile` and `firmware_install` require target and expected_revision. Install performs a Supervisor backup, rejects offline targets, waits for both native compile and its dependent upload, then verifies online state and matching nonempty configuration hashes. A queued/running/unknown/unverified job is not success. Read the same Admin job after transport loss; never repeat under a new ID. Native task IDs are retained in the Admin job summary, and can be reconciled through firmware_jobs. Reconnection proves firmware state, not acoustic wake accuracy.

`firmware_model_install` additionally requires model_id (already in target), model_base64, sha256 and manifest. Manifest contains only wake_word and micro {probability_cutoff,sliding_window_size,feature_step_size,tensor_arena_size}. Generated version 2 manifests include minimum_esphome_version 2024.7.0. Binary is bounded and checked for TFL3 and digest; the compiler validates model compatibility. Assets are content addressed and private. The single model source scalar changes; all other configuration bytes remain unchanged. Alias/anchor configurations are rejected for this edit. This saves configuration but does not compile or flash it.

`firmware_config_restore` requires target, expected_revision and backup_id of the model install. It restores the local before-image without flashing. Model assets remain available for audit/reuse. Neither config restoration nor the Supervisor backup constitutes automatic bootloader rollback on devices that do not support it.

The addon invokes the explicitly installed HA integration jarvis_firmware_bridge through its admin-only, five-command WebSocket capability. Both integration targets and addon firmware_targets must authorize the configuration. The Core integration privately uses Device Builder 1.25 native tasks via authenticated Supervisor ingress. It does not expose session credentials or a generic Supervisor proxy; the addon never calls the Supervisor/hassio command prefixes prohibited by its Core WebSocket proxy. Core creates its own fresh private sessions after restart, so browser sessions are not required. Unsupported upstream protocols fail closed with generic errors, never returning session tokens or raw output. Firmware source must not be edited simultaneously in another client during a build/install; revision checks detect drift, but an already-started native OTA is not automatically undone.

## Live verification — 2026-10-29

Jarvis 3.11.1 update verified (job 249c0870327d422daa63a8c793dcf6cb, backup 8eef43cc). Native Core integration activation verified on Core 2026.6.4 (backup ba5a595a). No browser used.

Private model import fw3111-private-model-import-20261029 verified, preserving the existing personal model SHA256 8e2b5d19041e7f865e0c7a7c3078732b017dee824484971a9e606b2ec1d6056c. No model binary or recording is published here.

End-to-end install fw3111-live-install-20261029 verified at 08:34:04 UTC, backup a00e2594. Native compile 68663b2cddd5 and dependent OTA upload 3b0f3de15d4d both completed with exit code 0. Device home-assistant-voice-0a8bde.yaml returned online with expected and deployed config hashes 1312060e. Acoustic wake accuracy was not tested by this installation. Configured speech volume remains 0.35.

Validation: 193 addon tests and 5 native integration tests passed; release manifest/source parity check and git diff whitespace check passed.

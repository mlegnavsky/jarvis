# Voice stock recovery implementation plan

**Goal:** Restore the living-room Voice PE remotely to the official configuration and compare its released version with the hallway unit.

**Architecture:** Add one narrowly scoped staging operation to existing firmware administration. Keep networking, encryption and OTA credentials inside the private mount; remove custom models and runtime overlays. Compile and install through the existing verified native OTA jobs. Device public metadata gains software/hardware versions. No new voice framework, Core upgrade, audio capture or memory deletion.

- [ ] Test pure stock rendering: fixed target, immutable official source, retained credentials/identity, no custom callbacks or models, reject ambiguous YAML and stale writes.
- [ ] Implement rendering and revision-bound staging; retain explicit rollback and support stock metadata without local wake models.
- [ ] Add public device versions, release3.12.6, regenerate contract; run targeted/full tests and review.
- [ ] Publish with expected remote HEAD; update only management addon, leaving native voice hooks disabled.
- [ ] Read hallway version, resolve matching immutable official package, stage/compile/install once; verify native upload, reconnect and config hashes.
- [ ] Match terminal settings and retain clear pending physical conversation acceptance.

Configuration before-images remain private. Never copy the hallway device identity or network encryption key into the living-room device. Failed/unknown OTA is reconciled, never blindly repeated.

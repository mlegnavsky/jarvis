# Remote management implementation plan

Goal: manage HA editor automations and inspect configuration from the existing authenticated Jarvis connector. User requests implementation and a live update verification without further manual commands.

Architecture: bounded HA API methods; MCP tools use existing jarvis:maintain consent and maintenance_enabled. No filesystem mount or Supervisor role increase. All writes have durable request IDs, a stored before-image, revision precondition and readback. Creating or editing automations requires initial_state=false; enabling is a distinct existing allowlisted device action. No arbitrary URL, shell or file editing proxy.

Scope: read selected HA system configuration, run HA configuration validation, list automation states, read editor automation definitions, save disabled definitions, delete and restore backed-up definitions. HA performs semantic validation before saving. Backups are local in the Jarvis data directory and included in its existing add-on backup.

Limitations: HA's editor API offers no atomic compare-and-swap against independent UI edits. Revision checking prevents known stale writes but cannot eliminate the final external race. Stored definition verification does not establish execution or physical results. No installation of other add-ons or arbitrary configuration.yaml edits.

Tasks:
- [ ] Add failing HTTP fixture tests for missing definitions versus unavailable API, rejected writes, successful config readback.
- [ ] Add HAClient bounded automation API methods and configuration diagnostics.
- [ ] Add failing management tests: backup, stale revision, idempotency across restart, uncertain outcome, restore, disabled default and permissions.
- [ ] Implement SQLite journal with before-images and fail-closed replay; backups precede effects.
- [ ] Add MCP tools and end-to-end authorization/argument validation tests.
- [ ] Run full test suite, manifest checks and CI arm64/amd64 build/start checks.
- [ ] Release 3.1.0, update through Updater, record backup and verified job, check live diagnostics and report any unavailable live verification separately.

Review focus: absent config integration must not be interpreted as missing automation; stale or conflicting requests never write; unknown outcomes never repeat; secrets never enter audit metadata; tests never operate physical devices.

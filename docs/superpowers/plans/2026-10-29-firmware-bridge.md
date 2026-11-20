# Direct firmware bridge

User explicitly requests end-to-end firmware management without browser sessions and has opted out of further design questions.

Use existing maintain-scope Admin durable jobs and explicit configured target filenames. Connect to Device Builder1.25's native persistent firmware task WebSocket API through authenticated Supervisor ingress, creating sessions through HA's supported ingress command. Never disable authentication or expose a dashboard port.

1. Add bounded native client: devices/jobs, compile, install, upload, task readback; no raw source or logs returned. Reconnect by persisted native task IDs; unknown outcomes are not blindly retried.
2. Add private model installation with checksum/TFLite validation, content-addressed local files, target revision CAS and local config before-image. Modify only an existing model ID; preserve Wi-Fi/API/OTA settings verbatim. No arbitrary YAML/shell/URL execution.
3. Expose reads and writes through existing jarvis.admin route plus MCP schema; version3.10.0, explicit firmware_targets addon option. Test native transport, auth redaction, allowlists, concurrency/CAS, persistent job states and source/model rollback boundaries.
4. Review, publish via Git, update addon, authorize the known online terminal, verify native target/config/job reads and perform compile/install through the bridge. Confirm device reconnect; physical wake accuracy remains a separate owner acceptance test.

Implementation: Admin read queries firmware_devices/config/job/jobs; operations firmware_compile/install/model_install/config_restore. Model install affects one existing model source scalar and immutable private assets; YAML anchors/aliases are rejected for this edit. Compile and upload are both checked by native identity, target and dependency. Install requires online target before submission and confirms deployed hash afterward. Native session credentials remain internal.

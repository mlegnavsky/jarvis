# Software audio recovery

Owner rejects physical disconnection and requests autonomous software repair. Continue the existing local conversation design; no microphone recording, idle cloud stream, wake cutoff change or OS/Core upgrade.

1. Add bounded fixed diagnostics: actual synthesized PCM signal and safe agent-response error facts, plus a fixed voice-scoped story probe without fabricated identity or device actions.
2. Add one nonce-bound software audio recovery for the exact Voice PE: use the existing authenticated HA native connection and cached Restart button, require idle output, observe disconnect/reconnect, reassert only the fresh existing volume/mute state. Never factory-reset, expose API credentials, or restart another device. Respect a user-disabled restart entity.
3. RED→GREEN tests for target scoping, zero/mute preservation, absent disconnect, PCM metrics and secret-free response facts; relevant suites and pinned API review. Publish with expected HEAD; CAS/backed-up native component activation, then run no-mic probe/recovery/output test and fixed voice agent test. Report device-state proof separately from acoustic proof.

Pinned interfaces: HA2026.6.4 ESPHome button.py/entry_data.py; aioesphomeapi45.3.1 button_command(key,device_id). A remote software restart is an authorized diagnostic recovery, not proof of the underlying acoustic cause.

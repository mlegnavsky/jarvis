# Software audio recovery

Owner rejects physical disconnection and requests autonomous software repair. Continue the existing local conversation design; no microphone recording, idle cloud stream, wake cutoff change or OS/Core upgrade.

1. Add bounded fixed diagnostics: actual synthesized PCM signal and safe agent-response error facts, plus a fixed voice-scoped story probe without fabricated identity or device actions.
2. Add one nonce-bound software audio recovery for the exact Voice PE: use the existing authenticated HA native connection and cached Restart button, require idle output, observe disconnect/reconnect, reassert only the fresh existing volume/mute state. Never factory-reset, expose API credentials, or restart another device. Respect a user-disabled restart entity.
3. RED→GREEN tests for target scoping, zero/mute preservation, absent disconnect, PCM metrics and secret-free response facts; relevant suites and pinned API review. Publish with expected HEAD; CAS/backed-up native component activation, then run no-mic probe/recovery/output test and fixed voice agent test. Report device-state proof separately from acoustic proof.

Pinned interfaces: HA2026.6.4 ESPHome button.py/entry_data.py; aioesphomeapi45.3.1 button_command(key,device_id). A remote software restart is an authorized diagnostic recovery, not proof of the underlying acoustic cause.

Owner follow-up: audit every voice/TV rule. Live audit found both legacy HomePod fixed-volume automations enabled because their old output sensor is absent in local mode. Disable only these two exact rules through initial_state false and targeted automation reload, preserve the unrelated heating automation, and distinguish this confirmed conflict from the still-inaudible local hardware path.

## Bounded native audio audit

The legacy migration is active_verified with exact readback; both rules off, heating on. PCM is non-silent, software restart and native playback transitions completed, but owner still hears neither speech nor the embedded wake tone. Native decoder/codec evidence is therefore required before another repair.

One task, inline under the existing authorized software repair. Create `native_audit.py` and `test_native_audit.py`; modify fixed control dispatch, component version and tests. `AudioFacts.feed(message)` accepts native log messages but returns only fixed enums and numeric audio facts, never raw lines, URLs, speech, names or credentials. `audit_native(client, playback, restore_level, ...)` subscribes to the existing exact player connection with DEBUG/dump_config, waits one second, runs the existing fixed output test, and restores the HA integration's current expected log level in finally. It never opens a microphone or changes volume/mute/firmware. Total deadline25s,512messages,64unique facts; no persistent raw logs.

RED→GREEN tests: secret-bearing lines and non-audio tags never escape; known decoder/codec errors and numeric format facts survive; message/fact bounds; exact log subscription is removed and previous/current HA log level restored on success, failure and cancellation; native connection mismatch fails before subscribing. Include fixed-control rejection of target/text arguments. Then local duplex suite, manifest/diff, fresh scoped review, public CAS source, storage preflight and one backed-up runtime activation. Live audit must distinguish native errors/configuration from acoustic acceptance.

Review refinement: refuse before request if HA log subscription/native transport DEBUG is already active; exact-device filters on the pinned HA manager/native connection/frame helper loggers protect any mid-audit change and are removed in finally. Only closed ESP error codes survive; any unknown suffix becomes unknown_error.73tests pass after both observed regressions.

# Stock Voice PE coexistence — final firmware implementation report

Firmware product code complete and frozen for root focused review; all final host checks and all three final compiles passed. Scope: firmware/reference_bridge only. No commit, live API call, install, microphone or household action performed.

## Contract and routing

- Required component `reference_server_id`: exact 43 base64url public characters; overlay `${jarvis_reference_server_id}`; fixture dummy is 43 A characters. Existing four native actions unchanged.
- Python existing_player now requires concrete SendspinMediaSource and saves its PlayerRoleListener pointer before installing the adapter listener.
- Stream identity is latched for the complete lifetime as NORMAL / REFERENCE / DROP. Normal foreign server delegates start, PCM, end, volume/mute/delay to stock outside reference mutex. Configured reference server stays silent while unarmed and after cancel/drain/reboot-like startup. Unknown identity drops/yields. Foreign stream during a held lease faults FOREIGN_MEDIA, drops until end, then a subsequent stream may use normal output.
- Normal stream blocks arm before physical output begins; stream_open stays asserted through delegated end callback. In-flight callback/write counters and condition variable serialize write/end without holding the reference mutex while upstream re-enters the mixer/speaker lifecycle. Dropped normal route still closes stock lifecycle.
- Reference arm accepts only configured identity plus current actually paired USER connection. Reference PCM retains exact 48k/stereo16, mute/DAC/amp proof, lease checks, DMA/discard accounting and bounded zero-progress yield outside mutex.
- Removed diagnostics overriding stock codec list/fixed_delay. Removed common unpaired_access override; only legacy explicitly selects false. Removed mixer16 override; normal gate accepts 16..32bits at 48k/stereo, stock mixer inherits32bits while reference always sets 16bits. Stock 480us DAC delay remains a diagnostic and never proves actual reference alignment.

## Test evidence (current)

- RED: stock_adapter_test on real original adapter failed assertion `normal start must reach stock source` (/tmp/stock-adapter-red.log).
- Additional RED: normal identity change suppressed stock end; regression failed `dropped normal route must still close stock lifecycle` (/tmp/stock-adapter-crossing-red.log); fixed using independent stock-start lifetime ownership.
- Additional RED: SDK-permitted main-loop start callback re-entering end deadlocked (20s host timeout; /tmp/stock-adapter-reentrant-end-red.log). Fixed by waiting only concurrent PCM writes in end, retaining all callbacks in arm guard. New regression passes.
- RED: overlay_codegen_test failed missing configured identity setter (/tmp/stock-overlay-red.log).
- RED baseline hub setup prefix extracted from original HEAD fails `diagnostics must preserve stock codec advertisement` (/tmp/stock-hub-red.log). Current extracted prefix passes preserving FLAC/mono/480us (/tmp/stock-hub-green.log).
- GREEN: python3 firmware/reference_bridge/tests/stock_adapter_test.py. Actual production header/methods compiled with host-only SDK/hardware boundaries, real mutex/lease; normal lifecycle/PCM/metadata, identity isolation, cancel/late PCM, foreign lease invalidation, unknown identity, actual gate re-entry from all callbacks, concurrent write/end, main-loop callback reentrant teardown, rearm guard through callback, normal 32bit and strict reference format.
- GREEN: python3 firmware/reference_bridge/tests/audio_write_test.py (UBSAN; 1ms and 10ms ticks); all previous lease/DMA/no-progress cases retained.
- GREEN: UBSAN lease_test.cpp.
- GREEN: /tmp/refbridge-esphome-env/bin/python firmware/reference_bridge/tests/overlay_codegen_test.py; both real overlays with minimal fixtures, listener order/pointer, fixed identity, normal 32bits, stock FLAC+PCM/480us/default unpaired policy.
- Upstream patch regenerated against SHA-verified SDK originals. Applies cleanly and reproduces all 36 vendored files byte-for-byte.

## Builds (current)

- Legacy minimal final compile PASS: /tmp/refbridge-esphome-env/bin/esphome compile /workspace/scratch/698c1908029a/jarvis-echo-measurement/firmware/reference_bridge/compile-fixture.yaml; log /tmp/reference-legacy-stockcompat-build.log; config 0x728dd656; RAM 112691/341760, flash 1128531/8126464; OTA SHA256 b854cc6a118cd32d7a2dbb4dc26ec605cf06e5bc37a95549eaa46a86eba19392.
- Stock minimal final compile PASS: /tmp/refbridge-esphome-env/bin/esphome compile /workspace/scratch/698c1908029a/jarvis-echo-measurement/firmware/reference_bridge/compile-fixture-stock.yaml; log /tmp/reference-stock-stockcompat-build.log; config 0x1ee90bd3; RAM 112755/341760, flash 1135635/8126464; OTA SHA256 da83d7173818ba16e40ddd3b8498c0e84da39b92b34e151375018c5a1b0a58b1.
- Full official default package SHA d4e6fa43d6a1a7d342b7d4d403567e06516719de (original package SHA256 d4e7ab1da4f5b77d1683aa3b47a1ef5b2f1a230b94e37091faab0aa0855908dc) merged with actual stock overlay. Official voice_kit source clone verified exact SHA. Scratch fixture freezes dev sound/component references to that SHA and uses only dummy Wi-Fi/API credentials/public identity. Full final compile PASS: /tmp/reference-full-stock-build.log; config 0x91263d25; RAM 149883/341760, flash 2847423/8126464; OTA SHA256 911c8d2554482e277187990a4082d0dd387648cf014cc9064396eaaaabbeebfa. All three final compiled SDK trees byte-match all seven modified/reference source files, including final reentrant-counter correction. Full generated C++ preserves stock listener order/pointer, FLAC+PCM, default unpaired=true, fixed 480us, mixer 32bit through gate, fixed public identity and native 4 actions.

## Limits

No fixture proves the exact private Green target/wake package, runtime scheduler/heap/DMA timing, actual pairing, acoustic alignment or installed readiness. Exact private target compile remains Green gate; no deployment authorized by these results. Final source, test, overlay, patch, public asset/model, dependency lock, generated C++ and ELF/OTA/factory hashes are recorded in firmware/reference_bridge/build-proof.json. No private target was read or compiled. Public upstream warnings concern voice_kit synchronous annotation, GPIO strapping and deprecated rgb_order; legacy fixture also reports absent display/static pairing code. No compiler error occurred. Root owns integrated project-wide host/addon verification and final focused review.

## Final verification commands

`python3 firmware/reference_bridge/tests/stock_adapter_test.py`; `python3 firmware/reference_bridge/tests/audio_write_test.py`; `python3 firmware/reference_bridge/tests/hub_config_test.py`; `/tmp/refbridge-esphome-env/bin/python firmware/reference_bridge/tests/overlay_codegen_test.py`; UBSAN `lease_test.cpp`; SHA-verified upstream patch application/reconstruction; all three exact compile commands in build-proof.json; `git diff --check -- firmware/reference_bridge`. All passed.

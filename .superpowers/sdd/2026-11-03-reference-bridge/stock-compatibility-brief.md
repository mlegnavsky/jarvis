# Stock Voice PE coexistence — focused implementation brief

Repo /workspace/scratch/698c1908029a/jarvis-echo-measurement. Own ONLY firmware/reference_bridge. Root owns host/addon/tests/docs outside firmware. No commit/live calls/deploy/subagents. Read AGENTS; existing isolated worktree. Report to sibling stock-compatibility-report.md.

## Why
The real device uses official github://esphome/home-assistant-voice-pe/home-assistant-voice.yaml without@ref. Official default dev@d4e6fa43d6a1a7d342b7d4d403567e06516719de inherits SendspinMediaSource; legacy overlay fails duplicate player. Original stock experimental listener replacement silences normal media. Need preserve stock playback while reference stays strictly silent. Existing exact SDK ESPHome2026.10.1, sendspin-cpp0.9.3. Local env /tmp/refbridge-esphome-env. Public full package and merge evidence /tmp/reference-default-package-check. Existing /tmp/refbridge-esp-analysis and vendored source are primary references.

## Fixed identity contract (root implements complementary host/admin)
- Add required component YAML `reference_server_id`: exact43 base64url public server identity (no secrets). All overlays use `${jarvis_reference_server_id}`; fixtures use a fixed43-char public dummy ID.
- Root will prepare stable HA private identity locally onGreen through a generated-only control; stage operation accepts its PUBLIC server_id and injects fixed package variable. Firmware knows this identity from boot; no new native action or NVS storage is needed.
- Existing4 native actions unchanged. arm(generation,owner,duration) accepts only configured public identity and actual paired connection. Unarmed reference-server streams/metadata never delegate to audible stock source, including after cancel/reboot. A different normal server continues upstream behavior when no reference lease is held. Unknown server identity fails closed until known.

## Required stock behavior
- Preserve pointer to existing SendspinMediaSource as PlayerRoleListener, via concrete Python type/dependency then setter, before replacing hub listener. C++ base pointer can invoke its protected overrides through public interface.
- Route whole stream lifetime using explicit route identity: normal foreign server with idle lease delegates start/audio/end and volume/mute to stock listener; configured reference server uses current strict lease/DMA path; unarmed/invalid reference drops with bounded yield; foreign stream during lease invalidates reference and does not acquire normal output until drained/end. Do not mistake later PCM/end callbacks for another generation.
- All forwarded callbacks must run outside reference mutex; stock listener can re-enter mixer/speaker lifecycle. Keep stream_open/rearm guard until delegated end callback completes. Protect crossing stop/end/write; normal active stream must block reference arm even before physical output starts.
- Normal speaker/HTTP playback still goes through gate and preserves output format/mute/volume. Inspect existing16bit mixer override: if required to remove for stock fidelity, gate can accept normal16..32bit audio while reference itself remains strict48k/stereo16. Keep normal format limits compatible with actual public package.
- Do not override stock codec advertisement, fixed DAC delay or unpaired-access policy merely to enable reference diagnostics. Only legacy reference-only path can use fixed PCM-only/zero-delay/unpairedfalse defaults. Native/host reference still requires paired encrypted identity and exact PCM48k; stock's480us fixed delay is diagnostic, not proof of actual reference alignment.
- Preserve current no-progress yield outside mutex and all lease/DMA/discard safeguards.

## Tests and evidence
Write failing behavior regressions first for normal lifecycle/PCM/metadata forwarding; reference-server unarmed/reboot-like startup never delegates; normal stream blocks arm; foreign stream while reference faults/drops; callbacks can acquire gate lock; cancel/late packets cannot become normal; normal codec/delay/policy remain intact. Exercise actual adapter methods using existing extraction/host harness pattern where useful, no test-only product branches. Reproduce failures then fix. Run lease+adapter+overlay tests. Update upstream-hooks.patch for modified upstream hooks.
Compile BOTH minimal fixtures and full official immutable default package+actualstockoverlay with dummycredentials/publicdummyidentity in scratch if merge validates. Full private target/wake files remain Green compile gate. Record hashes/limits in build-proof.json and report. Do not claim acoustic proof or install readiness from fixtures.

## Scope and ruling
This is required compatibility within accepted synchronized-reference plan. HomePod remains sole audible assistant output. New reference stays off for normal conversation. No microphone or household action. This is one implementation task; root will request one focused review of integrated change after completion, no reviewer/subagent dispatch by implementer.

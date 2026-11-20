# Reference transport proof — 2026-11-03

This is a generated-signal software transport test. It does not open microphones,
HomePods, speakers, or house controls. It does not prove speech recognition, human
barge-in, physical DMA timing, acoustic echo cancellation, or reply latency.

The frozen first 240.000699 s run has **pass=false**: the original acceptance
criterion required three independently observed stream/clear events; zero arrived.
The library intentionally coalesces clear followed immediately by end to end.
The experiment is preserved without relaxing its criteria or rewriting its result.

Measured in that same run: 9,541 authenticated encrypted chunks, no mismatched PCM,
no discontinuity, no late reception, and no old-generation frames rendered after
three simulated cancellations. Input queue peak3/8, receiver60/96, sender2.
Software render scheduler p99 lateness1.949ms, maximum16.890ms.
The explicit1.5s presentation lead is **not** conversational reply latency.

Reproduction uses Python3.12, aiosendspin[server]==10.3.0, av16.0.1,
numpy2.3.2 and Pillow12.2.0. The harness has loopback-only socket auditing and
prohibits audio-device opens. `transport-results.json` is its unchanged output.
Copy `transport_simulation.py` into a new empty experiment directory and run it
with the pinned dependencies; it writes results beside the harness and refuses a
second attempt in the same directory. Dependency closure metadata is included
for the separate HA Core2026.6.4/CPython3.14/musllinuxaarch64 resolution proof.

The firmware endpoint requires an explicit native cancel plus physical
speaker-stopped/empty acknowledgement before another generation. Sendspin's
stream/clear and local writer-drained notifications do not provide that proof.


## Actual host-module integration

`integration/` preserves one additional 7.571352 s run of the actual repository
probe, writer and native adapter against official paired/encrypted Sendspin.
It verifies 44.1 to 48 kHz conversion, timestamps, cancellation, rearming and
TaskGroup cleanup. The native service facade, DMA counters and stop ACK were
**simulated**; the nested probe's electrical-output field is synthetic evidence.
See `integration/OUTCOME.md` for measured facts and the teardown warning.
The harness retains the exact original absolute source path and hashes. To
reproduce elsewhere, copy it to a new empty directory, point `SOURCE` to the
provided source snapshot, and install `requirements.lock`; this is a new run,
not a replacement for the frozen result. Original attempt markers are retained.

## Firmware verification

`../../firmware/reference_bridge/build-proof.json` records final compiled inputs,
binary hashes, RAM/flash and the local build-environment workaround. Both pinned
ESPHome 2026.10.1 fixtures compile, and the real overlays pass code generation
against minimal Voice PE ID fixtures. Neither fixture is the installed complete
private device configuration, and neither has been flashed.

## Activation status

Native 1.3.6 and addon 3.12.3 are candidates. Live baseline remains native 1.3.5
and addon 3.12.2. The generated-only endpoint probe is implemented but has not run
on hardware. Ordinary HomePod dialogue is not connected to the new reference;
fast interruption and acoustic cancellation remain unproved and disabled.
Live preflight found 1.6 GiB free against a required 2 GiB backup threshold.
No backup was deleted and no deployment attempted by this change.

Review correction: stock_sendspin staging is now explicitly rejected before any
write because its experimental listener replacement silences normal Sendspin
media. Its YAML/fixture remains a build-only experiment, not a deployable profile.
Only legacy staging is allowed, and exact installed-package compatibility remains
a required compile gate. Review also found and corrected zero-progress callback
busy-loop and HA initialization/probe ownership race. Full review/rulings are in
docs/evidence/2026-11-03-reference-bridge-review.json.

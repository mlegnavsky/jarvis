# Frozen outcome and focused follow-up

The only long run lasted **240.000699 real seconds**. Its original verdict remains **FALSE**. Its predicate required at least three received `stream/clear` events; the observed count was zero. Three `stream/end` events and four starts were received instead. No result or threshold was edited and the run was not repeated.

Other measured long-run results:
- Official aiosendspin 10.3.0 server and client completed real Pairing PSK exchange and used authenticated long-term Noise.
- 9,541 chunks and 10,514,182 PCM frames received; exact byte comparison and contiguous sample checks had zero mismatches. Timestamp error was 0 microseconds.
- Three producer cancellations/new generations; 195,054 scheduled old frames were discarded from the software sink queue. Stale received/rendered frames: 0.
- Late received chunks: 0. Minimum receive lead: 1,452,484 microseconds.
- Software scheduler delay: p99 1,949.48 microseconds; maximum 16,890 microseconds. No claim of hardware/DMA accuracy follows.
- Queue peaks: input 3/8, software sink 60/96, official server queue 2.
- Four generations used long voiced/syllabic synthetic signal sections alternating with exact silence; no microphone, audio device, intelligible TTS, or house service was used.
- Both endpoints shared the host RAW clock and event loop. Independent oscillator drift, WLAN, ESPHome, HomePod, physical output, and AEC were not exercised.

Frozen results SHA-256: `fa69a54634c141cf4ddb3557afc11f8e1e4dba15457c4d4a1860d8ed6cb916c5`.
Frozen harness SHA-256: `38b2f393334d451df762c9940824e5b5f352f3a51e2b3650f6cb8fe11cb06556`.

## Source explanation of the FALSE predicate

Official aiosendspin 10.3.0 `server/connection.py:820-838` documents that `StreamEnd` drops queued, unsent `StreamStart` and `StreamClear`. `_supersede_queued_stream` at lines 871-889 filters those messages. The harness invoked `push.clear()` immediately followed by `await group.stop()`. The end superseded the unsent clear as designed. This does not retroactively turn the long-run verdict into PASS; it narrows what was demonstrated to end/restart transport cancellation.

`server/client.py:899` delegates public `wait_role_drained("player")` to `server/connection.py:642`. That waits while any role queue entry remains or the writer is actively sending that role. The writer signals completion at lines 3693-3701. JSON controls are included, but messages may have been sent OR discarded. A disconnected client returns immediately. This is not receiver processing, I2S stop, or empty-DMA acknowledgement.

Default `push.clear()` calls `PlayerV1Role.on_stream_clear` (`server/roles/player/v1.py:395`), which emits only `stream/clear`. `push.clear(end_roles={role})` explicitly emits end for selected roles instead. Python client `client/connection.py:1717` dispatches clear only to its clear callback; it does not dispatch end or end the current stream.

## One focused real-protocol follow-up

`clear_only.py` was run once separately, after authorization for this focused test. It reused the installed official library and the frozen harness's safe generated-PCM helper, and started no endpoint model. Result: **PASS** for its limited protocol assertions.

- Real long-term Noise authentication.
- One clear arrived and the stream remained active.
- No end was emitted by clear; resumed audio required no additional start.
- Two received chunks exactly matched the expected PCM. The 98 samples left in the pre-clear encoder buffer did not contaminate resumed PCM.
- Public `wait_role_drained` returned after **190 microseconds**, at which point the receiver's clear callback had **not yet run**.
- Receiver clear callback arrived after **589 microseconds**.
- A later explicit `group.stop()` emitted one end.
- The frozen long-run results hash was checked before and after and remained identical.

This is direct observed evidence that local writer drain is not receiver acknowledgement.

## Exact ESP library source audit

ESPHome 2026.10.1's component declares `sendspin/sendspin-cpp` ref `0.9.3`.
Fetched exact tag source:
https://github.com/Sendspin/sendspin-cpp/blob/v0.9.3/src/player_role.cpp

The preserved source `sendspin-cpp-v0.9.3-player_role.cpp` has SHA-256:
`5890f6459f48c597cd2e058146ee4ec50c1e656344bf1d43c8d8bd9c586a78d2`.

At lines 424-440, `handle_stream_clear()` signals the sync task and adds a clear marker. It explicitly provides **no listener callback**, because clear is a seek inside the active stream. Clear therefore does not invoke `on_stream_end()`. A failed marker insertion can also discard some new data along with old data.

At lines 418-422, end signals the sync task and queues a stream-end event. Lines 548-565 defer `listener->on_stream_end()` until the sync task is idle. This is the library boundary, not evidence that a separate downstream I2S hardware queue is stopped and empty.

An endpoint using start/end callbacks must use an explicit generation-matched stop/empty acknowledgement before accepting the next generation; neither clear nor local writer drainage establishes that condition. The actual endpoint/I2S handshake remains outside this experiment and is covered by the root implementation's tests.

## Dependencies and reproducibility

`requirements.lock` records the exact Python 3.12 x86_64 execution environment, retaining the compatible HA pins (AV 16.0.1, NumPy 2.3.2, Pillow 12.2.0). The separate previously completed binary-closure audit proved availability of all 23 corresponding CPython 3.14 musllinux aarch64 wheels under HA Core 2026.6.4 constraints; it did not execute them.

Source metadata, requirement comparisons, exact target wheel versions/hashes, and official HA constraints are preserved beside this evidence bundle. No production repository files were changed.


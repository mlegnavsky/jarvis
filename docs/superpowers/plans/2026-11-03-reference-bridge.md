# Reference bridge implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Deliver a bounded timestamped HomePod reference path and prove its synchronization before enabling acoustic decisions.
**Architecture:** Exact owned RAOP packet tap, integer clock bounds, and a silent terminal reference endpoint. Keep sender timing distinct from actual receiver timing.
**Tech Stack:** Python3.12 host/3.14 Green, pyatv0.17.0, aioesphomeapi45.3.1, ESPHome2026.10.1, Voice PE XMOS.
**Spec:** docs/superpowers/specs/2026-11-03-reference-bridge-design.md

## Global Constraints

- HomePod sole audible assistant output; unchanged command identity permissions.
- Core2026.6.4, no microphone-on during bridge initialization, no private audio in Git.
-200ppm clock bound,2s clock expiry,10ms maximum half-width; unknown receiver latency stays unknown.
- Existing consumed room-test latch is immutable; no silent repeat of its grant.
- Preserve exact media ownership, bounded queues and explicit timing-fault state.

## Review Focus

- RTP wrap/reorder/reset must not reinterpret old audio as a new sample epoch (Task1).
- Tight network RTT does not bound actual receiver render delay (Task1).
- Late data and disconnect must not replay an old generation (Task2).
- DMA discard credits must never count as verified playback (Task2).
- Foreign media/amp changes must not be restored over the owner (Task3).

## Task1: sender sample timeline and clock bounds

Files: managed_sources/local_duplex/reference_timing.py, reference_tap.py,
test_reference_timing.py, test_reference_tap.py.
Interfaces: ClockBounds.observe(boot_id,sent_ns,device_us,received_ns),
ClockBounds.to_device_us(host_ns,now_ns); RaopTimeline.observe_sync(bytes),
RaopTimeline.packet(header,pcm,now_ns) -> immutable timed packet.

- [x] Write failing tests for interval bounds, stale/restarted clocks, NTP/RTP wrap,
      changed epochs, discontinuities and actual big-endian packet data.
- [x] Run targeted tests; expected missing-feature failures.
- [x] Implement integer timing and instance-local owned native tap; receiver
      timing remains unverified even when sender/terminal clocks pass.
- [x] Run targeted tests and duplex suite; expected all passing. Commit.

## Task2: terminal timed PCM endpoint and240s transport proof

Files: firmware/reference_bridge/components/jarvis_reference/*,
firmware/reference_bridge/tests/*, experiments/reference-bridge-20261103/*.
Interfaces: authenticated clock/begin/feed/status/end operations, generation and
sequence identity, bounded PCM queue; DMA acknowledgement or explicit fault.

- [x] Pin concrete upstream interfaces before implementing the endpoint.
- [x] Write RED tests for late packets, overflow, clock restart, cancellation and
      discard-credit rejection. Implement smallest compatible endpoint.
- [x] Compile against exact ESPHome; run240s simulated timestamp/queue scenarios.
      Both fixtures and state tests pass. Frozen240s result remains false for
      clear-event criterion; separate clear-only proof passes. Physical proof pending.
      Published54e9bce; all8CI jobs41646159996 passed. Physical proof pending.

## Task3: activation and measured proof

Files: fixed-target firmware administration capability and native bridge binding,
their regression tests, docs/evidence/2026-11-03-reference-bridge-proof.json.
Interfaces: CAS firmware source/restore, existing native deploy and native API.

- [x] Add only the target-scoped configuration operation the reviewed endpoint
      requires; preserve secrets and existing source bytes. RED/GREEN tests.
- [x] Fresh whole-change review; one critical/important fix pass with regressions.
      Three Important and one Minor accepted; stock staging rejected, firmware
      rejection yields, HA interlock rechecked, actual overlays covered in CI.
- [x] Publish exact tree and pass CI/compile:54e9bce, run41646159996 all8jobs.
- [ ] Backed-up CAS activation and real version/source/timing readback. Perform
      a generated-only silent endpoint test. Blocked by storage/explicit cleanup;
      exact installed package compatibility remains required, stock unsupported.
- [ ] Record receiver/microphone timing and acoustic acceptance separately; keep
      unproved interruption logic disabled and report remaining limitations.

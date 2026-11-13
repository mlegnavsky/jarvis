# Synchronized HomePod reference bridge

Owner accepted implementation on 3 November (request4c928910). Continue inline
in the existing isolated worktree; the prior design-question opt-out and Git/
deployment authorization stand. HomePod is the sole audible assistant output;
human interruption and continuous conversation remain acceptance requirements.

## Approach

Branch the exact generated PCM handed to the owned RAOP protocol, after codec
conversion and final-frame padding. Associate it with the actual outgoing RTP/
NTP synchronization anchor. Map host and terminal monotonic clocks using bounded
round-trip exchanges. Feed a silent digital reference into Voice PE's existing
I2S-to-XMOS path; DAC/amp mute must preserve those digital samples.

Rejected alternatives: the previously rejected FIR/spectral/AEC3 classifiers do
not establish human preservation. Two independent media play calls have no
shared sample timeline. The existing separately decoded16k reference is useful
for observation but is not the actual RAOP PCM and must not be labelled exact.

## Evidence boundary

RTP/NTP supplies a sender presentation timeline, not a receiver DAC timestamp.
HomePod receiver offset and microphone pipeline delay are unbounded by the
current protocol observations. The measured additional382ms is one session's
aggregate observation, not a constant to hard-code as proven. Expose this
uncertainty explicitly. No unknown/expired timing state may enable an acoustic
success flag or fast human-interruption gate.

The1.5s sender setting is not altered in this change. Preserve provider/profile,
command authorization, Core version, existing room-test consumed latch, and
other users' media ownership. Do not open a microphone merely to initialize a
reference transport. A new actual room-test scope must be recorded separately;
the old one-shot grant cannot be replayed or reset.

## Interfaces and failure behavior

Transport taps are instance-local and owned by exactly one asyncio task. Install
before the first audio packet; remove by identity comparison after owner drains.
Only the initialized pinned format is accepted. RTP sequence/timestamp wrap is
valid; dropped/reordered packets, changed clock epoch, format changes, stale
anchors, wall-clock jumps and queue overflow invalidate the reference epoch.

Clock exchanges carry a boot identity and integer microseconds. Offset intervals
include the full round trip and a200ppm drift allowance, expire after2s, and
must stay within10ms half-width. An invalid or restarted clock requires a new
epoch. No float32 or32bit timestamp represents an absolute clock.

The terminal must prove physical DMA completion independently of speaker queue
credits: ESPHome drain_lockstep_ can credit discarded frames as played. A timing
fault must invalidate the epoch. Keep buffers bounded, keep explicit silence
through preroll/tail, stop only owned output, and restore amp/DAC state only
after silence/stop confirmation. Never claim speaker enqueue is physical output.

## Acceptance

1. Exact native sender packets including endian/padding and wrap are verified.
2. A240s deterministic transport simulation exercises clock drift, bounded jitter,
   silence, long speech, interruption/cancellation, restart and delayed packets.
3. A compiled terminal endpoint proves queue/timing fault behavior and an on-device
   generated-only silent reference test verifies the real clock and cleanup.
4. Room echo suppression and short mixed-human preservation are separately measured
   before production fast interruption is enabled. Software timing tests alone do
   not establish acoustic acceptance or a one-second conversational response.

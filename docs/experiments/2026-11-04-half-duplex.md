# HomePod conversation: half duplex, 4 November 2026

Owner explicitly chose to suspend barge-in and echo cancellation to regain
ordinary turn-taking. Archive branch `archive/homepod-duplex-experiments-20261104`
preserves commit `129149e2e1984b83e8fab98a88fd96ce4c80ce7c`, including firmware,
all experiments and existing evidence. Do not replay the consumed room-test grant.

## Evidence and failed paths

- Live 1.3.6 last session: 4 outputs, 2 complete, 2 interrupted, no transport errors.
  Captured 1248 overlap frames. Transcript confirmation did not prevent self-talk.
- Firmware is online on reverted configuration cbdb20ba; no firmware change in
  this repair. Reverting firmware did not remove Green's overlap processing.
- Text echo heuristics accept inaccurate echo transcripts. Rejected spectral,
  acoustic and causal filters can reject humans or amplify artifacts; prior
  results are preserved under experiments/rejected-*.
- Reference bridge simulations did not prove physical HomePod clock alignment.
  Do not activate it based on transport tests alone.
- Continuous PlaybackObserver correlation/waveform measurements added CPU work
  during output. They are removed from ordinary dialogue, without claiming they
  were the independently proved cause of audible distortion.

## Production 1.3.7

HalfDuplexSession is the only ordinary dialogue entry. Incoming microphone bytes
are drained as silence before native VAD while transcribing/thinking/speaking;
completed overlapping input is discarded, never queued. No overlap confirmation,
echo gate, waveform observer, transcript echo classifier or reference bridge is
attached to ordinary dialogue. Human identity/authorization and TV ownership
remain in place. Native microphone transport stays connected: this is input
suppression, not a physical microphone mute.

After output finishes (or raises), the longer of a 600ms tail and the transport latency tail discards residual output, then
normal input resumes. Existing finite provider/source/session bounds remain.
This intentionally cannot interrupt a spoken reply. Provider latency and wake
word acoustic reliability are not claimed fixed by this change.

## Verification

Regression tests cover overlap rejection, no deferred commands while thinking,
raw suppression before VAD, automatic follow-up and recovery after output error.
Legacy tests continue to exercise archived experimental algorithms. Live
activation and output-test outcomes belong in OPEN-WORK and deployment evidence.

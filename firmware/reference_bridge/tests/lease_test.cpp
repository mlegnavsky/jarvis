// Safety/ownership boundary tests run without an ESP or audio devices.
#include "../components/jarvis_reference/lease.h"
#include <cassert>
#include <cmath>
#include <iostream>
using namespace jarvis_reference_core;

Proof good() { return {true, true, true, true, true, true, 100, 6000000}; }
int main() {
  const int64_t t = 6000000;
  {
    Lease x; auto p = good();
    assert(!x.arm(0, t, 1000000, p));
    assert(x.arm(1, t, 1000000, p));
    assert(!x.arm(2, t, 1000000, p)); // no takeover
    assert(!x.can_write());
    assert(x.start(t, p));
    assert(x.can_write());
    assert(x.wrote(1920));
    assert(x.played(480, t + 10000));
    assert(x.completed_frames() == 480);
    assert(!x.cancel(2)); // stale owner cannot cancel
    assert(x.cancel(1));
    assert(!x.can_write());
    x.fail(Fault::DMA_DISCARD); // expected physical discard during explicit cancel
    assert(x.fault() == Fault::NONE);
    assert(!x.release(false, true));
    assert(!x.release(true, false));
    assert(x.release(true, true));
    assert(x.idle());
    assert(!x.arm(1, t, 1000000, p)); // generation may never be reused
    assert(x.arm(2, t, 1000000, p));
  }
  // Every trust, silence and ownership precondition is independently required.
  for (int missing = 0; missing < 6; ++missing) {
    Lease x; auto p = good();
    bool *conditions[] = {&p.connected, &p.paired_owner, &p.time_synced,
                         &p.dac_mute_confirmed, &p.amp_off, &p.output_idle};
    *conditions[missing] = false;
    assert(!x.arm(1, t, 1000000, p));
    assert(x.idle());
  }
  {
    Lease x; auto p = good(); p.clock_error_us = NAN;
    assert(!x.arm(1, t, 1000000, p));
    p = good(); p.clock_error_us = 10001;
    assert(!x.arm(1, t, 1000000, p));
    p = good(); p.sync_at_us = t - 2000001;
    assert(!x.arm(1, t, 1000000, p));
    p = good(); p.sync_at_us = t + 1;
    assert(!x.arm(1, t, 1000000, p));
    p = good(); assert(!x.arm(1, 1000000, 1000000, p)); // boot not settled
    assert(!x.arm(1, t, 245000001, p)); // bounded consent
  }
  {
    Lease x; auto p = good(); assert(x.arm(1, t, 1000000, p));
    assert(x.start(t, p)); assert(x.wrote(1920));
    x.fail(Fault::DMA_DISCARD); // upstream reports this BEFORE its fake playback credit
    assert(!x.played(480, t + 10000));
    assert(x.completed_frames() == 0);
    assert(x.fault() == Fault::DMA_DISCARD);
    assert(!x.can_write());
  }
  {
    Lease x; auto p = good(); assert(x.arm(1, t, 1000000, p));
    assert(x.start(t, p)); assert(!x.wrote(3));
    assert(x.fault() == Fault::PARTIAL_FRAME);
  }
  {
    Lease x; auto p = good(); assert(x.arm(1, t, 1000000, p));
    assert(x.start(t, p)); assert(!x.played(1, t));
    assert(x.fault() == Fault::DMA_ACCOUNTING);
  }
  {
    Lease x; auto p = good(); assert(x.arm(1, t, 1000000, p));
    assert(x.start(t, p)); assert(x.wrote(3840));
    assert(x.played(480, t + 10000));
    assert(!x.played(480, t + 9999)); // DMA clock cannot move backwards
    assert(x.fault() == Fault::DMA_ACCOUNTING);
  }
  {
    Lease x; auto p = good(); assert(x.arm(1, t, 1000000, p));
    assert(x.start(t, p));
    p.connected = false; x.check(t + 1, p);
    assert(!x.can_write()); assert(x.fault() == Fault::TRANSPORT);
    p = good(); x.check(t + 2, p); assert(!x.can_write()); // no automatic resurrection
  }
  {
    Lease x; auto p = good(); assert(x.arm(1, t, 1000000, p));
    assert(x.start(t, p)); x.check(t + 1000000, p);
    assert(x.fault() == Fault::EXPIRED);
  }
  {
    Lease x; auto p = good(); assert(x.arm(1, t, 1000000, p));
    assert(x.start(t, p)); assert(!x.start(t + 1, p));
    assert(x.fault() == Fault::UNEXPECTED_STREAM);
  }
  {
    Lease x; auto p = good(); assert(x.arm(1, t, 1000000, p));
    assert(x.start(t, p)); x.fail(Fault::FOREIGN_MEDIA);
    assert(!x.idle()); assert(!x.release(true, false));
    assert(x.release(true, true)); assert(x.idle());
    assert(x.fault() == Fault::FOREIGN_MEDIA); // observable after cleanup
  }
  // Long input: credit each 10 ms DMA block; old generations never resume.
  {
    Lease x; auto p = good(); assert(x.arm(1, t, 241000000, p)); assert(x.start(t, p));
    for (int i = 0; i < 24000; ++i) {
      int64_t now = t + (i + 1) * 10000LL; p.sync_at_us = now;
      x.check(now, p); assert(x.wrote(1920)); assert(x.played(480, now));
    }
    assert(x.completed_frames() == 11520000);
    assert(x.cancel(1)); assert(!x.played(480, t + 240010000));
  }
  {
    SignalCounters signal;
    uint8_t pcm[1920]{}; pcm[4 * 23] = 1;
    signal.wrote(pcm, sizeof(pcm), 0);
    assert(signal.nonzero_frames == 1); assert(signal.first_signal_frame == 24);
    signal.played(0, 480, 1000000);
    assert(signal.first_signal_dma_us == 990500); // 456 frames before descriptor end
    signal.played(480, 480, 1010000);
    assert(signal.first_signal_dma_us == 990500);
    assert(sizeof(SignalCounters) <= 32); // counters retain no PCM
  }
  std::cout << "lease: all ownership, silence, DMA and 240 s state scenarios passed\n";
}

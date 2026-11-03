// Executes the actual adapter method body, with host substitutes only for
// ESP timer, I2S writes and FreeRTOS scheduling. Lease and mutex stay real.
#include "lease.h"
#include <algorithm>
#include <cassert>
#include <functional>
#include <iostream>
#include <mutex>
#include <thread>

using TickType_t = uint32_t;
static constexpr uint32_t TICK_MS = TEST_TICK_MS;
#define pdMS_TO_TICKS(ms) ((ms) / TICK_MS)
static int64_t now_us = 6000000;
int64_t esp_timer_get_time() { return now_us; }
static std::function<void(TickType_t)> on_delay;
void vTaskDelay(TickType_t ticks) { on_delay(ticks); }

struct Output {
  size_t accepted{0};
  unsigned writes{0};
  size_t play(uint8_t *, size_t, TickType_t) { ++writes; return accepted; }
};
struct ReferenceSpeaker {
  using Fault = jarvis_reference_core::Fault;
  std::mutex mutex_;
  jarvis_reference_core::Lease lease_;
  jarvis_reference_core::SignalCounters signal_;
  jarvis_reference_core::Proof cached_{true, true, true, true, true, true, 100, 6000000};
  int64_t checked_at_{6000000}, last_write_at_{0};
  Output output;
  Output *output_{&output};
  void fail_(Fault fault) { lease_.fail(fault); }
  size_t on_audio_write(uint8_t *, size_t, uint32_t);
};
#include ADAPTER_WRITE_IMPL

static void active(ReferenceSpeaker &s) {
  assert(s.lease_.arm(1, now_us, 1000000, s.cached_));
  assert(s.lease_.start(now_us, s.cached_));
}

static void rejection(ReferenceSpeaker &s, size_t length, uint32_t timeout) {
  unsigned delays = 0;
  on_delay = [&](TickType_t ticks) {
    ++delays;
    assert(ticks >= 1 && ticks * TICK_MS <= 10);
    bool acquired = false;
    std::thread main_loop([&]() {
      acquired = s.mutex_.try_lock();
      if (acquired) {
        s.lease_.cancel(s.lease_.generation());
        s.mutex_.unlock();
      }
    });
    main_loop.join();
    assert(acquired && "rejected writer must release mutex before delaying");
  };
  uint8_t pcm[8]{};
  assert(s.on_audio_write(pcm, length, timeout) == 0);
  assert(delays == 1 && "zero-progress write must block at least one tick");
}

int main() {
  // Removing any rejection delay, or delaying while holding the mutex, fails.
  for (uint32_t timeout : {0u, 1u, 10u, 1000u}) {
    ReferenceSpeaker idle;
    rejection(idle, 8, timeout);
    assert(idle.output.writes == 0);
    ReferenceSpeaker draining; active(draining); draining.lease_.cancel(1);
    rejection(draining, 8, timeout);
    assert(draining.output.writes == 0);
  }
  { ReferenceSpeaker armed; assert(armed.lease_.arm(1, now_us, 1000000, armed.cached_));
    rejection(armed, 8, 10); assert(armed.output.writes == 0); }
  { ReferenceSpeaker stale; active(stale); stale.checked_at_ -= 150001;
    rejection(stale, 8, 10); assert(stale.lease_.fault() == ReferenceSpeaker::Fault::CLOCK); }
  { ReferenceSpeaker expired; active(expired); now_us += 1000000;
    expired.checked_at_ = now_us; rejection(expired, 8, 10);
    assert(expired.lease_.fault() == ReferenceSpeaker::Fault::EXPIRED); now_us -= 1000000; }
  { ReferenceSpeaker unmuted; active(unmuted); unmuted.cached_.dac_mute_confirmed = false;
    rejection(unmuted, 8, 10); assert(unmuted.lease_.fault() == ReferenceSpeaker::Fault::SILENCE); }
  { ReferenceSpeaker partial_frame; active(partial_frame);
    rejection(partial_frame, 3, 10); assert(partial_frame.output.writes == 0);
    assert(partial_frame.lease_.fault() == ReferenceSpeaker::Fault::PARTIAL_FRAME); }
  { ReferenceSpeaker full; active(full); rejection(full, 8, 10);
    assert(full.output.writes == 1); assert(full.lease_.submitted_frames() == 0); }
  // A positive partial physical write keeps its old return and accounting,
  // without an extra scheduler delay.
  { ReferenceSpeaker partial; active(partial); partial.output.accepted = 4;
    on_delay = [](TickType_t) { assert(false && "positive progress must not delay"); };
    uint8_t pcm[8]{1};
    assert(partial.on_audio_write(pcm, sizeof(pcm), 10) == 4);
    assert(partial.lease_.submitted_frames() == 1);
    assert(partial.signal_.nonzero_frames == 1); }
  { ReferenceSpeaker malformed; active(malformed); malformed.output.accepted = 3;
    uint8_t pcm[8]{};
    assert(malformed.on_audio_write(pcm, sizeof(pcm), 10) == 3);
    assert(malformed.lease_.fault() == ReferenceSpeaker::Fault::PARTIAL_FRAME); }
  std::cout << "audio_write: rejected paths yield outside mutex; partial progress unchanged\n";
}

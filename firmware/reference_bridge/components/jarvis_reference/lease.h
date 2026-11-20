#pragma once
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <limits>

namespace jarvis_reference_core {
// Caller serializes all methods. The SDK adapter holds the same mutex through
// the physical write, so release cannot race a previously admitted writer.
enum class State : uint8_t { IDLE, ARMED, ACTIVE, DRAINING };
enum class Fault : uint8_t {
  NONE, TRANSPORT, CLOCK, SILENCE, EXPIRED, UNEXPECTED_STREAM,
  DMA_DISCARD, DMA_ACCOUNTING, PARTIAL_FRAME, FOREIGN_MEDIA, WRITE_STALL, FORMAT
};
struct Proof {
  bool connected, paired_owner, time_synced, dac_mute_confirmed, amp_off, output_idle;
  float clock_error_us;
  int64_t sync_at_us;
};

// Constant-size signal counters. No input/reference audio is stored here.
struct SignalCounters {
  uint64_t nonzero_frames{0}, first_signal_frame{0};
  int64_t first_signal_dma_us{0};
  void wrote(const uint8_t *pcm, size_t bytes, uint64_t previous_frames) {
    for (size_t i = 0; i + 3 < bytes; i += 4) {
      if (pcm[i] || pcm[i+1] || pcm[i+2] || pcm[i+3]) {
        ++nonzero_frames;
        if (!first_signal_frame) first_signal_frame = previous_frames + i / 4 + 1;
      }
    }
  }
  void played(uint64_t before, uint32_t frames, int64_t when) {
    if (!first_signal_dma_us && first_signal_frame > before &&
        first_signal_frame <= before + frames)
      first_signal_dma_us = when - int64_t((before + frames - first_signal_frame) * 1000000 / 48000);
  }
};

class Lease {
 public:
  bool arm(uint32_t generation, int64_t now, int64_t duration, const Proof &p) {
    if (!idle() || generation <= generation_ || now < 5000000 || duration <= 0 ||
        duration > 245000000 || now > INT64_MAX - duration || !p.output_idle ||
        proof_fault(now, p) != Fault::NONE) return false;
    generation_ = generation; expires_ = now + duration; state_ = State::ARMED;
    fault_ = Fault::NONE; submitted_ = completed_ = 0; last_dma_us_ = 0;
    return true;
  }
  bool start(int64_t now, const Proof &p) {
    if (state_ != State::ARMED) { fail(Fault::UNEXPECTED_STREAM); return false; }
    check(now, p);
    if (state_ != State::ARMED) return false;
    state_ = State::ACTIVE; return true;
  }
  void check(int64_t now, const Proof &p) {
    if (idle() || state_ == State::DRAINING) return;
    if (now >= expires_) { fail(Fault::EXPIRED); return; }
    auto reason = proof_fault(now, p);
    if (reason != Fault::NONE) fail(reason);
  }
  bool wrote(size_t bytes) {
    if (!can_write()) return false;
    if (bytes % 4) { fail(Fault::PARTIAL_FRAME); return false; }
    if (bytes / 4 > UINT64_MAX - submitted_) { fail(Fault::DMA_ACCOUNTING); return false; }
    submitted_ += bytes / 4; return true;
  }
  bool played(uint32_t frames, int64_t when) {
    if (!can_write()) return false;
    if (when <= 0 || when < last_dma_us_ || frames > submitted_ - completed_) {
      fail(Fault::DMA_ACCOUNTING); return false;
    }
    completed_ += frames; last_dma_us_ = when; return true;
  }
  bool cancel(uint32_t generation) {
    if (idle() || generation != generation_) return false;
    state_ = State::DRAINING; return true;
  }
  void fail(Fault reason) {
    if (idle() || draining()) return;
    if (fault_ == Fault::NONE) fault_ = reason;
    state_ = State::DRAINING;
  }
  bool release(bool physical_stopped, bool no_buffered_data) {
    if (state_ != State::DRAINING || !physical_stopped || !no_buffered_data) return false;
    state_ = State::IDLE; return true;
  }
  bool idle() const { return state_ == State::IDLE; }
  bool can_write() const { return state_ == State::ACTIVE; }
  bool draining() const { return state_ == State::DRAINING; }
  uint32_t generation() const { return generation_; }
  uint64_t completed_frames() const { return completed_; }
  uint64_t submitted_frames() const { return submitted_; }
  int64_t last_dma_us() const { return last_dma_us_; }
  State state() const { return state_; }
  Fault fault() const { return fault_; }
 private:
  static Fault proof_fault(int64_t now, const Proof &p) {
    if (!p.connected || !p.paired_owner) return Fault::TRANSPORT;
    // The library's Kalman error is a diagnostic, NOT a certified bound on
    // clock offset or HomePod acoustic timing. No acoustic-ready flag exists.
    if (!p.time_synced || !std::isfinite(p.clock_error_us) ||
        std::abs(p.clock_error_us) > 10000 || p.sync_at_us <= 0 ||
        p.sync_at_us > now || now - p.sync_at_us > 2000000) return Fault::CLOCK;
    if (!p.dac_mute_confirmed || !p.amp_off) return Fault::SILENCE;
    return Fault::NONE;
  }
  State state_{State::IDLE};
  Fault fault_{Fault::NONE};
  uint32_t generation_{0};
  int64_t expires_{0}, last_dma_us_{0};
  uint64_t submitted_{0}, completed_{0};
};
}  // namespace jarvis_reference_core

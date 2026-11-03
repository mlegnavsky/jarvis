#include "jarvis_reference.h"
#include <algorithm>
#include <cstdio>
#include <esp_timer.h>
#include <esp_random.h>

namespace esphome::jarvis_reference {
void ReferenceSpeaker::setup() {
  boot_id_ = esp_random();
  volume_ = output_->get_volume(); mute_state_ = output_->get_mute_state();
  output_->add_audio_output_callback([this](uint32_t n, int64_t t) { dma_(n, t); });
  output_->add_dma_discard_callback([this]() {
    std::lock_guard<std::mutex> lock(mutex_); fail_(Fault::DMA_DISCARD);
  });
  amp_->add_on_state_callback([this](bool) {
    if (changing_amp_.load()) return;
    std::lock_guard<std::mutex> lock(mutex_);
    if (!lease_.idle()) {
      restore_amp_ = false; // do not restore over a foreign writer
      fail_(Fault::SILENCE);
    }
  });
}
::jarvis_reference_core::Proof ReferenceSpeaker::proof_() {
  return {hub_->reference_connected(), hub_->reference_paired_owner(owner_),
          hub_->reference_time_synced() && hub_->get_player_role(), mute_confirmed_ && dac_->is_muted(),
          !amp_->state, output_->is_stopped() && !output_->has_buffered_data(),
          hub_->reference_sync_error(), hub_->reference_sync_at()};
}
void ReferenceSpeaker::amp_off_() {
  changing_amp_.store(true); amp_->turn_off(); changing_amp_.store(false);
}
bool ReferenceSpeaker::arm(uint32_t generation, const std::string &server_id, uint32_t duration_ms) {
  std::lock_guard<std::mutex> lock(mutex_);
  if (!lease_.idle() || stream_open_ || stock_callbacks_ || !output_->is_stopped() || output_->has_buffered_data() ||
      reference_server_id_.empty() || server_id != reference_server_id_ || duration_ms == 0 || duration_ms > 245000 ||
      generation <= lease_.generation() || esp_timer_get_time() < 5000000) return false;
  owner_ = server_id;
  if (!hub_->reference_paired_owner(owner_)) { owner_.clear(); return false; }
  saved_amp_ = amp_->state; restore_amp_ = true;
  output_->set_mute_state(true); // keep future speaker startup muted as well
  mute_confirmed_ = dac_->set_mute_on(); // actual I2C result, not merely cached mute
  amp_off_();
  cached_ = proof_(); checked_at_ = esp_timer_get_time();
  if (!lease_.arm(generation, checked_at_, int64_t(duration_ms) * 1000, cached_)) {
    restore_(); return false;
  }
  output_->set_audio_stream_info(audio::AudioStreamInfo(16, 2, 48000));
  stop_requested_ = false; last_write_at_ = 0; signal_ = {};
  return true;
}
bool ReferenceSpeaker::cancel(uint32_t generation) {
  std::lock_guard<std::mutex> lock(mutex_); return lease_.cancel(generation);
}
void ReferenceSpeaker::fail_(Fault fault) { lease_.fail(fault); }
void ReferenceSpeaker::restore_() {
  // Must never be called while reference PCM can still reach the DAC.
  output_->set_volume(volume_); output_->set_mute_state(mute_state_);
  if (restore_amp_ && saved_amp_ && !amp_->state) {
    changing_amp_.store(true); amp_->turn_on(); changing_amp_.store(false);
  }
  mute_confirmed_ = false; restore_amp_ = false; owner_.clear();
}
void ReferenceSpeaker::loop() {
  std::lock_guard<std::mutex> lock(mutex_);
  const int64_t now = esp_timer_get_time();
  if (!lease_.idle()) {
    cached_ = proof_(); checked_at_ = now; lease_.check(now, cached_);
    if (lease_.draining()) {
      if (!stop_requested_) { output_->stop(); stop_requested_ = true; }
      if (lease_.release(output_->is_stopped(), !output_->has_buffered_data())) restore_();
    }
  }
  state_ = output_->is_stopped() ? speaker::STATE_STOPPED :
           output_->is_running() ? speaker::STATE_RUNNING : speaker::STATE_STARTING;
}
void ReferenceSpeaker::on_shutdown() {
  std::lock_guard<std::mutex> lock(mutex_);
  if (!lease_.idle()) { lease_.cancel(lease_.generation()); output_->stop(); }
  // No restoration here: asynchronous stop has not yet been acknowledged.
}
void ReferenceSpeaker::on_stream_start() {
  std::unique_lock<std::mutex> lock(mutex_);
  // Route belongs to this complete stream lifetime, never to the current lease.
  // The SDK delivers lifecycle events on the main loop; PCM is concurrent.
  if (stream_open_) { fail_(Fault::UNEXPECTED_STREAM); return; }
  stream_open_ = true;
  stream_owner_ = hub_->reference_server_id();
  route_ = Route::DROP;
  if (stream_owner_.empty()) { fail_(Fault::TRANSPORT); return; }
  if (stream_owner_ != reference_server_id_) {
    if (!lease_.idle()) { fail_(Fault::FOREIGN_MEDIA); return; }
    if (!stock_listener_) return;
    route_ = Route::NORMAL; stock_stream_started_ = true; ++stock_callbacks_;
    lock.unlock(); stock_listener_->on_stream_start(); stock_done_(); return;
  }
  if (lease_.idle()) return; // A configured reference server never becomes audible.
  route_ = Route::REFERENCE;
  cached_ = proof_(); checked_at_ = esp_timer_get_time();
  const auto &params = hub_->get_player_role()->get_current_stream_params();
  if (params.codec != sendspin::SendspinCodecFormat::PCM || params.sample_rate != 48000 ||
      params.bit_depth != 16 || params.channels != 2) {
    fail_(Fault::FORMAT); return;
  }
  if (lease_.start(checked_at_, cached_)) stream_generation_ = lease_.generation();
}
void ReferenceSpeaker::on_stream_end() {
  std::unique_lock<std::mutex> lock(mutex_);
  if (!stream_open_) return;
  const bool normal = stock_stream_started_;
  route_ = Route::DROP; // stop admitting PCM before waiting for any in-flight write
  lease_.cancel(stream_generation_); stream_generation_ = 0;
  // Only PCM runs concurrently. Main-loop callbacks may re-enter teardown;
  // waiting for those would wait on our own stack. They still block arm().
  stock_idle_.wait(lock, [this]() { return stock_writes_ == 0; });
  if (normal) {
    // Retain stream_open_ until upstream stop/end has completed, including its
    // reentrant mixer calls. No new reference lease may cross this callback.
    lock.unlock(); stock_listener_->on_stream_end(); lock.lock();
  }
  stream_open_ = false; stock_stream_started_ = false; route_ = Route::NONE; stream_owner_.clear();
}
void ReferenceSpeaker::stock_done_(bool audio_write) {
  std::lock_guard<std::mutex> lock(mutex_);
  --stock_callbacks_;
  if (audio_write) --stock_writes_;
  if (stock_writes_ == 0) stock_idle_.notify_all();
}
bool ReferenceSpeaker::stock_metadata_() {
  if (!stock_listener_ || !lease_.idle()) return false;
  const auto identity = hub_->reference_server_id();
  if (identity.empty() || identity == reference_server_id_) return false;
  if (stream_open_ && (route_ != Route::NORMAL || identity != stream_owner_)) return false;
  ++stock_callbacks_; return true;
}
void ReferenceSpeaker::on_volume_changed(uint8_t volume) {
  { std::lock_guard<std::mutex> lock(mutex_); if (!stock_metadata_()) return; }
  stock_listener_->on_volume_changed(volume); stock_done_();
}
void ReferenceSpeaker::on_mute_changed(bool muted) {
  { std::lock_guard<std::mutex> lock(mutex_); if (!stock_metadata_()) return; }
  stock_listener_->on_mute_changed(muted); stock_done_();
}
void ReferenceSpeaker::on_output_delay_changed(uint16_t delay_ms) {
  // Preserve the stock listener's delay behavior; delay is diagnostic, never
  // proof of reference alignment. A reference stream still uses exact PCM.
  { std::lock_guard<std::mutex> lock(mutex_); if (!stock_metadata_()) return; }
  stock_listener_->on_output_delay_changed(delay_ms); stock_done_();
}
size_t ReferenceSpeaker::on_audio_write(uint8_t *data, size_t length, uint32_t timeout_ms) {
  std::unique_lock<std::mutex> lock(mutex_);
  const auto no_progress = [&]() -> size_t {
    // Sendspin retries zero-progress writes without yielding. Let cancellation
    // and the main loop run, without holding the lease lock while blocked.
    lock.unlock();
    vTaskDelay(std::max<TickType_t>(1, pdMS_TO_TICKS(std::min<uint32_t>(timeout_ms, 10))));
    return 0;
  };
  if (route_ == Route::NORMAL && stream_open_) {
    if (hub_->reference_server_id() != stream_owner_ || !lease_.idle()) {
      fail_(Fault::FOREIGN_MEDIA); route_ = Route::DROP; return no_progress();
    }
    ++stock_callbacks_; ++stock_writes_; lock.unlock();
    const size_t n = stock_listener_->on_audio_write(data, length, timeout_ms);
    stock_done_(true);
    if (!n) vTaskDelay(std::max<TickType_t>(1, pdMS_TO_TICKS(std::min<uint32_t>(timeout_ms, 10))));
    return n;
  }
  if (route_ != Route::REFERENCE || !stream_open_) return no_progress();
  if (hub_->reference_server_id() != stream_owner_) {
    fail_(Fault::FOREIGN_MEDIA); route_ = Route::DROP; return no_progress();
  }
  const int64_t now = esp_timer_get_time();
  if (now < checked_at_ || now - checked_at_ > 150000) fail_(Fault::CLOCK);
  lease_.check(now, cached_);
  if (!lease_.can_write()) return no_progress();
  if (length % 4) { fail_(Fault::PARTIAL_FRAME); return no_progress(); }
  size_t n = output_->play(data, length, pdMS_TO_TICKS(std::min<uint32_t>(timeout_ms, 10)));
  const uint64_t before_frames = lease_.submitted_frames();
  if (!lease_.wrote(n)) return n ? n : no_progress();
  signal_.wrote(data, n, before_frames);
  if (n) last_write_at_ = now;
  else if (last_write_at_ && now - last_write_at_ > 250000) fail_(Fault::WRITE_STALL);
  return n ? n : no_progress();
}
void ReferenceSpeaker::dma_(uint32_t frames, int64_t when) {
  bool normal = false;
  {
    std::lock_guard<std::mutex> lock(mutex_);
    normal = lease_.idle();
    const uint64_t before_frames = lease_.completed_frames();
    if (lease_.played(frames, when)) {
      signal_.played(before_frames, frames, when);
      // notify_audio_played only merges a mailbox; it cannot call this adapter.
      // Keep the lease mutex until credit is posted, before stop/rearm can ACK.
      if (auto *role = hub_->get_player_role()) role->notify_audio_played(frames, when);
    }
  }
  if (normal) audio_output_callback_(frames, when);
}
bool ReferenceSpeaker::normal_() {
  if (lease_.idle()) return true;
  fail_(Fault::FOREIGN_MEDIA); return false;
}
size_t ReferenceSpeaker::play(const uint8_t *data, size_t length, TickType_t wait) {
  std::lock_guard<std::mutex> lock(mutex_);
  if (!normal_()) return 0;
  output_->set_audio_stream_info(audio_stream_info_);
  return output_->play(data, length, std::min(wait, pdMS_TO_TICKS(10)));
}
void ReferenceSpeaker::start() {
  std::lock_guard<std::mutex> lock(mutex_);
  if (normal_()) { output_->set_audio_stream_info(audio_stream_info_); output_->start(); }
}
void ReferenceSpeaker::stop() {
  std::lock_guard<std::mutex> lock(mutex_);
  if (normal_()) output_->stop();
}
void ReferenceSpeaker::finish() {
  std::lock_guard<std::mutex> lock(mutex_);
  if (normal_()) output_->finish();
}
bool ReferenceSpeaker::has_buffered_data() const {
  std::lock_guard<std::mutex> lock(mutex_); return output_->has_buffered_data();
}
void ReferenceSpeaker::set_volume(float value) {
  std::lock_guard<std::mutex> lock(mutex_);
  volume_ = value; if (lease_.idle()) output_->set_volume(value);
}
void ReferenceSpeaker::set_mute_state(bool value) {
  std::lock_guard<std::mutex> lock(mutex_);
  mute_state_ = value; if (lease_.idle()) output_->set_mute_state(value);
}
std::string ReferenceSpeaker::status_json() {
  std::lock_guard<std::mutex> lock(mutex_);
  char b[768];
  std::snprintf(b, sizeof(b),
    "{\"schema\":1,\"boot_id\":%lu,\"stream_open\":%s,\"generation\":%lu,\"state\":%u,\"fault\":%u,"
    "\"submitted_frames\":%llu,\"dma_frames\":%llu,\"last_dma_us\":%lld,"
    "\"clock_us\":%lld,\"muted\":%s,\"physical_stopped\":%s,\"buffer_empty\":%s,"
    "\"nonzero_frames\":%llu,\"first_signal_dma_us\":%lld,\"receiver_timing_verified\":false,\"acoustic_verified\":false}",
    static_cast<unsigned long>(boot_id_), stream_open_ ? "true" : "false",
    static_cast<unsigned long>(lease_.generation()), unsigned(lease_.state()), unsigned(lease_.fault()),
    static_cast<unsigned long long>(lease_.submitted_frames()),
    static_cast<unsigned long long>(lease_.completed_frames()),
    static_cast<long long>(lease_.last_dma_us()), static_cast<long long>(esp_timer_get_time()),
    mute_confirmed_ && dac_->is_muted() && !amp_->state ? "true" : "false",
    output_->is_stopped() ? "true" : "false",
    !output_->has_buffered_data() ? "true" : "false",
    static_cast<unsigned long long>(signal_.nonzero_frames), static_cast<long long>(signal_.first_signal_dma_us));
  return b;
}
}  // namespace esphome::jarvis_reference

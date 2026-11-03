#pragma once
// GPL-3.0; see ../../ESPHome-LICENSE. Reference-only extension, 2026-11-03.
#include "lease.h"
#include "esphome/core/component.h"
#include "esphome/components/audio_dac/audio_dac.h"
#include "esphome/components/i2s_audio/speaker/i2s_audio_speaker_standard.h"
#include "esphome/components/sendspin/sendspin_hub.h"
#include "esphome/components/speaker/speaker.h"
#include "esphome/components/switch/switch.h"
#include <atomic>
#include <mutex>
#include <string>

namespace esphome::jarvis_reference {
class ReferenceSpeaker final : public Component, public speaker::Speaker, public sendspin::PlayerRoleListener {
 public:
  float get_setup_priority() const override { return sendspin_::sendspin_priority::CHILD; }
  void setup() override;
  void loop() override;
  void on_shutdown() override;
  void set_output_speaker(i2s_audio::I2SAudioSpeaker *v) { output_ = v; }
  void set_dac_id(audio_dac::AudioDac *v) { dac_ = v; }
  void set_amplifier_id(switch_::Switch *v) { amp_ = v; }
  void set_sendspin_id(sendspin_::SendspinHub *v) { hub_ = v; }
  // Expose only through encrypted, target-scoped native API actions. Default idle.
  bool arm(uint32_t generation, const std::string &server_id, uint32_t duration_ms);
  bool cancel(uint32_t generation);
  std::string status_json();

  // The ordinary mixer MUST use this gate, never the physical speaker directly.
  size_t play(const uint8_t *data, size_t length) override { return play(data, length, 0); }
  size_t play(const uint8_t *data, size_t length, TickType_t wait) override;
  void start() override;
  void stop() override;
  void finish() override;
  bool has_buffered_data() const override;
  void set_volume(float volume) override;
  void set_mute_state(bool muted) override;

  size_t on_audio_write(uint8_t *data, size_t length, uint32_t timeout_ms) override;
  void on_stream_start() override;
  void on_stream_end() override;
  void on_volume_changed(uint8_t) override {} // Never unmute/change reference samples.
  void on_mute_changed(bool) override {}
  void on_output_delay_changed(uint16_t delay_ms) override;
 private:
  using Fault = ::jarvis_reference_core::Fault;
  ::jarvis_reference_core::Proof proof_(); // main loop only
  void fail_(Fault fault); // mutex held
  bool normal_(); // mutex held
  void restore_(); // only after physical stop and empty buffer
  void amp_off_();
  void dma_(uint32_t frames, int64_t when);
  i2s_audio::I2SAudioSpeaker *output_{nullptr};
  audio_dac::AudioDac *dac_{nullptr};
  switch_::Switch *amp_{nullptr};
  sendspin_::SendspinHub *hub_{nullptr};
  mutable std::mutex mutex_;
  ::jarvis_reference_core::Lease lease_;
  ::jarvis_reference_core::SignalCounters signal_;
  ::jarvis_reference_core::Proof cached_{};
  int64_t checked_at_{0}, last_write_at_{0};
  std::string owner_;
  bool mute_confirmed_{false}, saved_amp_{false}, restore_amp_{false};
  bool stop_requested_{false}, stream_open_{false};
  uint32_t stream_generation_{0}, boot_id_{0};
  std::atomic<bool> changing_amp_{false};
};
}  // namespace esphome::jarvis_reference

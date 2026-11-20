// Hardware and SDK boundaries only; production adapter and lease are compiled.
#include <algorithm>
#include <atomic>
#include <cassert>
#include <condition_variable>
#include <cstdio>
#include <functional>
#include <iostream>
#include <mutex>
#include <string>
#include <thread>
#include <vector>
#include "lease.h"
using TickType_t = uint32_t;
#define pdMS_TO_TICKS(ms) (TickType_t(ms))
static int64_t now_us = 6000000;
int64_t esp_timer_get_time() { return now_us; }
uint32_t esp_random() { return 123; }
static std::function<void()> delay_hook = [] {};
static unsigned delays = 0;
void vTaskDelay(TickType_t ticks) { assert(ticks > 0 && ticks <= 10); ++delays; delay_hook(); }
namespace sendspin {
enum class SendspinCodecFormat { PCM, FLAC };
struct Params { SendspinCodecFormat codec{SendspinCodecFormat::PCM}; int sample_rate{48000}, bit_depth{16}, channels{2}; };
class PlayerRoleListener {
 public:
  virtual ~PlayerRoleListener() = default;
  virtual size_t on_audio_write(uint8_t *, size_t, uint32_t) = 0;
  virtual void on_stream_start() {}
  virtual void on_stream_end() {}
  virtual void on_volume_changed(uint8_t) {}
  virtual void on_mute_changed(bool) {}
  virtual void on_output_delay_changed(uint16_t) {}
};
struct Role {
  Params params;
  unsigned credits{0};
  const Params &get_current_stream_params() const { return params; }
  uint16_t get_output_delay_ms() const { return 0; }
  void notify_audio_played(uint32_t, int64_t) { ++credits; }
};
}
namespace esphome {
class Component { public: virtual ~Component() = default; virtual float get_setup_priority() const { return 0; }
  virtual void setup() {} virtual void loop() {} virtual void on_shutdown() {} };
namespace audio { struct AudioStreamInfo { int bits, channels, rate; AudioStreamInfo(int b=16,int c=2,int r=48000):bits(b),channels(c),rate(r){} }; }
namespace speaker {
enum State { STATE_STOPPED, STATE_RUNNING, STATE_STARTING };
class Speaker { public:
  virtual ~Speaker() = default;
  virtual size_t play(const uint8_t *,size_t)=0;
  virtual size_t play(const uint8_t *,size_t,TickType_t)=0;
  virtual void start()=0; virtual void stop()=0; virtual void finish()=0;
  virtual bool has_buffered_data() const=0;
  virtual void set_volume(float v) { volume_=v; } virtual void set_mute_state(bool v) { mute_state_=v; }
  float volume_{0.5f}; bool mute_state_{false}; State state_{STATE_STOPPED}; audio::AudioStreamInfo audio_stream_info_;
  std::function<void(uint32_t,int64_t)> audio_output_callback_=[](uint32_t,int64_t){};
}; }
namespace audio_dac { struct AudioDac { bool muted{false}; bool is_muted() const{return muted;} bool set_mute_on(){muted=true;return true;} }; }
namespace switch_ { struct Switch { bool state{false}; std::function<void(bool)> callback=[](bool){};
  void turn_on(){state=true;callback(true);} void turn_off(){state=false;callback(false);}
  void add_on_state_callback(std::function<void(bool)> cb){callback=cb;} }; }
namespace i2s_audio { struct I2SAudioSpeaker {
  bool stopped{true}, buffered{false}, muted{false}; float volume{0.5}; unsigned writes{0}; audio::AudioStreamInfo info;
  std::function<void(uint32_t,int64_t)> dma; std::function<void()> discard;
  float get_volume() const{return volume;} bool get_mute_state() const{return muted;}
  void set_volume(float v){volume=v;} void set_mute_state(bool v){muted=v;}
  bool is_stopped() const{return stopped;} bool is_running() const{return !stopped;}
  bool has_buffered_data() const{return buffered;}
  void stop(){stopped=true;buffered=false;} void start(){stopped=false;} void finish(){stop();}
  size_t play(const uint8_t *,size_t n,TickType_t){++writes;stopped=false;buffered=true;return n;}
  void set_audio_stream_info(audio::AudioStreamInfo v){info=v;}
  void add_audio_output_callback(std::function<void(uint32_t,int64_t)> v){dma=v;}
  void add_dma_discard_callback(std::function<void()> v){discard=v;}
}; }
namespace sendspin_ {
namespace sendspin_priority { static constexpr float CHILD=1; }
struct SendspinHub {
  std::string server_id{"BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB"}; bool connected{true}, paired{true}; sendspin::Role role;
  bool reference_connected() const{return connected;}
  bool reference_paired_owner(const std::string &id) const{return connected && paired && id==server_id;}
  std::string reference_server_id() const{return connected?server_id:"";}
  bool reference_time_synced() const{return connected;} float reference_sync_error() const{return 100;}
  int64_t reference_sync_at() const{return now_us;} sendspin::Role *get_player_role(){return &role;}
}; }
}
#include "adapter_header.inc"
#include "adapter_impl.inc"
using esphome::jarvis_reference::ReferenceSpeaker;
static const std::string REFERENCE="AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA";
struct Stock final:sendspin::PlayerRoleListener {
  ReferenceSpeaker *gate; std::vector<std::string> events;
  std::function<void()> end_hook=[]{}; std::function<void()> write_hook=[]{};
  std::function<void()> start_hook=[]{};
  explicit Stock(ReferenceSpeaker *v):gate(v){}
  void unlocked(){ bool acquired=false; std::thread t([&]{acquired=gate->mutex_.try_lock();if(acquired)gate->mutex_.unlock();});t.join();assert(acquired && "stock callback held reference mutex"); }
  size_t on_audio_write(uint8_t *p,size_t n,uint32_t t) override{unlocked();events.push_back("audio");write_hook();return gate->play(p,n,t);}
  void on_stream_start() override{unlocked();events.push_back("start");start_hook();}
  void on_stream_end() override{unlocked();events.push_back("end");end_hook();gate->stop();}
  void on_volume_changed(uint8_t v) override{unlocked();events.push_back("volume");gate->set_volume(v/100.f);}
  void on_mute_changed(bool v) override{unlocked();events.push_back("mute");gate->set_mute_state(v);}
};
struct Fixture {
  ReferenceSpeaker gate; esphome::i2s_audio::I2SAudioSpeaker output; esphome::audio_dac::AudioDac dac;
  esphome::switch_::Switch amp; esphome::sendspin_::SendspinHub hub; Stock stock{&gate};
  Fixture(){gate.set_output_speaker(&output);gate.set_dac_id(&dac);gate.set_amplifier_id(&amp);gate.set_sendspin_id(&hub);
    // Python omits the new setters only when reproducing the old baseline.
    INIT_STOCK
    gate.setup();}
};
int main(){
  uint8_t pcm[8]{1};
  { Fixture f; f.gate.on_stream_start();
    assert(f.stock.events==std::vector<std::string>{"start"} && "normal start must reach stock source");
    const auto normal_identity=f.hub.server_id;
    f.hub.server_id=REFERENCE;
    assert(!f.gate.arm(1,REFERENCE,1000) && "normal stream blocks an otherwise valid arm before physical start");
    f.hub.server_id=normal_identity;
    assert(f.gate.on_audio_write(pcm,8,10)==8);assert(f.output.writes==1);
    f.gate.on_volume_changed(23); f.gate.on_mute_changed(true);
    assert(f.output.volume==0.23f && f.output.muted);
    f.stock.end_hook=[&]{f.output.stop();f.hub.server_id=REFERENCE;assert(!f.gate.arm(1,REFERENCE,1000));};
    f.gate.on_stream_end();
    assert((f.stock.events==std::vector<std::string>{"start","audio","volume","mute","end"}));
    assert(!f.gate.stream_open_);
  }
  { Fixture f; f.hub.server_id=REFERENCE;
    f.gate.on_volume_changed(100);f.gate.on_mute_changed(false);f.gate.on_stream_start();
    assert(f.gate.on_audio_write(pcm,8,10)==0);f.gate.on_stream_end();
    assert(f.stock.events.empty() && f.output.writes==0 && "unarmed configured identity must stay silent");
    assert(!f.gate.arm(1,"BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB",1000));
    assert(f.gate.arm(1,REFERENCE,1000));f.gate.on_stream_start();assert(f.gate.on_audio_write(pcm,8,10)==8);
    assert(f.gate.cancel(1));f.gate.loop();assert(f.gate.lease_.idle());
    // A server change and released lease must not relabel late reference PCM.
    f.hub.server_id="BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB";
    assert(f.gate.on_audio_write(pcm,8,10)==0);f.gate.on_volume_changed(90);
    f.gate.on_stream_end();assert(f.stock.events.empty());
  }
  { Fixture f; f.hub.server_id=REFERENCE;assert(f.gate.arm(1,REFERENCE,1000));
    f.hub.server_id="BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB";
    f.gate.on_stream_start();assert(f.gate.lease_.fault()==ReferenceSpeaker::Fault::FOREIGN_MEDIA);
    f.gate.loop();assert(f.gate.lease_.idle());
    assert(f.gate.on_audio_write(pcm,8,10)==0);f.gate.on_volume_changed(100);f.gate.on_stream_end();
    assert(f.stock.events.empty() && f.output.writes==0);
    f.gate.on_stream_start();assert(f.gate.on_audio_write(pcm,8,10)==8);f.gate.on_stream_end();
  }
  { Fixture f;f.hub.server_id.clear();f.gate.on_stream_start();
    assert(f.gate.on_audio_write(pcm,8,10)==0);f.gate.on_volume_changed(100);f.gate.on_mute_changed(false);f.gate.on_stream_end();
    assert(f.stock.events.empty());
  }
  { Fixture f;f.hub.server_id=REFERENCE;f.hub.paired=false;assert(!f.gate.arm(1,REFERENCE,1000)); }
  { Fixture f;assert(!f.gate.arm(1,f.hub.server_id,1000) && "paired foreign identity cannot become reference owner"); }
  { Fixture f;f.hub.server_id=REFERENCE;assert(f.gate.arm(1,REFERENCE,1000));
    f.hub.role.params.codec=sendspin::SendspinCodecFormat::FLAC;
    f.gate.on_stream_start();assert(f.gate.lease_.fault()==ReferenceSpeaker::Fault::FORMAT);
    assert(f.gate.on_audio_write(pcm,8,10)==0);f.gate.on_stream_end();assert(f.stock.events.empty()); }
  { Fixture f;f.gate.on_stream_start();
    f.hub.server_id=REFERENCE;assert(f.gate.on_audio_write(pcm,8,10)==0);
    f.gate.on_stream_end();
    assert((f.stock.events==std::vector<std::string>{"start","end"}) && "dropped normal route must still close stock lifecycle");
  }
  { Fixture f; f.gate.on_stream_start();
    std::mutex barrier;std::condition_variable cv;bool writing=false, release=false;
    f.stock.write_hook=[&]{std::unique_lock<std::mutex> l(barrier);writing=true;cv.notify_all();cv.wait(l,[&]{return release;});};
    std::thread writer([&]{assert(f.gate.on_audio_write(pcm,8,10)==8);});
    { std::unique_lock<std::mutex> l(barrier);cv.wait(l,[&]{return writing;}); }
    std::atomic<bool> ended{false};
    std::thread ending([&]{f.gate.on_stream_end();ended=true;});
    // Wait until production has stopped admitting callbacks, without relying
    // on sleep or a scheduler timing guess.
    for(;;){std::lock_guard<std::mutex> l(f.gate.mutex_);if(f.gate.route_==ReferenceSpeaker::Route::DROP)break;}
    f.hub.server_id=REFERENCE;
    assert(!ended && !f.gate.arm(1,REFERENCE,1000));
    { std::lock_guard<std::mutex> l(barrier);release=true;cv.notify_all(); }
    writer.join();ending.join();assert(ended && f.output.stopped && !f.gate.stream_open_);
    assert((f.stock.events==std::vector<std::string>{"start","audio","end"}));
  }
  { Fixture f;f.gate.audio_stream_info_=esphome::audio::AudioStreamInfo(32,2,48000);
    assert(f.gate.play(pcm,8,10)==8);assert(f.output.info.bits==32);f.gate.stop(); }
  { Fixture f;f.stock.start_hook=[&]{f.gate.on_stream_end();};
    f.gate.on_stream_start();
    assert((f.stock.events==std::vector<std::string>{"start","end"}) && !f.gate.stream_open_);
  }
  assert(delays>=4);std::cout<<"stock adapter: lifecycle, identity isolation, reentrant callbacks and normal format passed\n";
}

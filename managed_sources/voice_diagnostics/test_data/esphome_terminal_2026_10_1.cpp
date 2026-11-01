// Narrow characterization fixture: exact event/stop-loop/set-state bodies from
// https://github.com/esphome/esphome/blob/2026.10.1/esphome/components/voice_assistant/voice_assistant.cpp
// Hardware, logging and callback effects are stubbed. Event and state logic is unchanged.
#include <iostream>
#include <string>
#define ESP_LOGD(...)
namespace api { namespace enums { enum Event {VOICE_ASSISTANT_RUN_END, VOICE_ASSISTANT_STT_VAD_END}; }}
enum class State {IDLE, START_PIPELINE, STARTING_PIPELINE, STREAMING_MICROPHONE, STOP_MICROPHONE, STOPPING_MICROPHONE, AWAITING_RESPONSE};
struct Microphone {bool running=true; bool is_running(){return running;} bool is_stopped(){return !running;} void stop(){running=false;}};
struct Trigger {void trigger(){}};
class VoiceAssistant {
 public:
  State state_=State::STREAMING_MICROPHONE, desired_state_=State::STREAMING_MICROPHONE;
  Microphone mic; Microphone *mic_source_=&mic, *mic_source2_=nullptr;
  Trigger end_trigger_, stt_vad_end_trigger_;
  template<class F> void defer(F f){f();}
  void set_state_(State state);
  void set_state_(State state, State desired_state);
  void event(api::enums::Event event) {switch(event) {
    case api::enums::VOICE_ASSISTANT_RUN_END: {
      ESP_LOGD(TAG, "Assist Pipeline ended");
      if ((this->state_ == State::START_PIPELINE) || (this->state_ == State::STARTING_PIPELINE) ||
          (this->state_ == State::STREAMING_MICROPHONE)) {
        // Microphone is running, stop it
        this->set_state_(State::STOP_MICROPHONE, State::IDLE);
      } else if (this->state_ == State::AWAITING_RESPONSE) {
        // No TTS start event ("nevermind")
        this->set_state_(State::IDLE, State::IDLE);
      }
      this->defer([this]() { this->end_trigger_.trigger(); });
      break;
    }
    case api::enums::VOICE_ASSISTANT_STT_VAD_END:
      ESP_LOGD(TAG, "STT by VAD end");
      this->set_state_(State::STOP_MICROPHONE, State::AWAITING_RESPONSE);
      this->defer([this]() { this->stt_vad_end_trigger_.trigger(); });
      break;
  }}
  void loop(){switch(state_) {
    case State::STOP_MICROPHONE: {
      // Check both microphone channels
      bool is_running = this->mic_source_->is_running();
      bool is_running2 = false;
      if (this->mic_source2_) {
        is_running2 = this->mic_source2_->is_running();
      }
      if (is_running || is_running2) {
        if (is_running) {
          this->mic_source_->stop();
        }
        if (is_running2) {
          this->mic_source2_->stop();
        }
        this->set_state_(State::STOPPING_MICROPHONE);
      } else {
        this->set_state_(this->desired_state_);
      }
      break;
    }
    case State::STOPPING_MICROPHONE: {
      // Check both microphone channels
      bool is_stopped = this->mic_source_->is_stopped();
      bool is_stopped2 = true;
      if (this->mic_source2_) {
        is_stopped2 = this->mic_source2_->is_stopped();
      }
      if (is_stopped && is_stopped2) {
        this->set_state_(this->desired_state_);
      }
      break;
    }
    default: break;
  }}
};
void VoiceAssistant::set_state_(State state) {
  State old_state = this->state_;
  this->state_ = state;
  ESP_LOGD(TAG, "State changed from %s to %s", LOG_STR_ARG(voice_assistant_state_to_string(old_state)),
           LOG_STR_ARG(voice_assistant_state_to_string(state)));
}

void VoiceAssistant::set_state_(State state, State desired_state) {
  this->set_state_(state);
  this->desired_state_ = desired_state;
  ESP_LOGD(TAG, "Desired state set to %s", LOG_STR_ARG(voice_assistant_state_to_string(desired_state)));
}


int main(int argc, char** argv){
 VoiceAssistant device;
 if(argc>1 && std::string(argv[1])=="START_PIPELINE")device.state_=State::START_PIPELINE;
 if(argc>1 && std::string(argv[1])=="STARTING_PIPELINE")device.state_=State::STARTING_PIPELINE;
 std::string event;
 while(std::cin>>event){
  if(event=="stt-vad-end")device.event(api::enums::VOICE_ASSISTANT_STT_VAD_END);
  if(event=="run-end")device.event(api::enums::VOICE_ASSISTANT_RUN_END);
 }
 for(int i=0;i<3;i++)device.loop();
 std::cout<<(device.state_==State::IDLE?"IDLE":device.state_==State::AWAITING_RESPONSE?"AWAITING_RESPONSE":"OTHER")<<"\n";
}

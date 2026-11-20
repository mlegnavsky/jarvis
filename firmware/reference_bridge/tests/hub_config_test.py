"""Execute the production hub configuration prefix, before hardware construction.

Diagnostics must not erase stock codec advertisement or DAC fixed delay. The
SDK client constructor and persistence/network setup are beyond this boundary.
"""
from pathlib import Path
import os
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
source_path = Path(os.environ.get("REFERENCE_HUB_SOURCE", ROOT / "components/sendspin/sendspin_hub.cpp"))
source = source_path.read_text()
start = source.index("void SendspinHub::setup() {")
end = source.index("  this->client_ =", start)
prefix = source[start:end] + "  effective = config;\n}\n"
harness = r'''
#include <cassert>
#include <vector>
#include <iostream>
namespace sendspin {
enum class SendspinCodecFormat { PCM, FLAC };
struct AudioFormat { SendspinCodecFormat codec; int channels, rate, bits; };
}
struct Config { int time_burst_interval_ms=1000, time_burst_response_timeout_ms=1000, liveness_timeout_ms=5000; };
struct SendspinHub {
 bool reference_diagnostics_=true;
 struct { std::vector<sendspin::AudioFormat> audio_formats{{sendspin::SendspinCodecFormat::FLAC,2,48000,16},
   {sendspin::SendspinCodecFormat::PCM,1,48000,16}}; int fixed_delay_us=480; } player_config_;
 Config effective;
 Config build_client_config_(){return {};}
 void setup();
};
'''
harness += prefix + r'''
int main(){SendspinHub hub;hub.setup();
 assert(hub.player_config_.audio_formats.size()==2 && "diagnostics must preserve stock codec advertisement");
 assert(hub.player_config_.audio_formats[0].codec==sendspin::SendspinCodecFormat::FLAC);
 assert(hub.player_config_.audio_formats[1].channels==1);
 assert(hub.player_config_.fixed_delay_us==480 && "diagnostics must preserve stock DAC delay");
 assert(hub.effective.time_burst_interval_ms==500);
 std::cout<<"hub diagnostics preserve stock codecs, mono support and 480us DAC delay\n";
}
'''
with tempfile.TemporaryDirectory(prefix="reference-hub-config-") as tmp:
    cpp = Path(tmp) / "test.cpp"
    cpp.write_text(harness)
    binary = Path(tmp) / "test"
    subprocess.run(["g++", "-std=c++17", "-Wall", "-Wextra", "-Werror", "-DUSE_SENDSPIN_PLAYER",
                    str(cpp), "-o", str(binary)], check=True)
    subprocess.run([str(binary)], check=True)

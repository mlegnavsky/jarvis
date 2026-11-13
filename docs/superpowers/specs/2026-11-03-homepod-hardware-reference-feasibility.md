# External HomePod reference into Voice PE AEC — feasibility, not a fix

Status3Nov2026: read-only upstream hardware/firmware investigation. No GPIO,
DAC, Voice PE firmware, microphone or new device output was changed.
The one consented room measurement has already run; its PCM was erased.

## Supported physical path

Voice PE routes ESP32 I2S output digitally to both XMOS reference and DAC,
before analog amplification. GPIO47 controls the internal speaker amplifier
independently. In the upstream configuration aic3204_dac handles volume/mute,
so DAC mute does not zero the digital I2S reference. Software PCM zeroing
would destroy it. Boot firmware enables the amplifier, requiring owned-state
handling rather than assuming persistent silent mode.

Primary sources: [ESP32 schematic](https://github.com/esphome/home-assistant-voice-pe/blob/dev/hardware/KiCad/ESP32S3.kicad_sch),
[XMOS schematic](https://github.com/esphome/home-assistant-voice-pe/blob/dev/hardware/KiCad/XMOS.kicad_sch),
[DAC schematic](https://github.com/esphome/home-assistant-voice-pe/blob/dev/hardware/KiCad/DAC.kicad_sch),
[upstream voice YAML](https://github.com/esphome/home-assistant-voice-pe/blob/dev/home-assistant-voice.yaml),
[ESPHome2026.10.1 speaker.h](https://github.com/esphome/esphome/blob/2026.10.1/esphome/components/speaker/speaker.h),
[I2S speaker](https://github.com/esphome/esphome/blob/2026.10.1/esphome/components/i2s_audio/speaker/i2s_audio_speaker.cpp).

## DSP and timing

XMOS v1.3.1 reads I2S as its AEC reference. Stock microphone delay is40ms;
main adaptive filter150ms and shadow75ms at16kHz. These are finite filter
windows, not a HomePod delay setting. Nominal reference arrivalR and acoustic
microphone arrivalM must satisfy0 <= M+40ms-R <150ms, with additional margin
for room response and processing. A shorter shadow window needs <75ms.

Core currently selects API channel1 when the STT provider prefers neither
AGC nor noise reduction. VoiceKit supports channel_1_stage:AEC to obtain an
AEC stage without adding the later processing stages. Upstream schema's
default is NS; the actual installed channel stage and XMOS version were
NOT read in this investigation. Core's label raw is not proof of hardware
unprocessed PCM. Verify the actual target before a firmware configuration.

Primary sources: [XMOS input/stage mapping](https://github.com/esphome/voice-kit-xmos-firmware/blob/v1.3.1/src/ffva/src/main.c),
[40ms configuration](https://github.com/esphome/voice-kit-xmos-firmware/blob/v1.3.1/src/ffva/src/app_conf.h),
[filter phases](https://github.com/esphome/voice-kit-xmos-firmware/blob/v1.3.1/modules/audio_pipelines/reference/fixed_delay/audio_pipeline_dsp.h),
[XMOS AEC frame definitions](https://github.com/xmos/fwk_voice/blob/8b80d3cf684934f038b6ae3167a70cacfb6dd2c1/modules/lib_aec/api/aec_defines.h),
[VoiceKit schema](https://github.com/esphome/home-assistant-voice-pe/blob/dev/esphome/components/voice_kit/__init__.py).

## Decision and missing evidence

Hardware reference path is feasible; a synchronized external HomePod feeder
is not present in the current stack. Two independent play_media calls do
not establish sample timing. HomePodOutput.started_at already includes its
1.5s sender scheduling delay. The measured additional band offset~382ms is
relative to that estimate, not receiver timestamps or acoustic propagation
alone. Adding another1.5s would be wrong. One captured session does not
establish a stable offset across sessions.

Do not deploy a configuration-only change as an acoustic repair. The bounded
next implementation is a timestamped generated-reference feeder with known
I2S playback timing, buffer/drift management, cancellation/flush tail, DAC
mute and owned amp state, plus AEC-stage output selection. It needs separate
synchronization and short mixed-human preservation proof. No new XMOS
firmware is inherently necessary for the already supported AEC path.

Unresolved alternatives are not permission for another remote microphone
start: the owner's single30s test is consumed. Original full-duplex/one-second
conversation goal remains OPEN. No hardware-reference implementation exists
yet; these are verified prerequisites and explicit implementation gaps.

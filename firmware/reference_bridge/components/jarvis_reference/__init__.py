"""Silent PCM reference endpoint; uses pinned ESPHome/Sendspin interfaces."""
import esphome.codegen as cg
import esphome.config_validation as cv
import re
from esphome.components import audio, audio_dac, sendspin, speaker, switch
from esphome.components.sendspin.media_source import SendspinMediaSource
from esphome.components.i2s_audio.speaker import I2SAudioSpeaker
from esphome.const import CONF_ID

DEPENDENCIES = ['esp32', 'sendspin', 'i2s_audio']
AUTO_LOAD = ['audio', 'speaker']
ns = cg.esphome_ns.namespace('jarvis_reference')
ReferenceSpeaker = ns.class_('ReferenceSpeaker', cg.Component, speaker.Speaker)

def _reference_server_id(value):
    value = cv.string_strict(value)
    if not re.fullmatch(r'[A-Za-z0-9_-]{43}', value):
        raise cv.Invalid('reference_server_id must be exactly 43 base64url characters')
    return value

def _limits(config):
    audio.set_stream_limits(min_bits_per_sample=16, max_bits_per_sample=32,
        min_channels=2, max_channels=2, min_sample_rate=48000, max_sample_rate=48000)(config)
    return config


def _player(config):
    if "existing_player" in config:
        return config
    sendspin.register_player_config({
        sendspin.CONF_CODECS: [sendspin.CODEC_PCM],
        'sample_rate': 48000, 'buffer_size': 768000,
        sendspin.CONF_INITIAL_STATIC_DELAY: cv.positive_time_period_milliseconds("0ms"),
        sendspin.CONF_FIXED_DELAY: cv.positive_time_period_microseconds("0us"),
        sendspin.CONF_TASK_STACK_IN_PSRAM: False,
        sendspin.CONF_DECODE_MEMORY: sendspin.MEMORY_PSRAM,
    })
    return config

CONFIG_SCHEMA = cv.All(cv.Schema({
    cv.GenerateID(): cv.declare_id(ReferenceSpeaker),
    cv.Required('output_speaker'): cv.use_id(I2SAudioSpeaker),
    cv.Required('dac_id'): cv.use_id(audio_dac.AudioDac),
    cv.Required('amplifier_id'): cv.use_id(switch.Switch),
    cv.Required('sendspin_id'): cv.use_id(sendspin.SendspinHub),
    cv.Required('reference_server_id'): _reference_server_id,
    cv.Optional('existing_player'): cv.use_id(SendspinMediaSource),
    cv.Optional('sample_rate', default=48000): cv.one_of(48000, int=True),
    cv.Optional('bits_per_sample', default=32): cv.one_of(16, 24, 32, int=True),
    cv.Optional('num_channels', default=2): cv.one_of(2, int=True),
}).extend(cv.COMPONENT_SCHEMA), cv.only_with_framework("esp-idf"), _player,
    _limits)

async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)
    await speaker.register_speaker(var, config)
    cg.add(var.set_reference_server_id(config['reference_server_id']))
    for key in ('output_speaker', 'dac_id', 'amplifier_id', 'sendspin_id'):
        value = await cg.get_variable(config[key])
        cg.add(getattr(var, 'set_' + key)(value))
    if 'existing_player' in config:
        # Codegen dependency: stock listener registration must complete first.
        stock = await cg.get_variable(config['existing_player'])
        cg.add(var.set_stock_listener(stock))
    hub = await cg.get_variable(config['sendspin_id'])
    cg.add(hub.set_listener(var))
    cg.add(hub.enable_reference_diagnostics())

"""Device-scoped direct light wakes; no raw audio or additional device privileges.

Bare light commands act in the microphone's assigned room. Named-room commands
continue to use Jarvis followed by the complete spoken instruction.
"""
COMMANDS = frozenset(('rozsviť', 'zhasni'))


def install(hass, input_class, stages, core_version, pipeline_id, satellite_id):
    report = {'status': 'unsupported_core', 'commands': 0,
              'scope': 'bare_light_commands_in_satellite_room'}
    if core_version != '2026.6.4':
        return report
    if '_jarvis_direct_wake' in input_class.__dict__:
        return input_class._jarvis_direct_wake
    original = input_class.execute

    async def execute(value, validate=False):
        run = value.run
        phrase = value.wake_word_phrase
        if not (run.hass is hass and run.pipeline.id == pipeline_id
                and value.satellite_id == satellite_id
                and run.start_stage == stages.STT and phrase in COMMANDS):
            return await original(value, validate=validate)
        # The detected word already IS the entire authorized command. No cloud
        # STT or wait for additional speech; native agent resolves exposed lights.
        stage, text, stream = run.start_stage, value.intent_input, value.stt_stream
        try:
            run.start_stage = stages.INTENT
            value.intent_input = phrase
            value.stt_stream = None
            report['commands'] += 1
            return await original(value, validate=validate)
        finally:
            run.start_stage, value.intent_input, value.stt_stream = stage, text, stream

    input_class.execute = execute
    report['status'] = 'active'
    input_class._jarvis_direct_wake = report
    return report

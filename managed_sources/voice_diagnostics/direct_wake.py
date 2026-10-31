"""Device-scoped direct light wakes; no raw audio or additional device privileges.

Bare light commands act in the microphone's assigned room. Named-room commands
continue to use Jarvis followed by the complete spoken instruction.
"""
import time
from types import SimpleNamespace

COMMANDS = frozenset(('rozsviť', 'zhasni'))


def install(hass, input_class, stages, core_version, pipeline_id, satellite_id, *, last_wakeups=None, cooldown=2., clock=time.monotonic, end_event=None):
    report = {'status': 'unsupported_core', 'commands': 0,
              'scope': 'bare_light_commands_in_satellite_room'}
    if core_version != '2026.6.4':
        return report
    if '_jarvis_direct_wake' in input_class.__dict__:
        return input_class._jarvis_direct_wake
    original = input_class.execute
    last_wakeups = {} if last_wakeups is None else last_wakeups
    end_event = end_event or (lambda: SimpleNamespace(type=SimpleNamespace(value="stt-vad-end")))

    async def execute(value, validate=False):
        run = value.run
        phrase = value.wake_word_phrase
        if not (run.hass is hass and run.pipeline.id == pipeline_id
                and value.satellite_id == satellite_id
                and run.start_stage == stages.STT and run.end_stage != stages.STT
                and phrase in COMMANDS):
            return await original(value, validate=validate)
        now = clock()
        if phrase in last_wakeups and now-last_wakeups[phrase] < cooldown:
            # Native STT branch emits the standard duplicate-wake error before
            # starting microphone/STT. Preserve that error and event lifecycle.
            return await original(value, validate=validate)
        last_wakeups[phrase] = now
        previous_event = run.process_event
        had_event_override = 'process_event' in run.__dict__
        def process_event(event):
            previous_event(event)
            if getattr(event.type, 'value', event.type) == 'run-start':
                # ESPHome starts uploading before the pipeline executes and only
                # stops its microphone on this native event, not INTENT_START.
                previous_event(end_event())
        # The detected word already IS the entire authorized command. No cloud
        # STT or wait for additional speech; native agent resolves exposed lights.
        stage, text, stream = run.start_stage, value.intent_input, value.stt_stream
        try:
            run.process_event = process_event
            run.start_stage = stages.INTENT
            value.intent_input = phrase
            value.stt_stream = None
            report['commands'] += 1
            return await original(value, validate=validate)
        finally:
            run.start_stage, value.intent_input, value.stt_stream = stage, text, stream
            if had_event_override:
                run.process_event = previous_event
            else:
                del run.process_event

    input_class.execute = execute
    report['status'] = 'active'
    input_class._jarvis_direct_wake = report
    return report

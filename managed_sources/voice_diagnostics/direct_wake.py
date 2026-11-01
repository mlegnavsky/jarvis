"""Keep unselected direct light models out of the ordinary wake-word flow.

The acoustic command models can fire on television audio even when the ordinary
wake-word slots are disabled. A detected command is not speaker authorization.
"""
import time
from types import SimpleNamespace

COMMANDS = frozenset(('rozsviť', 'zhasni'))


def install(hass, input_class, stages, core_version, pipeline_id, satellite_id, *, last_wakeups=None, cooldown=2., clock=time.monotonic, end_event=None):
    report = {'status': 'unsupported_core', 'commands': 0, 'blocked': 0,
              'scope': 'selected_wake_then_spoken_command_only'}
    if core_version != '2026.6.4':
        return report
    if '_jarvis_direct_wake' in input_class.__dict__:
        return input_class._jarvis_direct_wake
    original = input_class.execute
    end_event = end_event or (lambda: SimpleNamespace(type=SimpleNamespace(value="stt-vad-end")))

    async def execute(value, validate=False):
        run = value.run
        phrase = value.wake_word_phrase
        if not (run.hass is hass and run.pipeline.id == pipeline_id
                and value.satellite_id == satellite_id
                and run.start_stage == stages.STT and phrase in COMMANDS):
            return await original(value, validate=validate)
        from homeassistant.components.assist_pipeline.pipeline import PipelineEvent, PipelineEventType
        # Match Core's error lifecycle: stop device audio, discard prepared TTS,
        # emit a bounded error and always close the run. Never invoke STT/intent.
        report['blocked'] += 1
        run.start(conversation_id=value.session.conversation_id,
                  device_id=value.device_id, satellite_id=value.satellite_id)
        try:
            run.process_event(end_event())
            if run.tts_stream:
                run.tts_stream.delete()
                run.tts_stream = None
            run.process_event(PipelineEvent(PipelineEventType.ERROR, {
                'code': 'direct-command-wake-disabled',
                'message': 'Direct acoustic light commands are disabled; say Jarvis then the command.',
            }))
        finally:
            await run.end()

    input_class.execute = execute
    report['status'] = 'explicit_wake_required'
    input_class._jarvis_direct_wake = report
    return report

"""Route installed acoustic light commands through the public local intent gate.

Only exact light detections from this satellite/pipeline skip transcription.
They grant no identity, personal memory, lock or profile-management permission.
"""
import asyncio
import time
from types import SimpleNamespace

COMMANDS = frozenset(('rozsviť', 'zhasni'))


def install(hass, input_class, stages, core_version, pipeline_id, satellite_id, *, last_wakeups=None, cooldown=2., clock=time.monotonic, end_event=None):
    report = {'status': 'unsupported_core', 'version': 2, 'commands': 0, 'blocked': 0,
              'scope': 'public_local_lights_native_intent_only',
              'identity_inference': False, 'speech_to_text': False,
              'commands_count_handoffs_not_physical_confirmation': True}
    if core_version != '2026.6.4':
        return report
    if '_jarvis_direct_wake' in input_class.__dict__:
        return input_class._jarvis_direct_wake
    original = input_class.execute
    last_wakeups = {} if last_wakeups is None else last_wakeups
    end_event = end_event or (lambda: SimpleNamespace(type=SimpleNamespace(value="stt-vad-end")))

    async def blocked(value, code):
        run = value.run
        from homeassistant.components.assist_pipeline.pipeline import PipelineEvent, PipelineEventType
        report['blocked'] += 1
        report['last_blocked_reason'] = code
        run.start(conversation_id=value.session.conversation_id,
                  device_id=value.device_id, satellite_id=value.satellite_id)
        try:
            run.process_event(end_event())
            if run.tts_stream:
                run.tts_stream.delete()
                run.tts_stream = None
            run.process_event(PipelineEvent(PipelineEventType.ERROR, {
                'code': code,
                'message': 'Direct local light command is currently unavailable.',
            }))
        finally:
            await run.end()

    async def execute(value, validate=False):
        run = value.run
        phrase = value.wake_word_phrase
        if not (run.hass is hass and run.pipeline.id == pipeline_id
                and value.satellite_id == satellite_id
                and run.start_stage == stages.STT and phrase in COMMANDS):
            return await original(value, validate=validate)
        speaker = hass.data.get('jarvis_speaker_identity')
        if not (speaker and speaker.enforce and speaker.public_controls
                and getattr(type(run), '_jarvis_voice_intent_guard', False)
                and getattr(type(run), '_jarvis_speaker_adapter', None) is speaker):
            return await blocked(value, 'direct-command-policy-unavailable')
        def discard_pending():
            pending = speaker.results.get(satellite_id)
            if pending and pending.get('context_id') == run.context.id:
                speaker.results.pop(satellite_id, None)
        now = clock()
        previous = last_wakeups.get(phrase)
        if previous is not None and 0 <= now-previous < cooldown:
            return await blocked(value, 'duplicate-wake-up-detected')
        # Reserve before the first await so overlapping detections cannot repeat.
        last_wakeups[phrase] = now
        try:
            if await hass.async_add_executor_job(speaker.training_active):
                return await blocked(value, 'direct-command-training-active')
            await speaker.complete(satellite_id, b'', 0, phrase, context_id=run.context.id)
        except asyncio.CancelledError:
            discard_pending()
            await blocked(value, 'direct-command-cancelled')
            raise
        except Exception:
            discard_pending()
            return await blocked(value, 'direct-command-handoff-failed')
        native_start = run.start
        old_stage, old_input, old_stream = run.start_stage, value.intent_input, value.stt_stream
        native_started = False
        def start(**kwargs):
            nonlocal native_started
            native_start(**kwargs)
            native_started = True
            # Stop the Voice PE microphone immediately, including when no TTS follows.
            run.process_event(end_event())
        run.start = start
        run.start_stage, value.intent_input, value.stt_stream = stages.INTENT, phrase, None
        try:
            report['commands'] += 1
            report['last_phrase'] = phrase
            return await original(value, validate=validate)
        except (Exception, asyncio.CancelledError):
            # Core validates before entering its own run/end try/finally.
            if not native_started:
                run.start = native_start
                await blocked(value, 'direct-command-before-start-failed')
            raise
        finally:
            discard_pending()
            report['last_handoff_ms'] = round((clock()-now)*1000, 1)
            run.start = native_start
            run.start_stage, value.intent_input, value.stt_stream = old_stage, old_input, old_stream

    input_class.execute = execute
    report['status'] = 'public_light_fast_path'
    input_class._jarvis_direct_wake = report
    return report

"""Acoustic verbs activate complete utterance capture, never immediate actions."""
import asyncio
import time
from types import SimpleNamespace

COMMANDS = frozenset(('rozsviť', 'zhasni'))
MEDIA=('media_player.obyvak_televize_obyvak','media_player.obyvaci_pokoj_obyvaci_pokoj',
       'media_player.55_qled_2','media_player.homepod_obyvak_homepod_obyvak')

def media_active(hass):
    states=getattr(hass,'states',None)
    if states is None:return True
    return any((state:=states.get(entity)) is not None and state.state in
               ('on','playing','buffering','unknown','unavailable') for entity in MEDIA)


def install(hass, input_class, stages, core_version, pipeline_id, satellite_id, *, last_wakeups=None, cooldown=2., clock=time.monotonic, end_event=None):
    report = {'status': 'unsupported_core', 'version': 3, 'commands': 0, 'blocked': 0,
              'scope': 'whole_light_utterance_after_acoustic_hint',
              'continuation_wait_s':.75,'television_policy':'explicit_Jarvis_required_while_media_active',
              'identity_inference': False, 'speech_to_text': True,
              'commands_count_handoffs_not_physical_confirmation': True}
    if core_version != '2026.6.4':
        return report
    if '_jarvis_direct_wake' in input_class.__dict__:
        return input_class._jarvis_direct_wake
    original = input_class.execute
    # Native STT owns its shared cooldown; do not reserve that same dictionary
    # here or Core would reject this very run as a duplicate.
    last_hints = {}
    end_event = end_event or (lambda: SimpleNamespace(type=SimpleNamespace(value="stt-vad-end")))

    async def blocked(value, code):
        run = value.run
        report['blocked'] += 1
        report['last_blocked_reason'] = code
        run._jarvis_suppressed_activation=True
        try:
            run.start(conversation_id=value.session.conversation_id,
                      device_id=value.device_id, satellite_id=value.satellite_id)
            run.process_event(end_event())
            if run.tts_stream:
                run.tts_stream.delete()
                run.tts_stream = None
        finally:
            await run.end()
            del run._jarvis_suppressed_activation

    async def execute(value, validate=False):
        run = value.run
        phrase = value.wake_word_phrase
        if not (run.hass is hass and run.pipeline.id == pipeline_id
                and value.satellite_id == satellite_id
                and run.start_stage == stages.STT and phrase in COMMANDS):
            return await original(value, validate=validate)
        if media_active(hass):
            return await blocked(value, 'media-active-explicit-wake-required')
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
        previous = last_hints.get(phrase)
        if previous is not None and 0 <= now-previous < cooldown:
            return await blocked(value, 'duplicate-wake-up-detected')
        # Reserve before the first await so overlapping detections cannot repeat.
        last_hints[phrase] = now
        try:
            if await hass.async_add_executor_job(speaker.training_active):
                return await blocked(value, 'direct-command-training-active')
        except asyncio.CancelledError:
            discard_pending()
            await blocked(value, 'direct-command-cancelled')
            raise
        except Exception:
            discard_pending()
            return await blocked(value, 'direct-command-handoff-failed')
        native_start = run.start
        native_event = run.process_event
        native_started = False
        def start(**kwargs):
            nonlocal native_started
            native_start(**kwargs)
            native_started = True
        def process_event(event):
            if str(getattr(event.type,'value',event.type))=='stt-vad-start':
                run._jarvis_direct_continuation_started=True
            return native_event(event)
        run.start = start
        run.process_event=process_event
        run._jarvis_direct_command_prefix=phrase
        run._jarvis_command_wait_s=.75
        run._jarvis_direct_continuation_started=False
        run._jarvis_initial_silence_expired=False
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
            if hasattr(run,'_jarvis_direct_effective_text'):
                report['last_effective_command']=run._jarvis_direct_effective_text
            run.start = native_start
            run.process_event=native_event
            for name in ('_jarvis_direct_command_prefix','_jarvis_command_wait_s','_jarvis_direct_continuation_started','_jarvis_direct_effective_text','_jarvis_initial_silence_expired'):
                if hasattr(run,name):delattr(run,name)

    input_class.execute = execute
    report['status'] = 'whole_utterance_lights'
    input_class._jarvis_direct_wake = report
    return report

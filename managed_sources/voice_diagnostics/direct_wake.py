"""Acoustic verbs activate complete utterance capture, never immediate actions."""
import asyncio
import time

COMMANDS = frozenset(('rozsviť', 'zhasni'))
COMMAND_SWITCHES = {'rozsviť': 'input_boolean.jarvis_povel_rozsvit',
                    'zhasni': 'input_boolean.jarvis_povel_zhasni'}
MEDIA=('media_player.obyvak_televize_obyvak','media_player.obyvaci_pokoj_obyvaci_pokoj',
       'media_player.55_qled_2','media_player.homepod_obyvak_homepod_obyvak')

def media_active(hass):
    states=getattr(hass,'states',None)
    if states is None:return True
    if states.get('media_player.obyvaci_pokoj_obyvaci_pokoj') is None:return True
    return any((state:=states.get(entity)) is not None and state.state in
               ('on','playing','buffering','unknown','unavailable') for entity in MEDIA)


def install(hass, input_class, stages, core_version, pipeline_id, satellite_id, *, last_wakeups=None, cooldown=2., clock=time.monotonic):
    report = {'status': 'unsupported_core', 'version': 7, 'commands': 0, 'blocked': 0,
              'command_switches': dict(COMMAND_SWITCHES),
              'switch_scope': 'new_direct_runs_only_not_firmware_detection',
              'scope': 'whole_light_utterance_after_acoustic_hint',
              'continuation_wait_s':.75,'television_policy':'explicit_Jarvis_required_while_media_active',
              'identity_inference': False, 'speech_to_text': True,
              'commands_count_handoffs_not_physical_confirmation': True, 'recent_activations': []}
    if core_version != '2026.6.4':
        return report
    if '_jarvis_direct_wake' in input_class.__dict__:
        return input_class._jarvis_direct_wake
    original = input_class.execute
    # Native STT owns its shared cooldown; do not reserve that same dictionary
    # here or Core would reject this very run as a duplicate.
    last_hints = {}

    def record(value, outcome, **facts):
        entry={'at_epoch':time.time(),'run_id':str(getattr(value.run,'id','unknown')),
            'wake_word':value.wake_word_phrase,'outcome':outcome,**facts}
        report['recent_activations']=(report['recent_activations']+[entry])[-16:]
        return entry

    async def blocked(value, code):
        run = value.run
        report['blocked'] += 1
        report['last_blocked_reason'] = code
        record(value,'blocked',reason=code)
        run._jarvis_suppressed_activation=True
        try:
            # No TTS is going to follow: do not advertise a deleted stream URL.
            if run.tts_stream:
                run.tts_stream.delete()
                run.tts_stream = None
            run.start(conversation_id=value.session.conversation_id,
                      device_id=value.device_id, satellite_id=value.satellite_id)
            # Native RUN_END stops the microphone and targets IDLE. Sending
            # STT_VAD_END just before it races ESPHome's stop loop: RUN_END
            # does not clear the pending AWAITING_RESPONSE target while the
            # device is in STOP_MICROPHONE, so it remains busy indefinitely.
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
        states = getattr(hass, 'states', None)
        enabled = states.get(COMMAND_SWITCHES[phrase]) if states else None
        if enabled is None or enabled.state != 'on':
            return await blocked(value, 'direct-command-disabled')
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
        activation=record(value,'handoff',continuation_wait_s=.75)
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
            activation.update(duration_ms=report['last_handoff_ms'],
                continuation_started=run._jarvis_direct_continuation_started,
                initial_silence_expired=run._jarvis_initial_silence_expired)
            if hasattr(run,'_jarvis_direct_effective_text'):
                report['last_effective_command']=run._jarvis_direct_effective_text
                activation['transcript']=str(run._jarvis_direct_effective_text)[:240]
            run.start = native_start
            run.process_event=native_event
            for name in ('_jarvis_direct_command_prefix','_jarvis_command_wait_s','_jarvis_direct_continuation_started','_jarvis_direct_effective_text','_jarvis_initial_silence_expired'):
                if hasattr(run,name):delattr(run,name)

    input_class.execute = execute
    report['status'] = 'whole_utterance_lights'
    input_class._jarvis_direct_wake = report
    return report

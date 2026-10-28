"""Version-guarded, per-satellite initial-silence adapter for native Assist.

No wake-word model, background recognition, or full-duplex audio is invented here.
Native VAD decides speech; its utterance limit is distinct from the follow-up wait.
"""
import asyncio
from collections import deque
from contextlib import aclosing
from dataclasses import replace
from datetime import datetime, timezone
import inspect
import re
import time
from types import SimpleNamespace
from uuid import uuid4


def spoken_name(text):
    """Phonetic Czech name only at the final TTS boundary, not agent history."""
    return re.sub(r'\bjarvis(e|i|ovi|em|ův|ova|ovo|ovu|ovy|ové|ových|ovým|ovými)?\b',
                  lambda match: 'Džárvis' + (match.group(1) or ''), text, flags=re.IGNORECASE)


class InitialSilenceExpired(asyncio.CancelledError):
    """Internal cancellation of a silent provider stream, never user cancellation."""


class Controller:
    def __init__(self, hass, pipeline_id, satellite_id, wait_seconds, clock):
        self.hass = hass
        self.pipeline_id = pipeline_id
        self.satellite_id = satellite_id
        self.wait_seconds = wait_seconds
        self.clock = clock
        self.pending = None
        self.events = deque(maxlen=100)
        self.boot_id = uuid4().hex
        self.status = 'starting'

    def matches(self, run):
        return (run.hass is self.hass and run.pipeline.id == self.pipeline_id
                and run._satellite_id == self.satellite_id)

    def record(self, run, event, **values):
        self.events.append({'run_id': str(run.id), 'event': event,
                            'boot_id': self.boot_id,
                            'at': datetime.now(timezone.utc).isoformat(),
                            'monotonic_s': round(self.clock(), 3), **values})

    def restore_history(self, events):
        """Restore observations only; never restore pending windows/deadlines."""
        if not isinstance(events, list):
            return
        fields = {'run_id', 'event', 'boot_id', 'at', 'monotonic_s', 'wait_s',
                  'previous_run_id', 'continue_conversation', 'next_wait_s',
                  'reason', 'code'}
        for event in events[-100:]:
            if not isinstance(event, dict) or not isinstance(event.get('event'), str):
                continue
            clean = {key: value[:200] if isinstance(value, str) else value
                     for key, value in event.items() if key in fields
                     and (value is None or isinstance(value, (str, bool, int, float)))}
            clean.setdefault('boot_id', 'previous_boot_unknown')
            self.events.append(clean)

    def observe(self, run, event):
        kind, data = str(event.type), event.data or {}
        if kind == 'run-start':
            pending, self.pending = self.pending, None
            run._jarvis_wait_s = None
            # The preceding answer may take arbitrarily long to finish. The
            # native conversation ID, not time since intent generation, scopes
            # this one-shot handoff; consume it only in the next matching run.
            if pending and data.get('conversation_id') == pending['conversation_id']:
                run._jarvis_wait_s = pending['seconds']
                self.record(run, 'followup_open', wait_s=pending['seconds'],
                            previous_run_id=pending['run_id'])
            else:
                self.record(run, 'explicit_activation')
        elif kind == 'intent-end':
            output = data.get('intent_output') or {}
            continuing = output.get('continue_conversation') is True
            speech = (output.get('response') or {}).get('speech') or {}
            text = (speech.get('plain') or {}).get('speech') or ''
            if continuing:
                self.pending = {'conversation_id': output.get('conversation_id'),
                                'at': self.clock(), 'seconds': self.wait_seconds(text),
                                'run_id': str(run.id)}
            else:
                self.pending = None
            self.record(run, kind, continue_conversation=continuing,
                        next_wait_s=self.pending['seconds'] if self.pending else None)
        elif kind in ('stt-start', 'stt-vad-start', 'stt-vad-end', 'stt-end',
                       'tts-start', 'tts-end', 'run-end', 'error'):
            values = {'code': str(data.get('code', 'unknown'))[:80]} if kind == 'error' else {}
            self.record(run, kind, **values)

    def snapshot(self):
        return {'status': self.status, 'version': 2, 'boot_id': self.boot_id, 'pipeline_id': self.pipeline_id,
                'satellite_id': self.satellite_id, 'statement_wait_s': 3,
                'question_wait_s': 6, 'utterance_pause_s': 1.5,
                'utterance_ceiling_s': 120,
                'arbitrary_speech_barge_in': 'not_implemented_device_support_required',
                'custom_wake_words': 'not_installed_trained_model_required',
                'name_pronunciation': {'written': 'Jarvis', 'spoken': 'Džárvis',
                                       'scope': 'non-streamed target TTS input'},
                'addressee_detection': 'explicit_activation_then_bounded_followup',
                'events': list(self.events)}


def install(hass, pipeline_class, error_class, core_version, pipeline_id,
            satellite_id, wait_seconds, clock=time.monotonic):
    """Install once at setup. Hooks delegate unchanged for every unrelated run."""
    controller = Controller(hass, pipeline_id, satellite_id, wait_seconds, clock)
    if core_version != '2026.6.4':
        controller.status = 'unsupported_core'
        return controller
    required = {'audio_stream', 'stt_vad', 'sample_rate', 'sample_width'}
    if not required <= set(inspect.signature(pipeline_class._speech_to_text_stream).parameters):
        controller.status = 'unsupported_stream_api'
        return controller
    if '_jarvis_turn_adapter' in pipeline_class.__dict__:
        controller.status = 'adapter_already_installed'
        return controller
    original_event = pipeline_class.process_event
    original_speech = pipeline_class.speech_to_text
    original_stream = pipeline_class._speech_to_text_stream
    original_tts = pipeline_class.text_to_speech

    def process_event(run, event):
        if controller.matches(run):
            controller.observe(run, event)
        return original_event(run, event)

    async def speech_to_text(run, metadata, stream):
        try:
            return await original_speech(run, metadata, stream)
        except InitialSilenceExpired as exc:
            # Native speech_to_text propagates CancelledError unchanged. Catch only
            # our sentinel; external cancellations must still cancel the HA task.
            raise error_class(code='stt-no-text-recognized',
                              message='Jarvis follow-up ended without speech') from exc

    async def text_to_speech(run, tts_input, override_media_path=None):
        if controller.matches(run) and override_media_path is None:
            if not getattr(run, '_streamed_response_text', False):
                adjusted = spoken_name(tts_input)
                if adjusted != tts_input:
                    controller.record(run, 'name_pronunciation_applied')
                tts_input = adjusted
            else:
                controller.record(run, 'name_pronunciation_not_applied', reason='streamed_text')
        return await original_tts(run, tts_input, override_media_path)

    async def speech_stream(run, audio_stream, stt_vad, sample_rate=16000, sample_width=2):
        if not controller.matches(run) or stt_vad is None:
            if controller.matches(run) and stt_vad is None:
                controller.record(run, 'adapter_not_applied', reason='external_vad_unavailable')
            async with aclosing(original_stream(run, audio_stream, stt_vad, sample_rate, sample_width)) as native:
                async for chunk in native:
                    yield chunk
            return
        # Fresh dataclass state is essential: changing .silence_seconds alone
        # leaves the already initialized countdown at the old 0.7 seconds.
        stt_vad = replace(stt_vad, silence_seconds=1.5, timeout_seconds=120)
        wait_s = getattr(run, '_jarvis_wait_s', None)

        async def gated_audio():
            elapsed = 0.0
            started = clock()
            speech_started = False
            candidate_at = None
            iterator = aiter(audio_stream)
            try:
                while True:
                    speech_started = speech_started or stt_vad.in_command
                    budget = None
                    if wait_s is not None and not speech_started:
                        # Speech starting just before expiry gets native VAD's
                        # 0.3-second validation time; noise cannot extend forever.
                        grace = .35 if candidate_at is not None else 0
                        budget = wait_s + grace - max(elapsed, clock() - started)
                        if budget <= 1e-6:
                            controller.pending = None
                            controller.record(run, 'followup_silence', wait_s=wait_s)
                            raise InitialSilenceExpired()
                    try:
                        chunk = await asyncio.wait_for(anext(iterator), budget) if budget is not None else await anext(iterator)
                    except StopAsyncIteration:
                        if wait_s is not None and not speech_started:
                            controller.pending = None
                            controller.record(run, 'followup_silence', wait_s=wait_s, reason='stream_ended_without_speech')
                            raise InitialSilenceExpired() from None
                        return
                    except TimeoutError as exc:
                        controller.pending = None
                        controller.record(run, 'followup_silence', wait_s=wait_s)
                        raise InitialSilenceExpired() from exc
                    seconds = (len(chunk.audio) // sample_width) / sample_rate
                    # Do not let a candidate first appearing AFTER expiry reopen
                    # a closed window. Native VAD still validates real speech.
                    is_speech = (chunk.speech_probability or 0) > stt_vad.before_command_speech_threshold
                    if not is_speech and not speech_started:
                        candidate_at = None
                    elif (is_speech and candidate_at is None
                          and wait_s is not None and elapsed < wait_s):
                        candidate_at = elapsed
                    elapsed += seconds
                    yield chunk
            finally:
                if hasattr(iterator, 'aclose'):
                    await iterator.aclose()

        async with aclosing(gated_audio()) as gated:
            async with aclosing(original_stream(run, gated, stt_vad, sample_rate, sample_width)) as native:
                async for chunk in native:
                    yield chunk

    pipeline_class.process_event = process_event
    pipeline_class.speech_to_text = speech_to_text
    pipeline_class._speech_to_text_stream = speech_stream
    pipeline_class.text_to_speech = text_to_speech
    pipeline_class._jarvis_turn_adapter = controller
    controller.status = 'active'
    return controller


async def native_probe(hass, pipeline_class, segmenter_class):
    """Exercise actual patched Core stream and native VAD with synthetic PCM.

    No providers, microphone, speakers, model, or household service is invoked.
    """
    control = pipeline_class.__dict__.get('_jarvis_turn_adapter')
    if control is None or control.status != 'active':
        return {'status': 'not_run', 'reason': 'adapter_not_active'}
    results = []
    for wait, speech_at in ((3, None), (6, None), (3, 2.8), (6, 5.8)):
        run = object.__new__(pipeline_class)
        run.hass = hass
        run.pipeline = SimpleNamespace(id=control.pipeline_id)
        run._satellite_id = control.satellite_id
        run._jarvis_wait_s = wait
        run.id = f'synthetic-probe-{wait}-{speech_at}'
        run._capture_chunk = lambda _: None
        run.process_event = lambda _: None
        count = 0
        async def audio():
            nonlocal count
            for n in range(140):
                count += 1
                speaking = speech_at is not None and n / 10 >= speech_at
                yield SimpleNamespace(audio=bytes(3200), speech_probability=.99 if speaking else 0., timestamp_ms=n*100)
        expired = False
        async with aclosing(pipeline_class._speech_to_text_stream(run, audio(), segmenter_class())) as stream:
            try:
                async for _ in stream:
                    pass
            except InitialSilenceExpired:
                expired = True
        passed = expired and abs(count / 10 - wait) <= .11 if speech_at is None else not expired and count == 140
        results.append({'wait_s': wait, 'speech_at_s': speech_at,
                        'input_audio_s': count/10, 'silence_expired': expired, 'passed': passed})
    # Exercise the actual Core text-to-speech method with a local result-stream
    # double. No voice provider or physical playback is called.
    messages = []
    run.pipeline.tts_language = 'cs-CZ'
    run.pipeline.tts_voice = 'onyx'
    run._streamed_response_text = False
    run.tts_stream = SimpleNamespace(engine='synthetic', async_set_message=messages.append,
                                     media_source_id='', token='', url='', content_type='audio/wav')
    await pipeline_class.text_to_speech(run, 'Jmenuji se Jarvis. O Jarvisovi.')
    pronunciation = {'input': 'Jmenuji se Jarvis. O Jarvisovi.',
                     'tts_message': messages[-1] if messages else None,
                     'passed': messages == ['Jmenuji se Džárvis. O Džárvisovi.']}
    return {'status': 'passed' if all(r['passed'] for r in results) and pronunciation['passed'] else 'failed',
            'scope': 'synthetic PCM + actual Core VAD/stream; no acoustic or provider test',
            'cases': results, 'name_tts_boundary': pronunciation}

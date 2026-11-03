"""Real-time synthetic dialogue through explicitly pinned control/audio code.

No real microphone, household action, remote provider or HomePod connection.
Speech recognition, identity, agent and receiver are explicit test adapters.
"""
import argparse
import asyncio
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace as NS

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'managed_sources/local_duplex'))

STORY = (
    'A small boat left the quiet harbour before sunrise. Anna carried a map, '
    'a lantern, and a basket of bread. Her friend Daniel watched the water. '
    'They were looking for an island that appeared only on an old family map. '
    'The morning wind moved the clouds and the distant shore slowly disappeared. '
    'At noon they saw a white tower above the trees. A narrow path led from '
    'the beach to a wooden door. Behind the door they found a garden filled '
    'with flowers and a friendly keeper who had been waiting for visitors. '
    'He offered them tea and explained how people had cared for the island '
    'for many years. Every spring they repaired the paths and planted new trees. '
    'Anna opened her map and marked the safe route through the rocks. Daniel '
    'helped the keeper mend a little bridge. When evening came, the lanterns '
    'around the garden began to shine. They sat together and listened to the '
    'sea. The next morning they sailed home with a new map and a promise to '
    'return. Which part of their journey would you like to hear about next?'
)
FALSE_REPLY = (
    'The keeper looked after the garden and the little bridge. '
    'The visitors helped him before returning to their boat. '
    'Would you like another detail about the journey?'
)
DETAIL = (
    'Anna was carrying the old map and a lantern. Daniel watched the water '
    'and helped repair the bridge. They found a garden rather than treasure, '
    'and the keeper shared his tea and his memories with them.'
)
EVENTS = [
    (1., 2., 'human', 'Tell me a long story.', None),
    (12., 3., 'echo_exact', 'A small boat left the quiet harbour before sunrise.', .2),
    (24., 3., 'echo_exact', 'They were looking for an island', 1.25),
    # Fault injection models the observed short ASR mismatch; it does NOT
    # assert that a real recognizer will produce these words from this audio.
    (35., 3., 'echo_asr_fault', 'really happened', 1.25),
    (55., 2., 'human', 'Continue the long story.', None),
    (80., 1.2, 'human', 'Stop speaking.', None),
    (90., 2., 'human', 'Tell the story again.', None),
    (105., 3., 'echo_exact', 'The morning wind moved the clouds', .2),
    (122., 3., 'echo_asr_fault', 'my favorite', 1.25),
    (145., 2., 'human', 'Continue with the island story.', None),
    (165., 3., 'echo_exact', 'A narrow path led from the beach', 1.25),
    (180., 2., 'human', 'What was Anna carrying?', None),
    (209., 2., 'human', 'Finish the long story.', None),
]


def source_fingerprint():
    folder = ROOT / 'managed_sources/local_duplex'
    hashes = [hashlib.sha256(p.read_bytes()).hexdigest()
              for p in sorted(folder.glob('*.py')) if not p.name.startswith('test_')]
    return hashlib.sha256(''.join(hashes).encode()).hexdigest()


def run_ffmpeg(args, data=None):
    result = subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', *args],
                            input=data, capture_output=True, check=True)
    return result.stdout


def speech(text, seconds, voice, directory):
    path = Path(directory) / 'synthetic-text.txt'
    path.write_text(text)
    pcm = run_ffmpeg(['-f', 'lavfi', '-i', f'flite=textfile={path}:voice={voice}',
                      '-ac', '1', '-ar', '16000', '-f', 's16le', 'pipe:1'])
    ratio = len(pcm) / 32000 / seconds
    return run_ffmpeg(['-f', 's16le', '-ar', '16000', '-ac', '1', '-i', 'pipe:0',
                       '-af', f'atempo={ratio:.8f},apad', '-t', str(seconds),
                       '-f', 's16le', 'pipe:1'], pcm)


async def simulate(duration, destination, expected_source):
    from bridge import TurnBridge
    from homepod_io import HomePodOutput, HOME
    from playback_observer import PlaybackObserver
    from session import Session
    from speech_stream import open_speech_stream, AudioPipe
    from pyatv.protocols.raop.audio_source import open_source
    import audioop

    fingerprint = source_fingerprint()
    if fingerprint != expected_source:
        raise ValueError('simulation source differs from explicitly pinned source')
    version = json.loads((ROOT/'managed_sources/local_duplex/manifest.json').read_text())['version']
    print(json.dumps({'event': 'preparing_generated_speech', 'duration_s': duration}), flush=True)
    with tempfile.TemporaryDirectory(prefix='jarvis-synthetic-only-') as folder:
        answers = {}
        for key, text, seconds in [('story', STORY, 60), ('false', FALSE_REPLY, 12),
                                   ('stop', 'I have stopped. I am listening.', 3),
                                   ('detail', DETAIL, 18)]:
            pcm = speech(text, seconds, 'slt', folder)
            answers[text] = run_ffmpeg(['-f', 's16le', '-ar', '16000', '-ac', '1',
                                      '-i', 'pipe:0', '-c:a', 'libmp3lame',
                                      '-b:a', '64k', '-f', 'mp3', 'pipe:1'], pcm)
        inputs = {text: speech(text, seconds, 'rms', folder)
                  for _, seconds, kind, text, _ in EVENTS if kind == 'human'}

    zero = bytes(320)
    rows, stt_rows, agent_rows, streams, native_rows = [], [], [], [], []
    hashes = {}
    native_started = None
    source_closed = False
    gate_peak = 0
    late_peak_ms = 0.
    counts = Counter()
    reader_errors = []
    original_read = AudioPipe.read
    def observed_read(pipe, size=-1):
        began = time.monotonic()
        try:
            return original_read(pipe, size)
        except Exception as error:
            row = {'pipe': next((name for s in streams for name, p in
                   (('native', s.native), ('reference', s.reference_pipe)) if p is pipe), 'opening'),
                   'requested_bytes': size, 'pending_bytes': len(pipe.buffer),
                   'elapsed_ms': round((time.monotonic()-began)*1000, 3),
                   'error_type': type(error).__name__, 'message': str(error)}
            reader_errors.append(row)
            print(json.dumps({'event': 'reader_exception', **row}), flush=True)
            raise
    AudioPipe.read = observed_read
    player = NS(entity_id=HOME, available=True, state='idle',
                volume_level=.45, is_volume_muted=False)
    started = time.monotonic()
    relative = lambda: time.monotonic() - started

    def log(event, **facts):
        row = {'at_s': round(relative(), 4), 'event': event, **facts}
        rows.append(row)
        if event in ('agent', 'output_start', 'output_end', 'output_cancel', 'checkpoint'):
            print(json.dumps(row), flush=True)

    async def tts(text):
        data = answers[text]
        class Response:
            async def iter_bytes(self):
                for offset in range(0, len(data), 2048):
                    yield data[offset:offset+2048]
                    await asyncio.sleep(.002)
        class Context:
            async def __aenter__(self): return Response()
            async def __aexit__(self, *_args): return None
        stream = await open_speech_stream(lambda: Context(), asyncio.to_thread)
        streams.append(stream)
        return stream

    async def native_start(_player, prepared, _volume):
        nonlocal native_started
        native_started = time.monotonic()
        player.state = 'playing'
        source = None
        native_count = 0
        log('output_start', answer_index=len(native_rows)+1)
        try:
            source = await open_source(prepared.native, 44100, 2, 2)
            schedule = time.monotonic()
            while data := await source.readframes(352):
                native_count += len(data)
                schedule += len(data) / (44100*2*2)
                await asyncio.sleep(max(0., schedule-time.monotonic()))
            # Same explicitly simulated 1.5s sender schedule as timing().
            await asyncio.sleep(1.5)
            log('output_end', native_bytes=native_count)
        except asyncio.CancelledError:
            log('output_cancel', native_bytes=native_count)
            raise
        finally:
            if source is not None: await source.close()
            native_rows.append({'native_bytes': native_count})
            player.state = 'idle'

    def timing(_player):
        if native_started is None or player.state != 'playing': return None
        return {'position_s': max(.001, time.monotonic()-native_started), 'latency_s': 1.5}

    output = HomePodOutput(lambda: player, tts, None,
        lambda _p: {'volume': .45, 'muted': False, 'source': 'raop', 'busy': False},
        timing, stream_start=native_start)
    observer = PlaybackObserver(lambda: output, run_executor=asyncio.to_thread)

    async def transcriber(audio):
        candidates = Counter(hashes.get(hashlib.sha256(audio[i:i+320]).digest())
                             for i in range(0, len(audio)-319, 320))
        candidates.pop(None, None)
        if not candidates: return ''
        index, _ = candidates.most_common(1)[0]
        at, _length, kind, text, _delay = EVENTS[index]
        await asyncio.sleep(.55)
        stt_rows.append({'event_index': index, 'origin': kind, 'fixture_onset_s': at,
                         'transcript': text, 'at_s': round(relative(), 4)})
        return text

    async def identity(*_args, **_kwargs): return None

    async def converse(**kwargs):
        text = kwargs['text']
        origin = stt_rows[-1]['origin']
        event_index = stt_rows[-1]['event_index']
        answer = ('I have stopped. I am listening.' if text == 'Stop speaking.' else
                  DETAIL if text == 'What was Anna carrying?' else
                  FALSE_REPLY if origin.startswith('echo') else STORY)
        row = {'input': text, 'origin': origin, 'event_index': event_index,
               'at_s': round(relative(), 4), 'answer': answer}
        agent_rows.append(row)
        log('agent', origin=origin, event_index=event_index, input=text)
        await asyncio.sleep(.15)
        return NS(conversation_id='synthetic-4min', continue_conversation=True,
                  response=NS(as_dict=lambda: {'response_type': 'query_answer',
                    'speech': {'plain': {'speech': answer}}}))

    session = None
    bridge = TurnBridge(transcriber, identity, converse,
        context_factory=lambda: NS(id='synthetic-context'), device_id='synthetic',
        satellite_id='synthetic', conversation_id='synthetic-4min',
        agent_id='scripted-boundary', language='en',
        playback_overlap=lambda _audio: output.playing(),
        transcript_filter=lambda text, audio, at: '' if output.is_own_transcript(text, audio, at) else text,
        input_allowed=lambda: not session.done and not session.closed)

    async def play(text):
        return await observer.play(output.play, text, bridge.timings_ms, output.snapshot)

    def gate(frame, current):
        nonlocal gate_peak
        value = output.gate(frame, current)
        gate_peak = max(gate_peak, output.recent_bytes + sum(len(pcm) for pcm, _p in output.pending))
        return value

    session = Session(transcribe=bridge.transcribe, respond=bridge.respond, play=play,
        stop=output.stop, gate=gate, playback_active=output.playing,
        on_capture=bridge.set_capture_time, on_interrupt=bridge.interrupted)

    async def raw_source():
        nonlocal source_closed, late_peak_ms
        try:
            for frame_index in range(round((duration+.2)*100)):
                target = started + frame_index/100
                await asyncio.sleep(max(0., target-time.monotonic()))
                late_peak_ms = max(late_peak_ms, (time.monotonic()-target)*1000)
                elapsed = frame_index/100
                selected = next(((i, event) for i, event in enumerate(EVENTS)
                                 if event[0] <= elapsed < event[0]+event[1]), None)
                audio = zero
                if selected is not None:
                    index, (at, _length, kind, text, delay) = selected
                    if kind == 'human':
                        offset = round((elapsed-at)*16000)*2
                        audio = inputs[text][offset:offset+320].ljust(320, b'\0')
                    elif output.playing() and output.reference is not None:
                        offset = round((time.monotonic()-output.started_at-delay)*16000)*2
                        offset -= offset % 2
                        ref = output.reference
                        if offset >= 0:
                            buffer = getattr(ref, '_pcm', None)
                            if buffer is None: buffer = ref.pcm
                            audio = memoryview(buffer)[offset:offset+320].tobytes().ljust(320, b'\0')
                            audio = audioop.mul(audio, 2, .37)
                            # Simple two-path synthetic room impulse response.
                            if offset >= 1120:
                                tail = memoryview(buffer)[offset-1120:offset-800].tobytes().ljust(320, b'\0')
                                audio = audioop.add(audio, audioop.mul(tail, 2, .11), 2)
                    if audioop.rms(audio, 2) > 30:
                        hashes[hashlib.sha256(audio).digest()] = index
                        counts[kind+'_frames'] += 1
                if frame_index and frame_index % 6000 == 0:
                    log('checkpoint', nominal_s=elapsed, session=session.snapshot(),
                        output={key: output.snapshot()[key] for key in ('started','completed','stopped')})
                yield audio
        finally:
            source_closed = True

    async def enhancer(source):
        async for audio in source:
            yield NS(audio=audio, speech_probability=.99 if audioop.rms(audio, 2)>30 else 0.)

    started = time.monotonic()
    log('run_start', duration_s=duration, source_fingerprint=fingerprint)
    await session.run(observer.enhanced_source(enhancer, raw_source()))
    bridge.clear()
    for stream in streams: await stream.release()
    elapsed = relative()
    faults = [row for row in agent_rows if row['origin'].startswith('echo')]
    result = {'schema': 1, 'scope': 'host_realtime_synthetic_dialogue_fault_injection',
        'started_utc': datetime.fromtimestamp(time.time()-elapsed, timezone.utc).isoformat(),
        'source_fingerprint': fingerprint, 'runtime_version': version,
        'requested_seconds': duration, 'wall_seconds': round(elapsed, 4),
        'session': session.snapshot(), 'output': output.snapshot(),
        'observer': observer.snapshot(), 'source_closed': source_closed,
        'input_frame_lateness_peak_ms': round(late_peak_ms, 3),
        'gate_buffer_peak_bytes': gate_peak, 'injected_frames': dict(counts),
        'reader_exceptions': reader_errors,
        'stt': stt_rows, 'agent': agent_rows, 'events': rows,
        'unwanted_echo_agent_turns': len(faults),
        'human_agent_turns': sum(row['origin']=='human' for row in agent_rows),
        'stream_resources': [{**s.snapshot(), 'native_readers': s.native.active_readers,
                              'reference_readers': s.reference_pipe.active_readers,
                              'producer_done': s.producer.done(), 'decoder_done': s.decoder.done()}
                             for s in streams],
        'boundaries': {'real': ['Session','Segmenter','TurnBridge','TextEcho','HomePodOutput',
                               'PlaybackObserver','streaming pipes','miniaudio1.71','pyatv0.17 audio source'],
            'simulated': ['microphone','VAD probability','ASR text and 550ms delay',
                          'identity','agent response and 150ms delay','TTS provider',
                          'RAOP receiver/1.5s timing','room impulse response'],
            'not_verified': ['real microphone','real ASR errors','speaker identity',
                             'provider latency','HomePod/network','actual room acceptance']},
        'real_microphone_opened': False, 'household_actions': False,
        'production_files_changed': False, 'synthetic_audio_only': True,
        'acoustic_fix_proved': False}
    result['checks'] = {
        'source_unchanged': source_fingerprint()==fingerprint,
        'duration_reached': elapsed >= duration-.1,
        'no_provider_failure': session.failures==0 and session.confirmation_failures==0,
        'all_workers_done': all(s.producer.done() and s.decoder.done() for s in streams),
        'all_readers_closed': all(s.native.active_readers==s.reference_pipe.active_readers==0 for s in streams),
        'pipes_within_256k_each': all(s.native.peak_bytes<=262144 and s.reference_pipe.peak_bytes<=262144 for s in streams),
        'no_echo_self_answers': not faults,
        'all_seven_human_turns_accepted': None if duration<240 else sum(row['origin']=='human' for row in agent_rows)==7,
    }
    destination.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({'event': 'result', 'path': str(destination), 'wall_seconds': result['wall_seconds'],
        'checks': result['checks'], 'session': result['session'],
        'unwanted_echo_agent_turns': len(faults), 'human_agent_turns': result['human_agent_turns']}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--duration', type=float, default=240.)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--native-deps', type=Path)
    parser.add_argument('--transport-control', action='store_true')
    parser.add_argument('--expected-source', required=True)
    args = parser.parse_args()
    if args.transport_control: EVENTS[:] = EVENTS[:3]
    if args.native_deps: sys.path.insert(0, str(args.native_deps.resolve()))
    asyncio.run(simulate(args.duration, args.output, args.expected_source))

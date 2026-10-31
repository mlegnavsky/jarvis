"""Pure, bounded voice diagnostic measurements; no HA or network dependency."""
import array
from datetime import datetime
import math
import re
import sys
import unicodedata


def audio_metrics(pcm, total_frames=None):
    if not pcm or len(pcm) % 2 or len(pcm) > 16000 * 2 * 20:
        raise ValueError('invalid_or_oversized_pcm')
    samples = array.array('h', pcm)
    if sys.byteorder != 'little':
        samples.byteswap()
    if total_frames is None: total_frames=len(samples)
    if not isinstance(total_frames,int) or total_frames<len(samples):
        raise ValueError('invalid_frame_count')
    peak = max(abs(n) for n in samples)
    rms = math.sqrt(sum(n*n for n in samples)/len(samples))
    return {'duration_s': round(total_frames/16000, 3),
            'analyzed_duration_s':round(len(samples)/16000,3),
            'truncated_analysis':total_frames>len(samples), 'sample_rate': 16000,
            'channels': 1, 'sample_bits': 16, 'peak_dbfs': round(20*math.log10(max(peak,1)/32768), 2),
            'rms_dbfs': round(20*math.log10(max(rms,1)/32768), 2),
            'clipping_percent': round(100*sum(abs(n)>=32760 for n in samples)/len(samples), 3),
            'silent': rms < 33}


def words(text):
    text = ''.join(c for c in unicodedata.normalize('NFKD', text.casefold()) if not unicodedata.combining(c))
    return re.findall(r'\w+', text)


def word_error(expected, actual):
    a, b = words(expected), words(actual)
    row = list(range(len(b)+1))
    for i, x in enumerate(a,1):
        next_row=[i]
        for j,y in enumerate(b,1):
            next_row.append(min(next_row[-1]+1,row[j]+1,row[j-1]+(x!=y)))
        row=next_row
    return round(row[-1]/max(1,len(a)),3)


def summarize_run(run_id, events):
    times = {}
    transcript = ''
    engine = None
    error = None
    continuation = None
    satellite_id = None
    timeline = []
    homepod_output = False
    for event in events:
        kind = str(event.get('type',''))
        try:
            times[kind] = datetime.fromisoformat(event['timestamp']).timestamp()
        except (KeyError,ValueError,TypeError):
            continue
        data=event.get('data') or {}
        if kind=='tts-end' and (data.get('tts_output') or {}).get('url')=='/api/jarvis_homepod_output/silence.wav':
            homepod_output=True
        timeline.append({'type':kind[:80], 'at':event['timestamp']})
        if kind=='run-start': satellite_id=data.get('satellite_id')
        if kind=='intent-end': continuation=(data.get('intent_output') or {}).get('continue_conversation')
        if kind=='stt-start': engine=data.get('engine')
        if kind=='stt-end': transcript=str(data.get('stt_output',{}).get('text',''))[:500]
        if kind=='error': error=str(data.get('code','unknown'))[:80]
    def span(a,b):
        return round(max(0,times[b]-times[a]),3) if a in times and b in times else None
    return {'id':str(run_id), 'started_at':next((e.get('timestamp') for e in events if e.get('type')=='run-start'),None),
            'complete':'run-end' in times,'error':error,'engine':engine,'transcript':transcript,
            'continue_conversation':continuation,'satellite_id':satellite_id,
            'speech_started':'stt-vad-start' in times,'timeline':timeline[-40:],
            'outcome':('error' if error else 'in_progress' if 'run-end' not in times else 'no_transcript_observed' if not transcript.strip() else 'intent_completed' if 'intent-end' in times else 'transcript_only'),
            'timings_s':{'capture_until_vad_end':span('stt-start','stt-vad-end'),
                         'stt_processing':span('stt-vad-end','stt-end'),
                         'stt_including_capture':span('stt-start','stt-end'),
                         'intent':span('intent-start','intent-end'),
                         'tts_generation_or_cache':None if homepod_output else span('tts-start','tts-end'),
                         'tts_synthesis_and_homepod_output':span('tts-start','tts-end') if homepod_output else None,
                         'total_pipeline':span('run-start','run-end')},
            'note':('Pipeline includes awaited HomePod rendering/playback; satellite receives only silent completion.' if homepod_output else 'Pipeline completion excludes satellite audio download and playback.')}


def merge_runs(previous, current, limit=20):
    merged={r['id']:r for r in previous if isinstance(r,dict) and 'id' in r}
    merged.update({r['id']:r for r in current if isinstance(r,dict) and 'id' in r})
    return sorted(merged.values(),key=lambda r:r.get('started_at') or '')[-limit:]

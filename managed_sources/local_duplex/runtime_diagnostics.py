"""Bounded private metadata for actual dialogue, never a microphone recorder."""
from collections import deque
from datetime import datetime, timezone
import time


def notify(callback, event, **facts):
    # An observer must never become part of the household command decision.
    if callback is not None:
        try:callback(event, **facts)
        except Exception:pass


class RuntimeTrace:
    def __init__(self, run_id, *, wake_word=None, clock=time.monotonic):
        self.run_id=str(run_id);self.clock=clock;self.started=clock()
        self.wake_word=wake_word[:64] if isinstance(wake_word,str) else None
        self.started_at=datetime.now(timezone.utc).isoformat()
        self.events=deque(maxlen=48);self.dropped_events=0
        self.emit('activation', source='native_pipeline', wake_word=self.wake_word)

    def emit(self, event, **facts):
        if len(self.events)==self.events.maxlen:self.dropped_events+=1
        if 'transcript' in facts:
            text=str(facts['transcript'] or '')
            facts['transcript']=text[:240]
            facts['transcript_truncated']=len(text)>240
        # Callers supply only scalar metadata, never PCM, response bodies or errors.
        facts={key:value for key,value in facts.items()
               if value is None or type(value) in (str,bool,int,float)}
        self.events.append({'event':event,'elapsed_ms':round((self.clock()-self.started)*1000,1),**facts})

    def snapshot(self):
        return {'run_id':self.run_id,'started_at':self.started_at,
            'activation_source':'native_pipeline','wake_word':self.wake_word,'acoustic_verified':False,
            'wake_word_note':'reported native hint only; no acoustic attribution',
            'raw_microphone_saved':False,'transcript_limit':240,
            'dropped_events':self.dropped_events,'events':[dict(e) for e in self.events]}

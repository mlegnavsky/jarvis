"""Bounded generated-speech fingerprints; microphone transcripts are never saved."""
import math
import re
import unicodedata
if __package__:
    from custom_components.jarvis_voice_common import command_action
else:
    from managed_sources.voice_common import command_action


def words(text):
    value=''.join(c for c in unicodedata.normalize('NFKD',str(text).casefold())
                  if not unicodedata.combining(c))
    return tuple('jarvis' if word in ('dzarvis','dzarvisi','jarvisi') else word
                 for word in re.findall(r'\w+',value))


class TextEcho:
    def __init__(self):self.records=[]

    def remember(self,text,*,started_at,duration,tail):
        if not all(isinstance(n,(int,float)) and not isinstance(n,bool) and math.isfinite(n)
                   for n in (started_at,duration,tail)) or not 0<duration<=90 or not 0<=tail<=11:
            raise ValueError('invalid_speech_interval')
        tokens=words(text)
        if not tokens:return
        self.records=[r for r in self.records if r['until']>=started_at-8][-2:]
        self.records.append({'words':tokens[:2000],'start':started_at,'until':started_at+duration+tail})

    def stopped(self,*,at,tail):
        if self.records:self.records[-1]['until']=min(self.records[-1]['until'],at+tail)

    def matches(self,text,*,captured_from,captured_until):
        if not (math.isfinite(captured_from) and math.isfinite(captured_until)
                and captured_from<=captured_until):return False
        candidate=words(text)
        if not candidate:return False
        for record in self.records:
            if captured_until<record['start'] or captured_from>record['until']:continue
            overlap=min(captured_until,record['until'])-max(captured_from,record['start'])
            if overlap<.5*(captured_until-captured_from):continue
            original=record['words']
            if len(candidate)==1:
                if candidate[0]==original[0] or (command_action(candidate[0]) is not None
                                            and candidate[0] in original):return True
                continue
            if len(candidate)>len(original):continue
            if any(original[i:i+len(candidate)]==candidate for i in range(len(original)-len(candidate)+1)):
                return True
        return False

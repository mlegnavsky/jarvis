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


def protected_word(word):
    return (word.startswith(('ne','zapn','vypn','rozsv','zhas','zamk','odemk','otev','zavr','zastav','spust','pust'))
            or word in ('stop','stuj','ticho','dost','staci','prestan','pockej')
            or command_action(word) is not None)


def variant_distance(candidate,original):
    """Bounded anchored phrase distance; never remove a novel human prefix."""
    count=len(candidate)
    if not 4<=count<=64:return None
    original_words=set(original)
    # New negation/stop/control words express a correction. A tolerant echo
    # fingerprint must never erase them as an ordinary recognition edit.
    if any(word not in original_words and protected_word(word) for word in candidate):return None
    protected_candidate=[protected_word(word) for word in candidate]
    budget=min(2,max(1,count//5));spent=0
    for start,word in enumerate(original):
        if word!=candidate[0]:continue
        target=original[start:start+count+budget];size=len(target)
        if size<count-budget:continue
        protected_target=[protected_word(word) for word in target]
        infinity=budget+1
        previous=[0]+[infinity]*size
        for j in range(1,size+1):
            if not protected_target[j-1]:previous[j]=min(infinity,previous[j-1]+1)
        for i,token in enumerate(candidate,1):
            current=[infinity]*(size+1)
            if not protected_candidate[i-1]:current[0]=min(infinity,previous[0]+1)
            for j in range(max(1,i-budget),min(size,i+budget)+1):
                spent+=1
                if spent>20000:return None
                same=token==target[j-1]
                current[j]=min(current[j-1]+(infinity if protected_target[j-1] else 1),
                    previous[j]+(infinity if protected_candidate[i-1] else 1),
                    previous[j-1]+(0 if same else infinity if protected_target[j-1] or protected_candidate[i-1] else 1))
            previous=current
        distance=min(previous[max(1,count-budget):])
        if distance<=budget:return distance
    return None


class TextEcho:
    def __init__(self):self.records=[];self.last_facts={}

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
        self.last_facts={'decision':'no_recent_output','candidate_words':0,
            'reference_words':0,'shared_words':0,'overlap_ratio':0.,'edit_distance':None}
        if not (math.isfinite(captured_from) and math.isfinite(captured_until)
                and captured_from<=captured_until):
            self.last_facts['decision']='invalid_timing';return False
        candidate=words(text)
        self.last_facts['candidate_words']=len(candidate)
        if not candidate:return False
        if self.records:self.last_facts['decision']='outside_output_interval'
        for record in self.records:
            if captured_until<record['start'] or captured_from>record['until']:continue
            overlap=min(captured_until,record['until'])-max(captured_from,record['start'])
            original=record['words']
            original_set=set(original)
            ratio=round(overlap/max(.001,captured_until-captured_from),4)
            facts={'decision':'different_words' if ratio>=.5 else 'insufficient_overlap',
                'candidate_words':len(candidate),'reference_words':len(original),'overlap_ratio':ratio,
                'shared_words':sum(word in original_set for word in candidate),'edit_distance':None}
            if ratio>=self.last_facts['overlap_ratio']:self.last_facts=facts
            if overlap<.5*(captured_until-captured_from):continue
            if len(candidate)==1:
                if candidate[0]==original[0] or (command_action(candidate[0]) is not None
                                            and candidate[0] in original):
                    facts.update(decision='generated_single_word',edit_distance=0);self.last_facts=facts;return True
                continue
            if any(original[i:i+len(candidate)]==candidate for i in range(len(original)-len(candidate)+1)):
                facts.update(decision='generated_exact_phrase',edit_distance=0);self.last_facts=facts;return True
            if (distance:=variant_distance(candidate,original)) is not None:
                facts.update(decision='generated_asr_variant',edit_distance=distance);self.last_facts=facts;return True
        return False

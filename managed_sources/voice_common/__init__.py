"""Pure shared command contract for the Jarvis voice stack.

No devices, storage, authentication, audio or HA lifecycle are owned here.
"""
from dataclasses import dataclass
import re
import unicodedata

VERSION='1.0.2'

def normalized(text):
    return ' '.join(re.findall(r'\w+', ''.join(c for c in unicodedata.normalize('NFKD',str(text).casefold()) if not unicodedata.combining(c))))

def strip_address(text):
    return re.sub(r'^(?:(?:hej|hey) )?(?:anicko|jarvis|jarvisi|dzarvis|dzarvisi)\s+','',normalized(text))

@dataclass(frozen=True)
class Command:
    canonical: str
    domain: str
    service: str
    scope: str
    room: str|None=None


def contains_quotes(text):
    return any(char in str(text) for char in ('"',"'",'„','“','”','«','»','`'))

def parse_command(text):
    # Quoted examples are data, including when a wake name precedes them.
    if contains_quotes(text):return None
    value=strip_address(text)
    light_verb=r'(?:rozsvit|rozsvitit|zhasni|zhasnout|zapni|zapnout|vypni|vypnout)\b'
    value=re.sub(r'^(?:ano|jo|jasne) (?=(?:prosim\b|muzes\b|'+light_verb+'))','',value)
    value=re.sub(r'^(?:muzes|mohla bys)(?: mi)?(?: prosim(?: te)?)? (?='+light_verb+')','',value)
    value=re.sub(r'^prosim(?: te)?\s+','',value)
    value=re.sub(r'\s+prosim(?: te)?$','',value)
    value=re.sub(r' at tady lepe vidim$','',value)
    # STT may choose the Czech infinitive for an otherwise exact imperative.
    verbs={'rozsvitit':'rozsvit','zhasnout':'zhasni','zapnout':'zapni','vypnout':'vypni'}
    value=re.sub(r'^(rozsvitit|zhasnout|zapnout|vypnout)\b',lambda match:verbs[match[1]],value)
    value=re.sub(r'^(rozsvit|zhasni|zapni|vypni) prosim(?: te)?(?: |$)',r'\1 ',value).strip()
    value=re.sub(r'^(rozsvit|zhasni|zapni|vypni) (?:mi|me) ',r'\1 ',value)
    if value in ('zamkni','zamkni hlavni vchod','odemkni','odemkni hlavni vchod'):
        return Command(value,'lock','lock' if value.startswith('zamkni') else 'unlock','entrance')
    # Zapni/vypni alone must never guess the device domain.
    value=re.sub(r'^zapni (?=svetlo\b|svetla\b|vsechna svetla\b)','rozsvit ',value)
    value=re.sub(r'^vypni (?=svetlo\b|svetla\b|vsechna svetla\b)','zhasni ',value)
    match=re.fullmatch(r'(rozsvit|zhasni)(?: (?:svetlo|svetla))? vsude|(rozsvit|zhasni) vsechna svetla',value)
    if match:
        verb=match[1] or match[2]
        return Command(verb+' vsude','light','turn_on' if verb=='rozsvit' else 'turn_off','all')
    match=re.fullmatch(r'(rozsvit|zhasni)(?: (?:to|svetlo|svetla))?(?: (?:v|ve) ([\w ]+))?',value)
    if not match:return None
    verb,room=match.groups()
    if room and re.search(r'\b(a|pak|potom|na|za|ale|az|kdyz|pokud|jestli|nebo)\b',room):return None
    return Command(value,'light','turn_on' if verb=='rozsvit' else 'turn_off','room' if room else 'current',room)


def canonical_command(text):
    command=parse_command(text)
    return command.canonical if command else None


def command_action(text):
    command=parse_command(text)
    return (command.domain,command.service) if command else None


def is_noise_transcript(text):
    value=normalized(text)
    echo='the following conversation is a smart home user talking to home assistant'
    return not value or value in {'context','blank_audio','silence','no','hm','hmm','ehm','mmm',echo,'context '+echo}


def complete_light_utterance(prefix,text,*,allow_bare=False):
    """Complete an acoustic activation only after its full continuation ended."""
    hint=parse_command(prefix)
    if not hint or hint.domain!='light' or hint.scope!='current' or contains_quotes(text):return ''
    explicit=parse_command(text)
    if explicit is not None:
        return explicit.canonical if explicit.domain=='light' else ''
    if is_noise_transcript(text):
        return hint.canonical if allow_bare else ''
    combined=parse_command(hint.canonical+' '+str(text))
    return combined.canonical if combined and combined.domain=='light' else ''

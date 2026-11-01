"""Pure shared command contract for the Jarvis voice stack.

No devices, storage, authentication, audio or HA lifecycle are owned here.
"""
from dataclasses import dataclass
import re
import unicodedata

VERSION='1.0.0'

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
    value=re.sub(r'^prosim(?: te)?\s+','',value)
    value=re.sub(r'\s+prosim(?: te)?$','',value)
    value=re.sub(r' at tady lepe vidim$','',value)
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

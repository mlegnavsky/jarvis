"""One-use active-utterance grants; matching a voice is not HA authentication."""
import re
import secrets
import time
if __package__:
 from .policy import norm
else:
 from policy import norm

LOCK='lock.vstup_zamek_vchod'
def canonical_command(text):
 value=norm(text)
 value=re.sub(r'^anicko\s+','',value)
 value=re.sub(r'^prosim(?: te)?\s+','',value)
 value=re.sub(r'\s+prosim(?: te)?$','',value)
 # Only finite courtesy wrappers, never arbitrary trailing clauses/actions.
 value=re.sub(r' at tady lepe vidim$','',value)
 value=re.sub(r'^(rozsvit|zhasni) (?:mi|me) ',r'\1 ',value)
 if value in ('zamkni','zamkni hlavni vchod','odemkni','odemkni hlavni vchod'):return value
 match=re.fullmatch(r'(rozsvit|zhasni)(?: (?:to|svetlo|svetla))?(?: (?:v|ve) (?!.*\b(?:a|pak|potom|na|za|ale|az|kdyz|pokud|jestli|nebo)\b)[\w ]+)?',value)
 if match:return value
 return None

def command(text):
 value=canonical_command(text)
 if value is None:return None
 if value.startswith('zamkni'):return ('lock','lock')
 if value.startswith('odemkni'):return ('lock','unlock')
 return ('light','turn_on' if value.startswith('rozsvit') else 'turn_off')

class VoiceGate:
 def __init__(self,clock=time.monotonic,challenge_words=()):
  self.clock=clock;self.grants={};self.waiting={};self.challenge_words=challenge_words
 def issue(self,device,text,voice_id,authorized):
  if not authorized or not voice_id or not device:return None
  self.grants={k:v for k,v in self.grants.items() if 0<=self.clock()-v['at']<=15}
  token=secrets.token_urlsafe(24)
  self.grants[token]={'at':self.clock(),'device':device,'text':norm(text),'action':command(text),'voice_id':voice_id}
  while len(self.grants)>64:self.grants.pop(next(iter(self.grants)))
  return token
 def bind(self,token,device,text,action,targets):
  grant=self.grants.get(token)
  if not grant or grant['device']!=device or grant['text']!=norm(text) or grant['action']!=action or 'targets' in grant:return False
  if action[0]=='lock' and targets!=((LOCK,),'vstup'):return False
  grant['targets']=targets;return True
 def consume(self,token,device,text,action,targets=None):
  grant=self.grants.pop(token,None)
  return bool(grant and 0<=self.clock()-grant['at']<=15 and grant['device']==device
              and grant['text']==norm(text) and grant['action']==action
              and (targets is None or grant.get('targets')==targets))
 def pending(self,device,text):
  challenge=' '.join(secrets.choice(self.challenge_words) for _ in range(3)) if self.challenge_words and command(text) and command(text)[0]=='lock' else ''
  if command(text):self.waiting[device]={'at':self.clock(),'text':norm(text),'action':command(text),'challenge':challenge}
  while len(self.waiting)>16:self.waiting.pop(next(iter(self.waiting)))
  return challenge
 def confirm(self,device,text,authorized):
  slot=self.waiting.get(device)
  if not slot:return None
  if not authorized or not 0<=self.clock()-slot['at']<=60:
   self.waiting.pop(device,None);return None
  value=re.sub(r'^anicko\s+','',norm(text))
  expected={('lock','unlock'):'potvrzuji odemknuti hlavniho vchodu',
            ('lock','lock'):'potvrzuji zamknuti hlavniho vchodu',
            ('light','turn_on'):'potvrzuji rozsviceni svetel v teto mistnosti',
            ('light','turn_off'):'potvrzuji zhasnuti svetel v teto mistnosti'}
  phrase=expected.get(slot['action'],'')+(' '+slot['challenge'] if slot.get('challenge') else '')
  if value!=phrase:return None
  self.waiting.pop(device,None)
  # Roomless short commands only. Named-room confirmation must not lose scope.
  return slot['text'] if slot['text'] in ('zamkni','odemkni','zhasni','rozsvit') else None
 def cancel(self,device):
  self.waiting.pop(device,None)
  self.grants={k:v for k,v in self.grants.items() if v['device']!=device}

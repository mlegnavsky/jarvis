"""Bounded local companion notes/topics and optional-joke filtering; no HA/API I/O."""
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import threading
import time
import unicodedata


def normalize(text):
 return ' '.join(re.findall(r'\w+',''.join(c for c in unicodedata.normalize('NFKD',text.casefold()) if not unicodedata.combining(c))))

ADDRESSES={'martin':'Martine','sarlota':'Šarloto','iris':'Iris','petr':'Petře','dana':'Dano'}

def session_address(text):
 value=normalize(text)
 for prefix in ('jsem ','tady je ','tady '):
  if value.startswith(prefix):
   name=value[len(prefix):]
   if name in ADDRESSES:return ADDRESSES[name]
 return None


def memory_command(text):
 match=re.match(r'^\s*zapamatuj\s+si\s+pro\s+domácnost\s*:?\s+(.+?)\s*$',text,re.I|re.S)
 if match:return 'household',match.group(1)[:600]
 match=re.match(r'^\s*zapamatuj\s+si\s*:?\s+(.+?)\s*$',text,re.I|re.S)
 if match:return 'private',match.group(1)[:600]
 return None


def serious_topic(text):
 value=normalize(text)
 return any(word in value.split() for word in ('pomoc','bolest','krvaceni','pozar','unik','plyn','alarm','nehoda','zraneni','umrti','smrt','nemoc','heslo','soukrome','zaplava'))


def blank():return {'notes':[],'topics':[],'jokes':[],'turns':0}

class MemoryStore:
 def __init__(self,path=None,clock=time.time):
  self.path=Path(path) if path else None;self.clock=clock;self.lock=threading.RLock();self.cache={}
 def _state(self,key,change=None):
  if not isinstance(key,str) or not key or len(key)>200:raise ValueError('invalid_memory_principal')
  with self.lock:
   if self.path is None:
    if key not in self.cache and len(self.cache)>=64:self.cache.pop(next(iter(self.cache)))
    state=json.loads(json.dumps(self.cache.get(key,blank())))
    result=change(state) if change else None
    if change:self.cache[key]=state
   else:
    self.path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    if self.path.is_symlink():raise ValueError('unsafe_memory_path')
    with sqlite3.connect(self.path,timeout=5) as db:
     self.path.chmod(0o600)
     db.execute('CREATE TABLE IF NOT EXISTS profiles (key TEXT PRIMARY KEY, payload TEXT NOT NULL)')
     db.execute('BEGIN IMMEDIATE')
     row=db.execute('SELECT payload FROM profiles WHERE key=?',(key,)).fetchone()
     state=json.loads(row[0]) if row else blank()
     result=change(state) if change else None
     if change:
      if not row and db.execute('SELECT count(*) FROM profiles').fetchone()[0]>=128:raise ValueError('memory_profile_limit')
      payload=json.dumps(state,ensure_ascii=False)
      if len(payload.encode())>64000:raise ValueError('memory_profile_size_limit')
      db.execute('INSERT OR REPLACE INTO profiles VALUES (?,?)',(key,payload))
   return result if change else state
 def context(self,key):
  s=self._state(key)
  last=max((j['turn'] for j in s['jokes']),default=-100)
  return {'notes':s['notes'][-20:],'topics':s['topics'][-8:],
          'humor_allowed':s['turns']-last>=2,'turns':s['turns']}
 def note(self,principal,text,key=None):
  note_key=key # named note updates replace the prior value
  def update(s):
   item={'text':str(text)[:600],'at':self.clock(),'source':'explicit_user_statement','key':note_key}
   if note_key:s['notes']=[x for x in s['notes'] if x.get('key')!=note_key]
   s['notes']=(s['notes']+[item])[-20:]
   return item
  return self._state(principal,update)
 def topic(self,key,conversation,text):
  def update(s):
   s['topics']=(s['topics']+[{'text':text[:600],'conversation':str(conversation)[:128],
                            'at':self.clock(),'source':'original_user_utterance'}])[-8:]
  self._state(key,update)
 def forget(self,key):self._state(key,lambda s:(s.clear(),s.update(blank())))
 def finish(self,key,joke,allow):
  tokens={hashlib.sha256(t.encode()).hexdigest()[:16] for t in normalize(joke).split()}
  def update(s):
   s['turns']+=1
   prior=[j for j in s['jokes'] if 0<=self.clock()-j['at']<=30*86400]
   repeated=any(len(tokens & set(j['tokens']))/max(1,len(tokens | set(j['tokens'])))>=.75 for j in prior)
   last=max((j['turn'] for j in prior),default=-100)
   accepted=bool(joke.strip() and allow and not repeated and s['turns']-last>=3)
   if accepted:prior.append({'tokens':sorted(tokens)[:60],'at':self.clock(),'turn':s['turns']})
   s['jokes']=prior[-20:]
   return accepted
  return self._state(key,update)


def finish_response(text,store,principal,allow_humor):
 # Drop only recognized optional joke blocks; never discard substantive text
 # following a misplaced block. Unbalanced markers are removed without hiding
 # their contents because those contents could contain important information.
 pattern=re.compile(r'⟦vtip⟧(.*?)⟦/vtip⟧',re.S)
 blocks=list(pattern.finditer(text))
 plain=pattern.sub('',text).replace('⟦vtip⟧','').replace('⟦/vtip⟧','').strip()
 eligible=(len(blocks)==1 and not text[blocks[0].end():].strip()
           and bool(text[:blocks[0].start()].strip()) and '⟦vtip⟧' not in blocks[0].group(1))
 joke=blocks[0].group(1).strip() if eligible else ''
 accepted=store.finish(principal,joke,allow_humor and eligible)
 return (plain+(' '+joke if accepted else '')).strip()


def fictional_probe():
 import tempfile
 with tempfile.TemporaryDirectory(prefix='jarvis-fictional-memory-') as folder:
  path=Path(folder)/'probe.sqlite';s=MemoryStore(path,clock=lambda:1000.)
  s.note('auth:fictional_a','Modrý drak Róza.')
  isolated=not s.context('auth:fictional_b')['notes']
  persisted=MemoryStore(path).context('auth:fictional_a')['notes'][0]['text']=='Modrý drak Róza.'
  s.topic('auth:fictional_a','old','Připravuji zahradu.')
  topic=s.context('auth:fictional_a')['topics'][0]['source']=='original_user_utterance'
  joke='Světlo je zhasnuté. ⟦vtip⟧Elektrárna pláče.⟦/vtip⟧'
  first=finish_response(joke,s,'auth:fictional_a',True)
  repeat=finish_response(joke,s,'auth:fictional_a',True)
  preserved=finish_response('Hotovo. ⟦vtip⟧Vtip.⟦/vtip⟧ Ventil se nezavřel.',s,'auth:fictional_a',False)
  s.forget('auth:fictional_a')
  checks={'profile_isolation':isolated,'restart_persistence':persisted,'dated_source_topic':topic,
          'first_joke_allowed':'Elektrárna' in first,'duplicate_removed':repeat=='Světlo je zhasnuté.',
          'substantive_remainder_preserved':'Ventil se nezavřel.' in preserved,
          'forget_verified':not s.context('auth:fictional_a')['notes']}
  return {'passed':all(checks.values()),'scope':'temporary fictional profiles; no household notes changed','checks':checks}

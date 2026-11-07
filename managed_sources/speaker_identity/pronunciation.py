"""Owner-confirmed vocabulary aliases; entirely separate from voice matching."""
if __package__:
 from .policy import norm
else:
 from policy import norm
class Pronunciation:
 def __init__(self,profiles):self.profiles=profiles;self.pending={}
 def propose(self,voice_id,heard,canonical):
  heard,canonical=norm(heard),norm(canonical)
  if not self.profiles.is_authorized(voice_id) or canonical not in ('rozsvit','zhasni','zamkni','odemkni') or not heard or len(heard)>40 or len(heard.split())!=1 or heard in ('anicko','rozsvit','zhasni','zamkni','odemkni'):raise ValueError('invalid_alias')
  self.pending[voice_id]=(heard,canonical,self.profiles.clock())
  return {'status':'confirmation_required'}
 def confirm(self,voice_id,heard,canonical):
  slot=self.pending.pop(voice_id,None)
  if not slot or slot[:2]!=(norm(heard),norm(canonical)) or not 0<=self.profiles.clock()-slot[2]<=60 or not self.profiles.is_authorized(voice_id):raise ValueError('confirmation_required')
  with self.profiles._db() as db:
   db.execute('CREATE TABLE IF NOT EXISTS voice_aliases (voice_id TEXT,heard TEXT,canonical TEXT,PRIMARY KEY(voice_id,heard))')
   if db.execute('SELECT count(*) FROM voice_aliases WHERE voice_id=?',(voice_id,)).fetchone()[0]>=32:raise ValueError('alias_limit')
   db.execute('INSERT OR REPLACE INTO voice_aliases VALUES (?,?,?)',(voice_id,slot[0],slot[1]))
  return {'status':'confirmed'}
 def resolve(self,voice_id,text):
  text=norm(text)
  if not self.profiles.is_authorized(voice_id):return text
  with self.profiles._db() as db:
   db.execute('CREATE TABLE IF NOT EXISTS voice_aliases (voice_id TEXT,heard TEXT,canonical TEXT,PRIMARY KEY(voice_id,heard))')
   row=db.execute('SELECT canonical FROM voice_aliases WHERE voice_id=? AND heard=?',(voice_id,text)).fetchone()
   return row[0] if row else text

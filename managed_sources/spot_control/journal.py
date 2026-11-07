"""Permanent local control evidence. No retention deletion or credentials."""
from contextlib import contextmanager
import json
import math
import os
import sqlite3
import threading
import time

class Journal:
 def __init__(self,path):
  self.path=str(path);self.lock=threading.RLock()
  with self.db() as db:
   db.execute('PRAGMA journal_mode=WAL')
   db.execute('CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY, t REAL NOT NULL, kind TEXT NOT NULL, payload TEXT NOT NULL)')
   db.execute('CREATE INDEX IF NOT EXISTS events_time ON events(t)')
   db.execute('CREATE TABLE IF NOT EXISTS commands(id TEXT PRIMARY KEY, body TEXT NOT NULL)')
  os.chmod(self.path,0o600)
 @contextmanager
 def db(self):
  with self.lock:
   db=sqlite3.connect(self.path,timeout=20)
   db.execute('PRAGMA synchronous=FULL')
   try:
    with db:yield db
   finally:db.close()
 def append(self,kind,payload,t=None):
  stamp=time.time() if t is None else float(t)
  if not math.isfinite(stamp) or stamp<0:raise ValueError('Invalid event time')
  if not isinstance(kind,str) or not kind or len(kind)>64:raise ValueError('Invalid event kind')
  body=json.dumps(payload,ensure_ascii=False,separators=(',',':'),allow_nan=False)
  with self.db() as db:
   cursor=db.execute('INSERT INTO events(t,kind,payload) VALUES(?,?,?)',(stamp,kind,body))
   return cursor.lastrowid
 def recent(self,limit=100):
  if type(limit) is not int or not 1<=limit<=1000:raise ValueError('Invalid history limit')
  with self.db() as db:
   rows=db.execute('SELECT id,t,kind,payload FROM events ORDER BY id DESC LIMIT ?',(limit,)).fetchall()
  return [{'id':r[0],'t':r[1],'kind':r[2],'payload':json.loads(r[3])} for r in reversed(rows)]
 def after(self,cursor,limit=100):
  if type(cursor) is not int or cursor<0 or type(limit) is not int or not 1<=limit<=1000:raise ValueError('Invalid history cursor')
  with self.db() as db:rows=db.execute('SELECT id,t,kind,payload FROM events WHERE id>? ORDER BY id LIMIT ?',(cursor,limit)).fetchall()
  return [{'id':r[0],'t':r[1],'kind':r[2],'payload':json.loads(r[3])} for r in rows]

 def claim_command(self,body):
  key=body['id'];encoded=json.dumps(body,sort_keys=True,allow_nan=False)
  with self.db() as db:
   cursor=db.execute('INSERT OR IGNORE INTO commands(id,body) VALUES(?,?)',(key,encoded))
   return cursor.rowcount==1

 def page(self,after=0,limit=100,since=None,until=None,kind=None,sale_id=None,until_id=None):
  """Stable ascending cursors over existing rows; no migration or deletion."""
  if type(after) is not int or after<0 or type(limit) is not int or not 1<=limit<=1000:
   raise ValueError('Invalid history cursor or limit')
  for value in (since,until):
   if value is not None and (type(value) not in (int,float) or not math.isfinite(value) or value<0):
    raise ValueError('Invalid history time filter')
  if since is not None and until is not None and since>until:raise ValueError('Invalid history interval')
  for value,maximum in ((kind,64),(sale_id,128)):
   if value is not None and (not isinstance(value,str) or not 1<=len(value)<=maximum):raise ValueError('Invalid history filter')
  if until_id is not None and (type(until_id) is not int or until_id<after):raise ValueError('Invalid history upper cursor')
  with self.db() as db:high=db.execute('SELECT COALESCE(MAX(id),0) FROM events').fetchone()[0] if until_id is None else until_id
  clauses=['id>?','id<=?'];args=[after,high]
  for column,operator,value in (('t','>=',since),('t','<=',until),('kind','=',kind)):
   if value is not None:clauses.append(column+operator+'?');args.append(value)
  if sale_id is not None:
   clauses.append("CASE WHEN json_valid(payload) THEN COALESCE(json_extract(payload,'$.sale_id'),json_extract(payload,'$.id')) END=?")
   args.append(sale_id)
  with self.db() as db:
   rows=db.execute('SELECT id,t,kind,payload FROM events WHERE '+' AND '.join(clauses)+' ORDER BY id LIMIT ?',(*args,limit+1)).fetchall()
  events=[{'id':r[0],'t':r[1],'kind':r[2],'payload':json.loads(r[3])} for r in rows[:limit]]
  return {'events':events,'next_cursor':events[-1]['id'] if events else after,
          'has_more':len(rows)>limit,'until_id':high,'retention':'permanent'}

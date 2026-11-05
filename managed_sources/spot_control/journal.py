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

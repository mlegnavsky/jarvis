"""Durable outbox. Remove only an exactly acknowledged immutable batch."""
import hashlib, json, os, sqlite3
from contextlib import contextmanager
class Outbox:
 def __init__(self,path,limit=64*1024*1024):
  self.path=str(path);self.limit=limit
  with self.db() as db:
   db.execute('CREATE TABLE IF NOT EXISTS queue(id INTEGER PRIMARY KEY, body TEXT NOT NULL)')
   db.execute('CREATE TABLE IF NOT EXISTS flight(key TEXT PRIMARY KEY, last_id INTEGER, body TEXT)')
  os.chmod(self.path,0o600)
 @contextmanager
 def db(self):
  db=sqlite3.connect(self.path)
  try:
   with db:yield db
  finally:db.close()
 def count(self):
  with self.db() as db:return db.execute('SELECT count(*) FROM queue').fetchone()[0]
 def append(self,record):
  body=json.dumps(record,separators=(',',':'),allow_nan=False)
  with self.db() as db:
   size=db.execute('SELECT coalesce(sum(length(body)),0) FROM queue').fetchone()[0]
   if size+len(body)>self.limit:raise RuntimeError('Local archive queue is full; capture paused, existing records preserved')
   db.execute('INSERT INTO queue(body) VALUES(?)',(body,))
 def batch(self):
  with self.db() as db:
   current=db.execute('SELECT key,body FROM flight LIMIT 1').fetchone()
   if current:return current
   rows=db.execute('SELECT id,body FROM queue ORDER BY id LIMIT 12').fetchall()
   if not rows:return None
   body='['+','.join(r[1] for r in rows)+']';key=hashlib.sha256(body.encode()).hexdigest()
   db.execute('INSERT INTO flight VALUES(?,?,?)',(key,rows[-1][0],body));return key,body
 def ack(self,key,received):
  if received!=key:raise ValueError('Archive acknowledgement mismatch')
  with self.db() as db:
   row=db.execute('SELECT last_id FROM flight WHERE key=?',(key,)).fetchone()
   if not row:raise ValueError('Unknown acknowledgement')
   db.execute('DELETE FROM queue WHERE id<=?',(row[0],));db.execute('DELETE FROM flight WHERE key=?',(key,))

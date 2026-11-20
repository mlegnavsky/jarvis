"""Owner-started collection only. Never assigns identity or promotes a profile."""
import json
import math
import re
if __package__:
 from .policy import MODEL_ID,norm,unit,similarity,centroid,profile_score,profile_threshold
else:
 from policy import MODEL_ID,norm,unit,similarity,centroid,profile_score,profile_threshold

class OwnerCalibration:
 def __init__(self,profiles,satellite):self.profiles=profiles;self.satellite=satellite
 def db(self):
  db=self.profiles._db();db.execute('BEGIN IMMEDIATE')
  db.execute('CREATE TABLE IF NOT EXISTS owner_calibration_sessions (id TEXT PRIMARY KEY,voice_id TEXT,device TEXT,created REAL,expires REAL,status TEXT,rejections INTEGER DEFAULT 0)')
  if 'mode' not in {x[1] for x in db.execute('PRAGMA table_info(owner_calibration_sessions)')}:db.execute("ALTER TABLE owner_calibration_sessions ADD COLUMN mode TEXT NOT NULL DEFAULT 'calibration'")
  db.execute('CREATE TABLE IF NOT EXISTS owner_calibration_windows (session TEXT,utterance TEXT,windows TEXT,PRIMARY KEY(session,utterance))')
  db.execute('CREATE TABLE IF NOT EXISTS owner_calibration_requests (id TEXT PRIMARY KEY,expires REAL)')
  db.execute('CREATE TABLE IF NOT EXISTS owner_calibration_samples (session TEXT,utterance TEXT,vector TEXT,diagnostic TEXT,PRIMARY KEY(session,utterance))')
  db.commit();return db
 def process_control(self,path):
  if not path.exists():return {'status':'no_request'}
  try:
   if path.is_symlink() or path.stat().st_size>4096:raise ValueError('unsafe_request')
   request=json.loads(path.read_text())
   if not isinstance(request,dict) or set(request)!={'request_id','action','profile','issued_at'}:raise ValueError('invalid_request')
   key=request['request_id'];issued=request['issued_at'];now=self.profiles.clock()
   if not isinstance(key,str) or not re.fullmatch('[a-f0-9]{32}',key):raise ValueError('invalid_request')
   if type(issued) not in (int,float) or not math.isfinite(issued) :raise ValueError('invalid_timestamp')
   if request['action'] not in ('start','resume','repair') or not isinstance(request['profile'],str) or len(request['profile'])>40:raise ValueError('invalid_request')
   with self.db() as db:
    db.execute('BEGIN IMMEDIATE')
    if db.execute('SELECT 1 FROM owner_calibration_requests WHERE id=?',(key,)).fetchone():return {'status':'already_consumed'}
    if not 0<=now-issued<=120:raise ValueError('stale_request')
    db.execute('DELETE FROM owner_calibration_requests WHERE expires<?',(now,))
    if db.execute('SELECT count(*) FROM owner_calibration_requests').fetchone()[0]>=512:raise ValueError('request_limit')
    row=db.execute('SELECT v.voice_id FROM voices v JOIN voice_authorizations a ON a.voice_id=v.voice_id WHERE v.name=? AND v.model=?',(norm(request['profile']),MODEL_ID)).fetchone()
    if not row:raise ValueError('authorized_existing_profile_required')
    if request['action']=='resume':
     previous=db.execute('SELECT id,voice_id,status,mode FROM owner_calibration_sessions WHERE device=? ORDER BY rowid DESC LIMIT 1',(self.satellite,)).fetchone()
     if not previous or previous[1]!=row[0] or previous[2] not in ('expired','paused','collecting'):raise ValueError('matching_unfinished_session_required')
     count=db.execute('SELECT count(*) FROM owner_calibration_samples WHERE session=?',(previous[0],)).fetchone()[0]
     required=2 if previous[3]=='repair' else 5
     if count>=required:raise ValueError('session_complete')
     db.execute('INSERT INTO owner_calibration_requests VALUES (?,?)',(key,now+600))
     db.execute("UPDATE owner_calibration_sessions SET status='collecting',expires=?,rejections=0 WHERE id=?",(now+600,previous[0]))
     return {'status':'collecting','samples':count,'required_samples':required,'resumed':True}
    db.execute("UPDATE owner_calibration_sessions SET status='cancelled' WHERE device=? AND status='collecting'",(self.satellite,))
    db.execute('INSERT INTO owner_calibration_requests VALUES (?,?)',(key,now+600))
    db.execute('INSERT INTO owner_calibration_sessions (id,voice_id,device,created,expires,status,mode) VALUES (?,?,?,?,?,?,?)',(key,row[0],self.satellite,now,now+600,'collecting','repair' if request['action']=='repair' else 'calibration'))
    db.execute('DELETE FROM owner_calibration_sessions WHERE rowid NOT IN (SELECT rowid FROM owner_calibration_sessions ORDER BY rowid DESC LIMIT 8)')
    db.execute('DELETE FROM owner_calibration_samples WHERE session NOT IN (SELECT id FROM owner_calibration_sessions)')
    db.execute('DELETE FROM owner_calibration_windows WHERE session NOT IN (SELECT id FROM owner_calibration_sessions)')
   return {'status':'collecting','samples':0,'required_samples':2 if request['action']=='repair' else 5}
  except (OSError,ValueError,TypeError):return {'status':'rejected'}
 def active(self,db):
  row=db.execute('SELECT id,voice_id,expires,status,mode FROM owner_calibration_sessions WHERE device=? ORDER BY rowid DESC LIMIT 1',(self.satellite,)).fetchone()
  if row and row[3]=='collecting':
   if not db.execute('SELECT 1 FROM voices v JOIN voice_authorizations a ON a.voice_id=v.voice_id WHERE v.voice_id=?',(row[1],)).fetchone() or not 0<=row[2]-self.profiles.clock()<=600:
    db.execute("UPDATE owner_calibration_sessions SET status='expired' WHERE id=?",(row[0],));row=(*row[:3],'expired',row[4])
  return row
 def summary(self):
  with self.db() as db:
   row=self.active(db)
   if not row:return {'status':'idle','samples':0,'required_samples':5,'live_profile_changed':False}
   sample_rows=db.execute('SELECT vector,diagnostic FROM owner_calibration_samples WHERE session=? ORDER BY rowid',(row[0],)).fetchall()
   required=2 if row[4]=='repair' else 5
   count=len(sample_rows);vectors=[json.loads(x[0]) for x in sample_rows]
   consistency=min((similarity(a,b) for i,a in enumerate(vectors) for b in vectors[i+1:]),default=None)
   return {'whole_scores':[json.loads(x[1])['whole']['best_score'] for x in sample_rows],
           'within_sample_min_similarity':round(consistency,4) if consistency is not None else None,'status':row[3],'samples':count,'required_samples':required,'mode':row[4],'expires_in_s':max(0,round(row[2]-self.profiles.clock())),
           'classification':'owner_supplied_unreviewed','live_profile_changed':False,'raw_audio_saved':False}
 def collect(self,device,item):
  if device!=self.satellite:return None
  with self.db() as db:
   db.execute('BEGIN IMMEDIATE');row=self.active(db)
   if not row or row[3]!='collecting':return None
   required=2 if row[4]=='repair' else 5
   count=db.execute('SELECT count(*) FROM owner_calibration_samples WHERE session=?',(row[0],)).fetchone()[0]
   data=item.get('result') or {};quality=data.get('quality') or {}
   clean=(data.get('status')=='ok' and data.get('model')==MODEL_ID and item.get('voiced',0)>=3
          and item.get('playback') is False and quality.get('status')=='ok'
          and quality.get('rms',0)>=.004 and quality.get('clipped_fraction',1)<=.02)
   if row[4]=='repair':clean=clean and item.get('voiced',0)>=6 and isinstance(data.get('windows'),list) and len(data['windows'])==2
   if not clean:
    db.execute('UPDATE owner_calibration_sessions SET rejections=rejections+1 WHERE id=?',(row[0],))
    failures=db.execute('SELECT rejections FROM owner_calibration_sessions WHERE id=?',(row[0],)).fetchone()[0]
    if failures>=3:db.execute("UPDATE owner_calibration_sessions SET status='paused' WHERE id=?",(row[0],))
    reply=(f'Kalibrace: mám {count} z {required} ukázek. Tuhle jsem nepřidala. Potřebuji šest až deset sekund čisté řeči s vypnutou televizí a bez dalšího mluvčího.' if failures<3 else 'Kalibraci jsem po třech odmítnutých ukázkách pozastavila. Další věty neopakuj, je potřeba zkontrolovat diagnostiku.')
    return {'status':'owner_calibration','calibration':True,'authorized':False,'samples':count,'retry_recommended':failures<3,'local_reply':reply}
   try:
    v=unit(data['vector']);windows=[unit(w) for w in data.get('windows',[])] if row[4]=='repair' else []
    if windows and (any(len(w)!=len(v) for w in windows) or similarity(*windows)<.55 or any(similarity(v,w)<.55 for w in windows)):raise ValueError('invalid_windows')
   except (ValueError,TypeError,KeyError):return {'status':'owner_calibration','calibration':True,'authorized':False,'samples':count,'retry_recommended':False,'local_reply':'Ukázku se nepodařilo zpracovat. Kalibraci je potřeba zkontrolovat.'}
   utterance=item.get('utterance')
   if not isinstance(utterance,str) or not utterance:return {'status':'owner_calibration','calibration':True,'authorized':False,'samples':count,'retry_recommended':False,'local_reply':'Chybí označení ukázky. Kalibraci je potřeba zkontrolovat.'}
   scores=sorted(((profile_score(v,json.loads(x[0]),x[1]),profile_threshold(x[1])) for x in db.execute("SELECT v.samples,COALESCE(p.policy,'centroid') FROM voices v LEFT JOIN voice_matching_policies p ON p.voice_id=v.voice_id WHERE v.model=?",(MODEL_ID,))),reverse=True)
   diagnostic={'whole':{'best_score':round(scores[0][0],4) if scores else None,'threshold':scores[0][1] if scores else None},'classification':'owner_supplied_unreviewed'}
   cursor=db.execute('INSERT OR IGNORE INTO owner_calibration_samples VALUES (?,?,?,?)',(row[0],utterance,json.dumps(v),json.dumps(diagnostic)))
   if cursor.rowcount==1 and windows:db.execute('INSERT INTO owner_calibration_windows VALUES (?,?,?)',(row[0],utterance,json.dumps(windows)))
   count+=int(cursor.rowcount==1)
   if cursor.rowcount==1:db.execute('UPDATE owner_calibration_sessions SET expires=? WHERE id=?',(self.profiles.clock()+600,row[0]))
   if count>=required:db.execute("UPDATE owner_calibration_sessions SET status='awaiting_review' WHERE id=?",(row[0],))
   reply=f'Mám {count} z {required} kalibračních ukázek. '
   reply+=('Řekni prosím jinou větu dlouhou šest až deset sekund.' if count<required else 'Ukázky jsou uložené odděleně pro kontrolu. Původní otisk ani oprávnění jsem nezměnila.')
   return {'status':'owner_calibration','calibration':True,'authorized':False,'samples':count,'retry_recommended':count<required,'local_reply':reply}

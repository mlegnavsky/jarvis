"""Owner-started, persistent family enrollment; training never executes commands."""
import hashlib,json,re,sqlite3
from uuid import uuid4
if __package__:
 from .policy import MODEL_ID,COHORT_POLICY,unit,norm,similarity,cohort_evidence,profile_evidence
 from .family_questions import QUESTIONS
else:
 from policy import MODEL_ID,COHORT_POLICY,unit,norm,similarity,cohort_evidence,profile_evidence
 from family_questions import QUESTIONS

STARTS={'nauc se noveho clena rodiny','pridej noveho clena rodiny','prosim nauc se noveho clena rodiny a proved ho zaucenim'}
RESUMES={'pokracuj v zauceni clena rodiny','pokracuj v zauceni'}
CANCELS={'zrus zauceni','zrus uceni hlasu','zrus pridavani clena rodiny','koncime'}

class FamilyEnrollment:
 def __init__(self,profiles):self.profiles=profiles
 def db(self):
  db=self.profiles._db()
  db.execute('CREATE TABLE IF NOT EXISTS voice_family_enrollment(device TEXT PRIMARY KEY,owner_id TEXT,state TEXT,expires REAL)')
  db.commit();return db
 def _save(self,db,device,owner,state):
  db.execute('INSERT OR REPLACE INTO voice_family_enrollment VALUES (?,?,?,?)',(device,owner,json.dumps(state,ensure_ascii=False),self.profiles.clock()+86400))
 def start(self,device,owner,resume=False):
  with self.db() as db:
   db.execute('BEGIN IMMEDIATE')
   if not device or not db.execute('SELECT 1 FROM voice_authorizations a JOIN voices v ON v.voice_id=a.voice_id LEFT JOIN voice_control_scopes s ON s.voice_id=a.voice_id WHERE a.voice_id=? AND s.scope IS NULL',(owner,)).fetchone():raise ValueError('authorized_owner_required')
   if resume:
    row=db.execute('SELECT owner_id,state FROM voice_family_enrollment WHERE device=?',(device,)).fetchone()
    if not row or row[0]!=owner:raise ValueError('matching_owner_session_required')
    state=json.loads(row[1])
    if state['stage']=='done':raise ValueError('session_already_completed')
    state['paused']=False;state['rejections']=0
   else:state={'stage':'name','training':[],'validation':[],'used':[],'question':0,'attempts':0,'rejections':0,'paused':False}
   self._save(db,device,owner,state)
  return self.reply(state,'Jak se nový člen rodiny jmenuje? Potom ho provedu otázkami a kontrolními větami.' if not resume else 'Pokračujeme v uloženém zaučení. '+self.prompt(state))
 def interrupt(self,device,*,cancel=False):
  with self.db() as db:
   if cancel:db.execute('DELETE FROM voice_family_enrollment WHERE device=?',(device,));return
   row=db.execute('SELECT owner_id,state FROM voice_family_enrollment WHERE device=?',(device,)).fetchone()
   if row:
    state=json.loads(row[1])
    if state['stage']!='done':state['paused']=True;self._save(db,device,row[0],state)
 def process_control(self,path):
  if __package__:from .family_control import FamilyControl
  else:from family_control import FamilyControl
  return FamilyControl(self.profiles,path).process()
 def progress(self,state):
  if state.get('stage')=='done':return 100
  return min(95,round(min(len(state.get('training',[])),5)*12+min(len(state.get('validation',[])),3)*40/3))
 def reply(self,state,message,*,status='family_enrollment',retry=True):
  return {'status':status,'calibration':True,'authorized':False,'retry_recommended':retry,
          'progress_percent':self.progress(state),'local_reply':message}
 def prompt(self,state):return QUESTIONS[state.get('question',0)%len(QUESTIONS)][1]
 def summary(self):
  with self.db() as db:
   db.execute('DELETE FROM voice_family_enrollment WHERE owner_id NOT IN (SELECT voice_id FROM voices)')
   row=db.execute('SELECT state,expires FROM voice_family_enrollment ORDER BY rowid DESC LIMIT 1').fetchone()
   approvals=[{'name':label,'revision':revision,'lights_authorized':authorized is not None and scope=='lights'} for label,revision,authorized,scope in db.execute('SELECT v.label,f.revision,a.voice_id,s.scope FROM voice_family_validations f JOIN voices v ON v.voice_id=f.voice_id LEFT JOIN voice_authorizations a ON a.voice_id=v.voice_id LEFT JOIN voice_control_scopes s ON s.voice_id=v.voice_id')]
   if not row:return {'status':'idle','raw_audio_saved':False,'approvals':approvals}
   s=json.loads(row[0]);paused=s.get('paused') or row[1]<self.profiles.clock()
   return {'status':'completed' if s['stage']=='done' else 'paused' if paused else 'active','stage':s['stage'],
           'progress_percent':self.progress(s),'training_samples':len(s.get('training',[])),'validation_samples':len(s.get('validation',[])),
           'validated_profile_revision':s.get('validated_profile_revision'),'progress_is_identity_probability':False,'raw_audio_saved':False,'automatic_authorization':False,'approvals':approvals}
 def _negatives(self,db):
  pools=[]
  for source,samples,policy in db.execute("SELECT v.voice_id,v.samples,COALESCE(p.policy,'centroid') FROM voices v LEFT JOIN voice_matching_policies p ON p.voice_id=v.voice_id WHERE model=?",(MODEL_ID,)):
   data=json.loads(samples);pools.append((source,[unit(v) for v in (data['positive'] if policy==COHORT_POLICY else data)]))
  result=[];sources=[]
  for i in range(max((len(v) for source,v in pools),default=0)):
   for source,pool in pools:
    if i<len(pool) and len(result)<16:result.append(pool[i]);sources.append(source)
  if len(result)<3:raise ValueError('reference_cohort_missing')
  return result,sources
 def _bank(self,db,state):
  negative,sources=self._negatives(db)
  return {'positive':[v for s in state['training'] for v in [s['vector'],*s['windows']]],'negative':negative,'negative_sources':sources}
 def _valid(self,sample,bank,db):
  if __package__:from .family_control import validate_holdout
  else:from family_control import validate_holdout
  return validate_holdout(db,sample,bank)
 def collect(self,device,text,item):
  value=re.sub(r'^anicko\s+','',norm(text))
  if value in STARTS|RESUMES:return None
  try:
   with self.db() as db:
    db.execute('BEGIN IMMEDIATE')
    row=db.execute('SELECT owner_id,state,expires FROM voice_family_enrollment WHERE device=?',(device,)).fetchone()
    if not row:return None
    owner,state,expires=row[0],json.loads(row[1]),row[2]
    if state['stage']=='done':return None
    if value in CANCELS:
     db.execute('DELETE FROM voice_family_enrollment WHERE device=?',(device,))
     return self.reply(state,'Zaučení jsem zrušila. Žádný nový hlasový profil jsem neuložila.',retry=False)
    if state.get('paused') or expires<self.profiles.clock():
     state['paused']=True;self._save(db,device,owner,state)
     return self.reply(state,'Rozpracované zaučení je zachované. Martin ho může obnovit větou: Pokračuj v zaučení.',retry=False)
    if not db.execute('SELECT 1 FROM voice_authorizations a JOIN voices v ON v.voice_id=a.voice_id LEFT JOIN voice_control_scopes s ON s.voice_id=a.voice_id WHERE a.voice_id=? AND s.scope IS NULL',(owner,)).fetchone():
     db.execute('DELETE FROM voice_family_enrollment WHERE device=?',(device,));return None
    if state['stage']=='name':
     label=re.sub(r'^(?:jmenuji se|jsem|jmeno je)\s+','',value).strip().title()
     label={'Sarlota':'Šarlota','Sarlotka':'Šarlotka'}.get(label,label)
     if (not re.fullmatch(r'[^\W\d_][^\W\d_ -]*(?:[ -][^\W\d_]+){0,2}',label,re.UNICODE) or len(label)>40 or
         db.execute('SELECT 1 FROM voices WHERE name=?',(norm(label),)).fetchone()):
      return self.reply(state,'Tohle jméno nemohu použít nebo už má uložený profil. Jak se nový člen rodiny jmenuje?')
     state.update(name=norm(label),label=label,stage='consent');self._save(db,device,owner,state)
     return self.reply(state,'Slyšela jsem jméno '+label+'. Je to správně a souhlasíš se zapamatováním hlasu pro rozpoznávání doma?')
    if state['stage']=='consent':
     if value.startswith('ne'):
      db.execute('DELETE FROM voice_family_enrollment WHERE device=?',(device,));return self.reply(state,'Dobře, hlas ukládat nebudu.',retry=False)
     if not (value.startswith('ano') or value in ('souhlasim','jo')):return self.reply(state,'Potřebuji odpověď ano, nebo ne.')
     state['stage']='training';self._save(db,device,owner,state)
     return self.reply(state,'Začínáme zaučení. Procenta ukazují postup zkoušek, ne jistotu totožnosti. Žádný tréninkový povel neprovedu. '+self.prompt(state))
    data=item.get('result') or {};q=data.get('quality') or {};state['attempts']+=1
    key=item.get('utterance');text_key=hashlib.sha256(value.encode()).hexdigest()
    clean=(data.get('status')=='ok' and data.get('model')==MODEL_ID and item.get('voiced',0)>=3 and item.get('playback') is False
           and q.get('status')=='ok' and q.get('rms',0)>=.004 and q.get('clipped_fraction',1)<=.02 and isinstance(key,str) and key and key not in state['used'] and text_key not in state['used'])
    sample=None
    if clean:
     v=unit(data['vector']);windows=[unit(w) for w in data.get('windows',[])]
     if len(windows)>2 or any(len(w)!=len(v) for w in windows):raise ValueError('invalid_windows')
     sample={'vector':v,'windows':windows}
     previous=sorted((similarity(v,s['vector']) for s in state['training']),reverse=True)
     clean=not previous or previous[0]>=.5 and (len(previous)<2 or previous[1]>=.45)
    if not clean:
     state['rejections']+=1;state['question']+=1
     if state['rejections']>=3 or state['attempts']>=24:state['paused']=True
     self._save(db,device,owner,state)
     return self.reply(state,'Tuhle odpověď jsem do zaučení nepřidala. Postup je '+str(self.progress(state))+' procent. '+('Rozpracované údaje jsou zachované, je potřeba zkontrolovat kvalitu rozpoznávání.' if state['paused'] else 'Odpověz prosím jinou celou větou alespoň tři sekundy dlouhou. '+self.prompt(state)),retry=not state['paused'])
    state['used'].extend((key,text_key));state['rejections']=0
    if state['stage']=='training':
     state['training'].append(sample)
     if len(state['training'])>=5:state['stage']='validation';state['question']=5
     else:state['question']+=1
    else:
     bank=self._bank(db,state)
     if self._valid(sample,bank,db):state['validation'].append(sample)
     else:
      state['validation']=[]
      # Learn a variation only when its whole voice already passes; never
      # treat this utterance as a holdout again after adding it to training.
      if cohort_evidence(sample['vector'],bank)['accepted'] and len(state['training'])<8:state['training'].append(sample)
     state['question']+=1
    complete=len(state['validation'])>=3 and sum(len(s['windows']) for s in state['validation'])>=2
    if complete:
     bank=self._bank(db,state)
     if all(self._valid(s,bank,db) for s in state['validation']):
      if db.execute('SELECT 1 FROM voices WHERE name=?',(state['name'],)).fetchone() or db.execute('SELECT count(*) FROM voices').fetchone()[0]>=16:raise ValueError('profile_exists_or_full')
      voice_id=uuid4().hex;now=self.profiles.clock()
      db.execute('INSERT INTO voices VALUES (?,?,?,?,?,?)',(state['name'],state['label'],MODEL_ID,json.dumps(bank),now,voice_id))
      db.execute('INSERT INTO voice_anchors VALUES (?,?)',(voice_id,json.dumps(bank['positive'])))
      db.execute('INSERT INTO voice_matching_policies VALUES (?,?)',(voice_id,COHORT_POLICY))
      if __package__:from .family_control import permission_revision
      else:from family_control import permission_revision
      revision=permission_revision(voice_id,bank,COHORT_POLICY,owner)
      report={'training_utterances':len(state['training']),'validation_utterances':len(state['validation']),'validation_windows':sum(len(s['windows']) for s in state['validation']),'holdouts':state['validation']}
      db.execute('INSERT INTO voice_family_validations VALUES (?,?,?,?)',(voice_id,owner,revision,json.dumps(report)))
      state={'stage':'done','label':state['label'],'paused':False,'validated_profile_revision':revision};self._save(db,device,owner,state)
      return self.reply(state,'Zaučení je dokončené na sto procent. Hlas prošel kontrolními větami. Oprávnění k ovládání domu musí Martin potvrdit zvlášť.',status='family_enrolled',retry=False)
     state['validation']=[]
    if state['attempts']>=24:state['paused']=True
    self._save(db,device,owner,state)
    return self.reply(state,'Postup zaučení je '+str(self.progress(state))+' procent. '+('Rozpracované zaučení jsem zachovala. Další odpovědi teď neopakuj, je potřeba zkontrolovat výsledky.' if state['paused'] else self.prompt(state)),retry=not state['paused'])
  except (ValueError,TypeError,KeyError,sqlite3.Error):
   return {'status':'family_enrollment_error','calibration':True,'authorized':False,'retry_recommended':False,'progress_percent':0,'local_reply':'Zaučení vyžaduje kontrolu. Žádný nový profil ani oprávnění jsem nevytvořila.'}

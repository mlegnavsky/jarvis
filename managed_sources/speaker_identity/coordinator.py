"""One-shot active-turn audio results and explicit enrollment conversation."""
import re
import copy
from datetime import datetime,timezone
import time
import hashlib
import asyncio
if __package__:
 from .policy import VoiceProfiles,MODEL_ID,norm
 from .authorization import VoiceGate,command,canonical_command
 from .adaptation import Adaptation
 from .pronunciation import Pronunciation
 from .owner_calibration import OwnerCalibration
 from .family_enrollment import FamilyEnrollment,STARTS,RESUMES
 from .familiar import FamiliarVoices
else:
 from policy import VoiceProfiles,MODEL_ID,norm
 from authorization import VoiceGate,command,canonical_command
 from adaptation import Adaptation
 from pronunciation import Pronunciation
 from owner_calibration import OwnerCalibration
 from family_enrollment import FamilyEnrollment,STARTS,RESUMES
 from familiar import FamiliarVoices

async def admin_forget(hass,user_id,name,coordinator,clear_memory):
 account=await hass.auth.async_get_user(user_id) if user_id else None
 if not account or not account.is_admin or not account.is_active or account.is_system_generated:raise PermissionError('administrator_required')
 memory_id=await hass.async_add_executor_job(coordinator.profiles.forget,name)
 await hass.async_add_executor_job(coordinator.familiar.forget,name)
 if memory_id and clear_memory:await hass.async_add_executor_job(clear_memory,memory_id)

class Coordinator:
 def __init__(self,hass,path,infer,clock=time.monotonic,*,enforce=False,calibration_satellite=None,public_controls=False):
  self.hass=hass;self.profiles=VoiceProfiles(path);self.infer=infer;self.clock=clock
  self.results={};self.aliases={};self.asked={};self.last={};self.capture_count=0;self.recent_turns=[];self.status='starting'
  self.enforce=enforce;self.public_controls=public_controls;self.gate=VoiceGate(clock=clock,challenge_words=('javor','kolo','most','reka','hora','okno','zahrada','strom'));self.adaptation=Adaptation(self.profiles)
  self.pronunciation=Pronunciation(self.profiles);self.calibration={};self.failures={}
  self.family=FamilyEnrollment(self.profiles)
  self.familiar=FamiliarVoices(self.profiles);self.learning_tasks=set();self.address_ticks={}
  self.owner_calibration=OwnerCalibration(self.profiles,calibration_satellite) if calibration_satellite else None
 def device(self,user):return getattr(user,'satellite_id',None) or self.aliases.get(user.device_id,user.device_id)
 def cancel_for(self,user):
  device=getattr(user,'satellite_id',None) or self.aliases.get(user.device_id,user.device_id)
  self.results.pop(device,None);self.profiles.cancel(device)
  self.gate.cancel(device)
  self.family.interrupt(device,cancel=norm(getattr(user,'text','')) in {'koncime','konec','stop','staci','dekuji konec','diky konec','uz koncime','to je vse','to je vsechno','to je vsechno dekuji','ukonci rozhovor','prestan poslouchat','dobrou noc','zrus zauceni','zrus pridavani clena rodiny'})
 def enrollment_state(self):
  now=self.profiles.clock()
  return [{'samples':len(slot['samples']),'required_samples':3,
           'expires_in_s':max(0,round(300-(now-slot['at'])))}
          for slot in list(self.profiles.pending.values()) if 0<=now-slot['at']<=300]
 async def complete(self,device,pcm,voiced,text,*,playback=False,context_id=None):
  self.capture_count+=1;capture_number=self.capture_count;start=self.clock()
  result={'status':'too_short'}
  public_light=self.public_controls and (command(text) or (None,))[0]=='light'
  training=self.family.summary()['status']!='idle' or bool(self.owner_calibration and self.owner_calibration.summary().get('status')=='collecting')
  deferred=public_light and not training
  if deferred:result={'status':'identity_optional_deferred'}
  elif voiced>=2.5:
   try:result=await self.infer(pcm)
   except Exception as exc:result={'status':'unavailable','error':type(exc).__name__}
  self.results[device]={'at':self.clock(),'text':norm(text),'voiced':voiced,'result':result,'playback':playback,
                        'utterance':hashlib.sha256(pcm).hexdigest(),'context_id':context_id,'capture_number':capture_number}
  while len(self.results)>4:self.results.pop(next(iter(self.results)))
  summary={'status':result.get('status','unavailable'),'audio_seconds':round(len(pcm)/32000,2),
           'voiced_seconds':round(voiced,2),'inference_ms':round((self.clock()-start)*1000,1),'capture_number':capture_number}
  self.results[device]['summary']=summary
  if deferred and voiced>=3 and playback is False:self.results[device]['learning_pcm']=pcm
  if capture_number>=self.last.get('capture_number',0):self.last=dict(summary)
 async def learn_later(self,item,conversation):
  pcm=item.pop('learning_pcm',None)
  if not pcm:return
  try:
   result=await self.infer(pcm)
   # Known protected profiles remain immutable; only anonymous familiarity is learned.
   def collect():
    if result.get('status')!='ok' or result.get('model')!=MODEL_ID:return
    if self.profiles.identify(result.get('vector'))['status']=='recognized':return
    self.familiar.observe({**item,'result':result},conversation)
   await self.hass.async_add_executor_job(collect)
  except asyncio.CancelledError:raise
  except Exception:pass
 async def turn(self,user,conversation):
  device=getattr(user,'satellite_id',None) or self.aliases.get(user.device_id,user.device_id)
  item=self.results.pop(device,None)
  if not item or not 0<=self.clock()-item['at']<=15 or norm(user.text)!=item['text']:return None
  if item.get('context_id') is not None and item['context_id']!=getattr(getattr(user,'context',None),'id',None):return None
  decision=await self.hass.async_add_executor_job(self._turn_sync,device,str(conversation),user.text,item)
  authorized=decision.get('authorized',False)
  # Keep bounded numeric evidence before follow-up capture replaces last.
  # Never retain transcript, waveform, embedding, identity or execution token.
  evidence=dict(item['summary'])
  if 'matching' in item:evidence['matching']=copy.deepcopy(item['matching'])
  evidence.update(capture_number=item['capture_number'],completed_at=datetime.now(timezone.utc).isoformat(),
                  decision_status=decision.get('status'),authorized=authorized)
  self.recent_turns.append(evidence)
  del self.recent_turns[:-16]
  if authorized and not decision.get('calibration'):
   effective=decision.get('effective_text',user.text)
   decision['control_token']=self.gate.issue(device,effective,decision.get('memory_id'),True)
   if decision.get('status')=='recognized':self.last['adaptation']=await self.hass.async_add_executor_job(self.adaptation.offer,decision['memory_id'],
    {'vector':item['result'].get('vector'),'windows':item['result'].get('windows',[]),'quality':item['result'].get('quality'),
     'seconds':item['voiced'],'playback':item['playback'],'conversation':str(conversation),'utterance':item['utterance'],'replay_live':False})
  if self.last.get('capture_number')==item['capture_number']:
   self.last.update(decision_status=decision.get('status'),accepted_samples=decision.get('samples'))
   if 'matching' in item:self.last['matching']=copy.deepcopy(item['matching'])
  if decision.get('status')=='public_command' and 'learning_pcm' in item and len(self.learning_tasks)<2:
   task=asyncio.create_task(self.learn_later(item,str(conversation)))
   self.learning_tasks.add(task);task.add_done_callback(self.learning_tasks.discard)
  return decision
 def _turn_sync(self,device,conversation,text,item):
  family_value=re.sub(r'^anicko\s+','',norm(text))
  family=self.family.collect(device,text,item)
  if family is not None:
   self.gate.cancel(device);return family
  if self.owner_calibration and family_value not in STARTS|RESUMES:
   collected=self.owner_calibration.collect(device,item)
   if collected is not None:
    self.gate.cancel(device)
    return collected
  action=command(text)
  if self.public_controls and action and action[0]=='light':
   self.gate.cancel(device)
   return {'status':'public_command','authorized':True,'memory_id':'public_household',
           'effective_text':canonical_command(text),'request_introduction':False}
  data=item['result'];value=norm(text)
  good=data.get('status')=='ok' and data.get('model')==MODEL_ID
  vector=data.get('vector') if good else None
  identity=self.profiles.identify(vector) if vector else {'status':data.get('status','unknown')}
  diagnostic={'whole':{'status':identity['status']},'windows':[]};window_scores=[]
  if vector:diagnostic['whole'].update(self.profiles.match_diagnostics(vector))
  if identity.get('status')=='recognized':
   inconsistent=False
   for window in data.get('windows',[]):
    match=self.profiles.identify(window,window=True);window_scores.append(match.get('score',-1))
    diagnostic['windows'].append({'status':match['status'],**self.profiles.match_diagnostics(window,window=True)})
    if match.get('profile')!=identity['profile']:inconsistent=True
   if inconsistent:identity={'status':'uncertain_windows'}
  item['matching']=diagnostic
  strong=identity.get('status')=='recognized' and identity.get('score',0)>=.75 and all(x>=.75 for x in window_scores)
  if value=='smaz muj hlasovy profil' and not strong:identity={'status':'strict_identity_required'}
  authorized=bool(identity.get('status')=='recognized' and self.profiles.is_authorized(identity.get('memory_id')))
  if authorized:self.failures.pop(device,None)
  if family_value in STARTS|RESUMES:
   if authorized:
    self.gate.cancel(device);self.profiles.cancel(device)
    try:return self.family.start(device,identity['memory_id'],resume=family_value in RESUMES)
    except ValueError:return {'status':'family_enrollment_error','calibration':True,'authorized':False,'retry_recommended':False,'local_reply':'Toto zaučení nemohu založit nebo obnovit.'}
   if data.get('status')=='too_short':return {'status':'family_owner_confirmation_required','authorized':False,'retry_recommended':True,'local_reply':'Pro spuštění potřebuji ověřit hlas správce. Řekni prosím celou větu: Aničko, prosím nauč se nového člena rodiny a proveď ho zaučením.'}
  management=bool(re.match(r'^(nauc se|vylepsi|smaz|potvrzuji slovo|zapomen.*hlas)',family_value)) or family_value in STARTS|RESUMES
  if self.public_controls and not authorized and not management and not (action and action[0]=='lock'):
   personalization={}
   if identity.get('status')=='recognized':
    key=identity['memory_id'];tick=self.address_ticks.get(key,0);self.address_ticks[key]=tick+1
    while len(self.address_ticks)>64:self.address_ticks.pop(next(iter(self.address_ticks)))
    if tick%6==0:personalization['familiar_address']=identity['name']
    return {'status':'personalization_only','authorized':False,'request_introduction':False,**personalization}
   try:
    if identity.get('status')!='recognized':
     match=self.familiar.observe(item,conversation)
     personalization=self.familiar.dialog(device,text,match,allow_ask=not bool(action))
   except Exception:pass
   return {**identity,'authorized':False,'request_introduction':False,**personalization}
  if self.enforce and identity.get('status')=='recognized' and not authorized:
   return {**identity,'authorized':False,'retry_recommended':False,'local_reply':'Poznávám tě jako '+identity['name']+'. Povel zatím neprovedu. Oprávnění k ovládání domu ještě musí potvrdit Martin.'}
  if self.enforce and not authorized:
   prior=self.failures.pop(device,None)
   failures=(prior['count'] if prior and 0<=self.clock()-prior['at']<=300 else 0)+1
   self.failures[device]={'count':failures,'at':self.clock()}
   while len(self.failures)>4:self.failures.pop(next(iter(self.failures)))
   if data.get('status')=='too_short' and norm(text) in ('zhasni','rozsvit','zamkni','odemkni'):
    challenge=self.gate.pending(device,text)
    phrases={'zhasni':'Potvrzuji zhasnutí světel v této místnosti.', 'rozsvit':'Potvrzuji rozsvícení světel v této místnosti.',
             'zamkni':'Potvrzuji zamknutí hlavního vchodu.', 'odemkni':'Potvrzuji odemknutí hlavního vchodu.'}
    reply='Krátké slovo nestačí k ověření hlasu. Po této odpovědi řekni: '+phrases[norm(text)].rstrip('.')+(' '+challenge if challenge else '')+'.'
   else:
    self.gate.cancel(device)
    reasons={'uncertain_windows':'Celá věta odpovídá profilu, ale její části nepotvrdily stejný hlas. Ztiš prosím okolní zvuk.',
             'too_short':'Pro ověření potřebuji alespoň tři sekundy souvislé řeči.',
             'quiet':'Nahrávka je příliš tichá. Přibliž se prosím k mikrofonu.',
             'clipped':'Zvuk je přebuzený. Mluv prosím přirozeně a trochu dál od mikrofonu.',
             'inconsistent':'Části nahrávky se příliš liší. Ztiš prosím televizi a ostatní hlasy.',
             'unavailable':'Služba ověřování hlasu není dostupná. Opakování věty teď nepomůže.'}
    reply='Hlas nemám ověřený, povel neprovedu. '+reasons.get(identity.get('status'),'Hlas se dost jistě neshoduje s uloženým profilem.')
   retry=failures<3 and identity.get('status')!='unavailable'
   if not retry:
    self.gate.cancel(device)
    reply='Hlas se nepodařilo ověřit. Povel neprovedu. Další věty teď neopakuj, je potřeba zkontrolovat diagnostiku.'
   self.last['verification_failures']=failures
   return {'status':identity.get('status','unknown'),'authorized':False,'local_reply':reply,'retry_recommended':retry}
  confirmed=self.gate.confirm(device,text,authorized)
  if authorized:
   identity={**identity,'authorized':True}
   if confirmed:identity['effective_text']=confirmed
   elif command(text):identity['effective_text']=canonical_command(text)
   alias=self.pronunciation.resolve(identity['memory_id'],value)
   if alias!=value:identity['effective_text']=alias
   proposal=re.fullmatch(r'nauc se slovo (\w+) znamena (\w+)',value)
   confirmation=re.fullmatch(r'potvrzuji slovo (\w+) znamena (\w+)',value)
   if proposal or confirmation:
    match=proposal or confirmation
    try:
     if proposal:self.pronunciation.propose(identity['memory_id'],match[1],match[2])
     else:self.pronunciation.confirm(identity['memory_id'],match[1],match[2])
     return {**identity,'calibration':True,'local_reply':('Potvrď prosím celou větou: Potvrzuji slovo '+match[1]+' znamená '+match[2]+'.') if proposal else 'Výslovnost jsem uložila k tvému ověřenému profilu.'}
    except ValueError:return {**identity,'calibration':True,'local_reply':'Tuto změnu výslovnosti nemohu potvrdit.'}
   slot=self.calibration.get(device)
   if slot and not 0<=self.clock()-slot['at']<=300:self.calibration.pop(device,None);slot=None
   if slot and slot['voice_id']==identity['memory_id']:
    q=data.get('quality') or {}
    if item['voiced']<3 or q.get('status')!='ok' or item['playback'] is not False:
     return {**identity,'calibration':True,'local_reply':'Pro ověřovací ukázku potřebuji delší čistou větu bez televize.'}
    try:self.adaptation.add_validation(identity['memory_id'],item['utterance'],vector,True)
    except Exception:
     return {**identity,'calibration':True,'local_reply':'Tuhle ukázku jsem nepřidala. Řekni prosím jinou větu.'}
    slot['count']+=1
    if slot['count']>=5:self.calibration.pop(device,None)
    return {**identity,'calibration':True,'local_reply':f"Mám {slot['count']} z pěti nezávislých ověřovacích ukázek. "+('Řekni prosím další jinou větu.' if slot['count']<5 else 'Původní otisk zůstává zachovaný. Pro zapnutí změn ještě potřebuji ověření proti cizím hlasům a přehrávce.')}
  if value in {'uz mas otisk meho hlasu','uz odtisk meho hlasu','uz znas muj hlas','poznavas muj hlas','mas ulozeny muj hlas'}:
   if device in self.profiles.pending:
    slot=self.profiles.pending[device]
    if 0<=self.profiles.clock()-slot['at']<=300:
     count=len(slot['samples'])
     return {'status':'enrolling','samples':count,'local_reply':f'Učení běží. Mám {count} ze tří ukázek. Profil ještě není uložený.'}
   if self.profiles.count()==0:
    return {'status':'not_enrolled','local_reply':'Zatím nemám uložený žádný hlasový profil. Učení ještě není dokončené.'}
   return {**identity,'local_reply':'Tvůj hlas odpovídá uloženému profilu.' if identity.get('status')=='recognized' else 'Tvůj hlas teď nedokážu jistě přiřadit k uloženému profilu.'}
  if value in {'zrus uceni hlasu','zrus uceni meho hlasu','zrus registraci hlasu'}:
   self.profiles.cancel(device);return {'status':'cancelled','local_reply':'Učení hlasu jsem zrušil.'}
  if value=='smaz muj hlasovy profil':
   if identity.get('status')=='recognized':
    self.profiles.forget(identity['profile'])
    return {'status':'deleted','deleted_profile':identity['profile'],'deleted_memory_id':identity['memory_id'],'local_reply':'Smazal jsem tvůj hlasový profil i jeho konverzační paměť.'}
   return {'status':'unknown','local_reply':'Tvůj hlas teď nerozpoznávám dost jistě. Profil proto nemažu.'}
  if value=='vylepsi muj hlasovy profil':
   if authorized:self.calibration[device]={'voice_id':identity['memory_id'],'at':self.clock(),'count':0}
   improved=bool(vector and identity.get('profile') and self.profiles.improve(identity['profile'],vector,item['voiced']))
   return {**identity,'calibration':True,'local_reply':'Původní otisk zachovám. Řekni postupně pět různých vět, každou pět až osm sekund dlouhou. Uložím je zvlášť jako ověřovací ukázky.'}
  enrollment=re.fullmatch(r'(?:nauc se|zapamatuj si) muj hlas (?:jsem|jmenuji se) (.+)',value)
  if value in {'nauc se muj hlas','zapamatuj si muj hlas'}:
   return {'status':'name_required','local_reply':'Řekni prosím celý povel se svým jménem, například: Nauč se můj hlas. Jsem Martin.'}
  if enrollment:
   names={'martin':'Martin','sarlota':'Šarlota','iris':'Iris','petr':'Petr','dana':'Dana'}
   name=names.get(enrollment[1],enrollment[1].title())
   result=self.profiles.begin(device,name)
   if result['status']=='exists':return {'status':'exists','local_reply':'Profil tohoto jména už existuje. Bez jeho rozpoznání ho nepřepíšu.'}
   if result['status']!='enrolling':return {'status':result['status'],'local_reply':'Tento hlasový profil se mi nepodařilo založit.'}
   return {'status':'enrolling','samples':0,'local_reply':'Začínáme. Potřebuji tři ukázky tvého hlasu, každou pět až osm sekund dlouhou. Zatím nemám žádnou. Řekni první větu.'}
  if device in self.profiles.pending:
   slot=self.profiles.pending[device]
   if not 0<=self.profiles.clock()-slot['at']<=300:self.profiles.cancel(device)
   else:
    result=self.profiles.sample(device,vector,item['voiced']) if vector else {'status':'too_short'}
    status=result['status']
    if status=='enrolled':return {**result,'local_reply':'Hotovo, hlasový profil '+result['name']+' je uložený. Příště ho porovnám s tvým hlasem; při nejistotě se raději zeptám.'}
    if status=='enrolling':return {**result,'local_reply':f"Mám {result['samples']} ze tří ukázek. Řekni prosím jinou větu alespoň tři sekundy dlouhou. Co jsi dnes dělal?"}
    if status=='inconsistent':return {**result,'local_reply':f"Tahle ukázka se od předchozích příliš liší, proto ji nepřidám. Přijaté ukázky jsem zachovala, mám {result['samples']} ze tří. Ztiš prosím okolní zvuk a řekni jinou větu, pět až osm sekund dlouhou."}
    return {'status':status,'local_reply':'Tuhle ukázku nepřidám. Potřebuji delší čistou větu bez dalšího mluvčího. Zkusíš ještě jednu?'}
  introduction=re.fullmatch(r'(?:jsem|tady je|jmenuji se) (.+)',value)
  if introduction and identity.get('profile') and norm(introduction[1])!=identity['profile']:
   return {'status':'identity_conflict','request_introduction':False}
  if identity.get('status')=='recognized':
   action=command(identity.get('effective_text',text))
   if action and not self.profiles.can_control(identity['memory_id'],action[0]):
    self.gate.cancel(device)
    return {'status':'voice_scope_required','authorized':False,'retry_recommended':False,'local_reply':'Pro tento povel nemáš nastavené oprávnění. Povel neprovedu.'}
   if action and action[0]=='lock' and not strong:
    self.gate.cancel(device)
    return {'status':'strict_lock_identity_required','authorized':False,'retry_recommended':False,'local_reply':'Pro ovládání zámku potřebuji silnější ověření hlasu. Tento povel teď neprovedu.'}
   self.last.update(status='recognized',profile=identity['profile'],score=identity['score'])
   if self.public_controls:
    key=identity['memory_id'];tick=self.address_ticks.get(key,0);self.address_ticks[key]=tick+1
    while len(self.address_ticks)>64:self.address_ticks.pop(next(iter(self.address_ticks)))
    identity['address_allowed']=tick%6==0
   return identity
  direct=bool(re.match(r'(kolik|zapni|vypni|zhasni|nastav|odemkni|zamkni)\b',value))
  ask=bool(not direct and conversation not in self.asked)
  if ask:self.asked[conversation]=True
  while len(self.asked)>32:self.asked.pop(next(iter(self.asked)))
  return {**identity,'request_introduction':ask}



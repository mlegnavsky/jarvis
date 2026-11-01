"""One-shot active-turn audio results and explicit enrollment conversation."""
import re
import time
import hashlib
if __package__:
 from .policy import VoiceProfiles,MODEL_ID,norm
 from .authorization import VoiceGate,command
 from .adaptation import Adaptation
 from .pronunciation import Pronunciation
else:
 from policy import VoiceProfiles,MODEL_ID,norm
 from authorization import VoiceGate,command
 from adaptation import Adaptation
 from pronunciation import Pronunciation

async def admin_forget(hass,user_id,name,coordinator,clear_memory):
 account=await hass.auth.async_get_user(user_id) if user_id else None
 if not account or not account.is_admin or not account.is_active or account.is_system_generated:raise PermissionError('administrator_required')
 memory_id=await hass.async_add_executor_job(coordinator.profiles.forget,name)
 if memory_id and clear_memory:await hass.async_add_executor_job(clear_memory,memory_id)

class Coordinator:
 def __init__(self,hass,path,infer,clock=time.monotonic,*,enforce=False):
  self.hass=hass;self.profiles=VoiceProfiles(path);self.infer=infer;self.clock=clock
  self.results={};self.aliases={};self.asked={};self.last={};self.capture_count=0;self.status='starting'
  self.enforce=enforce;self.gate=VoiceGate(clock=clock,challenge_words=('javor','kolo','most','reka','hora','okno','zahrada','strom'));self.adaptation=Adaptation(self.profiles)
  self.pronunciation=Pronunciation(self.profiles);self.calibration={}
 def device(self,user):return getattr(user,'satellite_id',None) or self.aliases.get(user.device_id,user.device_id)
 def cancel_for(self,user):
  device=getattr(user,'satellite_id',None) or self.aliases.get(user.device_id,user.device_id)
  self.results.pop(device,None);self.profiles.cancel(device)
  self.gate.cancel(device)
 def enrollment_state(self):
  now=self.profiles.clock()
  return [{'samples':len(slot['samples']),'required_samples':3,
           'expires_in_s':max(0,round(300-(now-slot['at'])))}
          for slot in list(self.profiles.pending.values()) if 0<=now-slot['at']<=300]
 async def complete(self,device,pcm,voiced,text,*,playback=False,context_id=None):
  self.capture_count+=1;start=self.clock()
  result={'status':'too_short'}
  if voiced>=2.5:
   try:result=await self.infer(pcm)
   except Exception as exc:result={'status':'unavailable','error':type(exc).__name__}
  self.results[device]={'at':self.clock(),'text':norm(text),'voiced':voiced,'result':result,'playback':playback,
                        'utterance':hashlib.sha256(pcm).hexdigest(),'context_id':context_id}
  while len(self.results)>4:self.results.pop(next(iter(self.results)))
  self.last={'status':result.get('status','unavailable'),'audio_seconds':round(len(pcm)/32000,2),
             'voiced_seconds':round(voiced,2),'inference_ms':round((self.clock()-start)*1000,1)}
 async def turn(self,user,conversation):
  device=getattr(user,'satellite_id',None) or self.aliases.get(user.device_id,user.device_id)
  item=self.results.pop(device,None)
  if not item or not 0<=self.clock()-item['at']<=15 or norm(user.text)!=item['text']:return None
  if item.get('context_id') is not None and item['context_id']!=getattr(getattr(user,'context',None),'id',None):return None
  decision=await self.hass.async_add_executor_job(self._turn_sync,device,str(conversation),user.text,item)
  authorized=decision.get('authorized',False)
  if authorized and not decision.get('calibration'):
   effective=decision.get('effective_text',user.text)
   decision['control_token']=self.gate.issue(device,effective,decision.get('memory_id'),True)
   self.last['adaptation']=await self.hass.async_add_executor_job(self.adaptation.offer,decision['memory_id'],
    {'vector':item['result'].get('vector'),'windows':item['result'].get('windows',[]),'quality':item['result'].get('quality'),
     'seconds':item['voiced'],'playback':item['playback'],'conversation':str(conversation),'utterance':item['utterance'],'replay_live':False})
  self.last.update(decision_status=decision.get('status'),accepted_samples=decision.get('samples'))
  return decision
 def _turn_sync(self,device,conversation,text,item):
  data=item['result'];value=norm(text)
  good=data.get('status')=='ok' and data.get('model')==MODEL_ID
  vector=data.get('vector') if good else None
  identity=self.profiles.identify(vector) if vector else {'status':data.get('status','unknown')}
  if identity.get('status')=='recognized':
   for window in data.get('windows',[]):
    match=self.profiles.identify(window)
    if match.get('profile')!=identity['profile']:identity={'status':'uncertain_windows'};break
  authorized=bool(identity.get('status')=='recognized' and self.profiles.is_authorized(identity.get('memory_id')))
  if self.enforce and not authorized:
   if data.get('status')=='too_short' and norm(text) in ('zhasni','rozsvit','zamkni','odemkni'):
    challenge=self.gate.pending(device,text)
    phrases={'zhasni':'Potvrzuji zhasnutí světel v této místnosti.', 'rozsvit':'Potvrzuji rozsvícení světel v této místnosti.',
             'zamkni':'Potvrzuji zamknutí hlavního vchodu.', 'odemkni':'Potvrzuji odemknutí hlavního vchodu.'}
    reply='Krátké slovo nestačí k ověření hlasu. Řekni do deseti sekund: '+phrases[norm(text)].rstrip('.')+(' '+challenge if challenge else '')+'.'
   else:
    self.gate.cancel(device);reply='Tvůj hlas nemám jistě ověřený a povel neprovedu. Řekni prosím delší větu.'
   return {'status':identity.get('status','unknown'),'authorized':False,'local_reply':reply}
  confirmed=self.gate.confirm(device,text,authorized)
  if authorized:
   identity={**identity,'authorized':True}
   if confirmed:identity['effective_text']=confirmed
   elif command(text):identity['effective_text']=re.sub(r'^anicko\s+','',norm(text))
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
   self.last.update(status='recognized',profile=identity['profile'],score=identity['score'])
   return identity
  direct=bool(re.match(r'(kolik|zapni|vypni|zhasni|nastav|odemkni|zamkni)\b',value))
  ask=bool(not direct and conversation not in self.asked)
  if ask:self.asked[conversation]=True
  while len(self.asked)>32:self.asked.pop(next(iter(self.asked)))
  return {**identity,'request_introduction':ask}



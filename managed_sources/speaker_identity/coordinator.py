"""One-shot active-turn audio results and explicit enrollment conversation."""
import re
import time
if __package__:
 from .policy import VoiceProfiles,MODEL_ID,norm
else:
 from policy import VoiceProfiles,MODEL_ID,norm

async def admin_forget(hass,user_id,name,coordinator,clear_memory):
 account=await hass.auth.async_get_user(user_id) if user_id else None
 if not account or not account.is_admin or not account.is_active or account.is_system_generated:raise PermissionError('administrator_required')
 memory_id=await hass.async_add_executor_job(coordinator.profiles.forget,name)
 if memory_id and clear_memory:await hass.async_add_executor_job(clear_memory,memory_id)

class Coordinator:
 def __init__(self,hass,path,infer,clock=time.monotonic):
  self.hass=hass;self.profiles=VoiceProfiles(path);self.infer=infer;self.clock=clock
  self.results={};self.aliases={};self.asked={};self.last={};self.capture_count=0;self.status='starting'
 def cancel_for(self,user):
  device=getattr(user,'satellite_id',None) or self.aliases.get(user.device_id,user.device_id)
  self.results.pop(device,None);self.profiles.cancel(device)
 def enrollment_state(self):
  now=self.profiles.clock()
  return [{'samples':len(slot['samples']),'required_samples':3,
           'expires_in_s':max(0,round(300-(now-slot['at'])))}
          for slot in list(self.profiles.pending.values()) if 0<=now-slot['at']<=300]
 async def complete(self,device,pcm,voiced,text):
  self.capture_count+=1;start=self.clock()
  result={'status':'too_short'}
  if voiced>=2.5:
   try:result=await self.infer(pcm)
   except Exception as exc:result={'status':'unavailable','error':type(exc).__name__}
  self.results[device]={'at':self.clock(),'text':norm(text),'voiced':voiced,'result':result}
  while len(self.results)>4:self.results.pop(next(iter(self.results)))
  self.last={'status':result.get('status','unavailable'),'audio_seconds':round(len(pcm)/32000,2),
             'voiced_seconds':round(voiced,2),'inference_ms':round((self.clock()-start)*1000,1)}
 async def turn(self,user,conversation):
  device=getattr(user,'satellite_id',None) or self.aliases.get(user.device_id,user.device_id)
  item=self.results.pop(device,None)
  if not item or not 0<=self.clock()-item['at']<=15 or norm(user.text)!=item['text']:return None
  decision=await self.hass.async_add_executor_job(self._turn_sync,device,str(conversation),user.text,item)
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
  if value in {'zrus uceni hlasu','zrus uceni meho hlasu','zrus registraci hlasu'}:
   self.profiles.cancel(device);return {'status':'cancelled','local_reply':'Učení hlasu jsem zrušil.'}
  if value=='smaz muj hlasovy profil':
   if identity.get('status')=='recognized':
    self.profiles.forget(identity['profile'])
    return {'status':'deleted','deleted_profile':identity['profile'],'deleted_memory_id':identity['memory_id'],'local_reply':'Smazal jsem tvůj hlasový profil i jeho konverzační paměť.'}
   return {'status':'unknown','local_reply':'Tvůj hlas teď nerozpoznávám dost jistě. Profil proto nemažu.'}
  if value=='vylepsi muj hlasovy profil':
   improved=bool(vector and identity.get('profile') and self.profiles.improve(identity['profile'],vector,item['voiced']))
   return {**identity,'local_reply':'Přidal jsem potvrzenou ukázku do tvého hlasového profilu.' if improved else 'Pro vylepšení potřebuji delší ukázku a jistější shodu hlasu.'}
  enrollment=re.fullmatch(r'(?:nauc se|zapamatuj si) muj hlas (?:jsem|jmenuji se) (.+)',value)
  if enrollment:
   if not vector:return {'status':data.get('status','unknown'),'local_reply':'Nemám teď dost kvalitní zvuk pro učení. Řekni prosím znovu delší větu se svým jménem.'}
   names={'martin':'Martin','sarlota':'Šarlota','iris':'Iris','petr':'Petr','dana':'Dana'}
   name=names.get(enrollment[1],enrollment[1].title())
   result=self.profiles.begin(device,name)
   if result['status']=='exists':return {'status':'exists','local_reply':'Profil tohoto jména už existuje. Bez jeho rozpoznání ho nepřepíšu.'}
   if result['status']!='enrolling':return {'status':result['status'],'local_reply':'Tento hlasový profil se mi nepodařilo založit.'}
   return {'status':'enrolling','local_reply':'Dobře, vytvořím místní hlasový profil pro oslovení a tvoji konverzační paměť. Potřebuji tři delší ukázky. Řekni třeba: Dnes jsem doma a učím Džárvise poznat můj hlas. Můžeš začít?'}
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


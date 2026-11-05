"""Fixed low-power commissioning of the inverter's native TOU Sell bit.

This never unlocks production battery sales. Daily recurrence is a separate gate.
Only verified LV/Capacity installations with uniform ordinary house slots qualify.
"""
import copy
from datetime import datetime,timedelta
import math
import time
from zoneinfo import ZoneInfo
try:from .sales import number
except ImportError:from sales import number
TZ=ZoneInfo('Europe/Prague')
WRITABLE={109,142,143,145,146,*range(148,160),*range(166,178)}

class NativeWindow:
 def __init__(self,native_read,native_write,telemetry,save,event,clock=time.time,saved=None):
  self.native_read,self.native_write,self.telemetry,self.save,self.event=native_read,native_write,telemetry,save,event
  self.clock=clock;self.record=copy.deepcopy(saved or {});self.error=''
 @property
 def active(self):return bool(self.record.get('before'))
 async def _set(self,address,value,protective=False):
  if address not in WRITABLE or type(value) is not int or not 0<=value<=65535:raise ValueError('Invalid native test write')
  try:await self.event('native_window_write_intent',{'address':address,'value':value,'id':self.record.get('id')})
  except Exception:
   if not protective:raise
  if address==173 and value==32:
   self._valid()
   if self.clock()>=self.record['arm_until']:raise ValueError('Native arming window or command expired')
  if address==145 and value==1 or address==142 and value==0:
   self._valid()
   if not self.record['start']<=self.clock()<self.record['end']-10:raise ValueError('Export enabling window expired')
  await self.native_write(address,value)
  try:await self.event('native_window_write_confirmed',{'address':address,'value':value,'id':self.record.get('id')})
  except Exception:
   if not protective:raise
 def _valid(self):
  s=self.telemetry();t=number(s.get('reported_at'));soc=number(s.get('soc'));price=number(s.get('net_price'))
  if not s.get('healthy') or t is None or not 0<=self.clock()-t<30 or soc is None or soc<97 or price is None or price<=0:
   raise ValueError('Native test needs fresh healthy measurements, SOC97% and positive price')
  return s
 async def start(self,valid_until=None,solar_sell=False,selling_first=False):
  if self.active:raise ValueError('Native test is already active')
  if type(solar_sell) is not bool or type(selling_first) is not bool or solar_sell and selling_first:raise ValueError('Invalid commissioning variant')
  self._valid();data=await self.native_read();self._valid();r=data['registers'];native=data['clock']
  now=self.clock()
  if valid_until is not None and now>valid_until:raise ValueError('Test command expired')
  if native.tzinfo is None or abs(native.timestamp()-now)>5:raise ValueError('Inverter clock is not verified')
  # The installed deye_p3 profile explicitly maps both 0x0005 and0x0500 to LV.
  if r.get(0) not in (5,0x0500) or r.get(98)!=1 or r.get(111)!=1 or r.get(130)!=0:
   raise ValueError(f"Requires LV lithium Capacity mode with grid charging off: type={r.get(0)}, control={r.get(98)}, operation={r.get(111)}, grid_charge={r.get(130)}")
  if r.get(142)!=2 or r.get(145)!=0 or r.get(146)!=255:raise ValueError('Requires ordinary Zero CT weekly house mode')
  socs=[r.get(166+i) for i in range(6)];powers=[r.get(154+i) for i in range(6)]
  if len(set(socs))!=1 or socs[0] is None or not 0<socs[0]<60 or len(set(powers))!=1 or powers[0] is None or powers[0]<500:
   raise ValueError('House schedule is not uniform; no automatic rewrite')
  if any(r.get(172+i)!=0 for i in range(6)):raise ValueError('Charging or selling is already scheduled')
  current=number(r.get(109));bms=number(r.get(219))
  if current is None or bms is None or not 1<=current<=175 or bms<1:raise ValueError('Native current limit is not verified')
  # A future five-minute boundary leaves a preparation buffer. Never cross days.
  local=native.astimezone(TZ);minute=math.ceil((local.hour*60+local.minute+3)/5)*5
  if not 5<=minute<=1415:raise ValueError('No same-day test window available')
  day=local.replace(hour=0,minute=0,second=0,microsecond=0)
  start=day+timedelta(minutes=minute);end=start+timedelta(minutes=5)
  if end.timestamp()-start.timestamp()!=300:raise ValueError('Ambiguous clock boundary')
  before={str(a):r[a] for a in WRITABLE}
  self.record={'id':str(time.time_ns()),'before':before,'start':start.timestamp(),'end':end.timestamp(),'arm_until':min(start.timestamp()-10,valid_until if valid_until is not None else start.timestamp()-10),'phase':'preparing','observed':False,'native_expiry_observed':False,'power_w':500,'minimum_soc':95,'solar_sell':solar_sell,'selling_first':selling_first,'production_verified':False,'notice':'Commissioning only. Daily slot can recur during an HA outage; production remains blocked.'+(' Outside-slot SOC100 blocks ordinary house battery use; grid supplies house until restoration. PV export may continue.' if selling_first else ' All six SOC floors remain95% until restoration.' if solar_sell else '')}
  await self.save(copy.deepcopy(self.record))
  try:
   await self.event('native_window_start',copy.deepcopy(self.record))
   await self._set(143,500);await self._set(109,int(min(20,current,bms)))
   # All flags remain clear while all six safe slots are prepared.
   for i,m in enumerate((0,minute,minute+5,minute+10,minute+15,1435)):
    await self._set(148+i,(m//60)*100+m%60)
    await self._set(154+i,500 if i==1 else powers[0])
    await self._set(166+i,95 if i==1 or solar_sell else 100 if selling_first else socs[0])
   self._valid()
   if self.clock()>=start.timestamp()-10 or valid_until is not None and self.clock()>valid_until:raise ValueError('Preparation window expired')
   if not selling_first:await self._set(173,32) # arm last, no grid/generator charge bits
   self.record['phase']='armed';await self.save(copy.deepcopy(self.record))
  except Exception:
   await self.stop('start_failed');raise
 async def tick(self):
  if not self.active:return
  if self.record.get('phase')=='stopping':await self.stop('retry');return
  now=self.clock();s=self.telemetry();stamp=number(s.get('reported_at'));grid=number(s.get('grid_w'));batt=number(s.get('battery_w'));pv=number(s.get('pv_w'));soc=number(s.get('soc'));price=number(s.get('net_price'))
  fresh=stamp is not None and 0<=now-stamp<30
  if not s.get('healthy') or not fresh or grid is None or batt is None or pv is None or soc is None or price is None or price<=0 or soc<=95 or grid<-800:
   await self.stop('guard');return
  if now<self.record['start']:
   if grid<-100:await self.stop('early_export')
   return
  if (self.record.get('solar_sell') or self.record.get('selling_first')) and not self.record.get('sell_enabled_at'):
   try:
    await self._set(142,0) if self.record.get('selling_first') else await self._set(145,1)
    self.record['sell_enabled_at']=self.clock();self.record['phase']='awaiting_power';await self.save(copy.deepcopy(self.record))
   except Exception as exc:self.error=str(exc);await self.stop('enable_failed')
   return
  await self.event('native_window_measurement',{'id':self.record['id'],'t':stamp,'grid_w':grid,'battery_w':batt,'pv_w':pv,'soc':soc})
  if now<self.record['end']:
   self.record['phase']='measuring'
   if grid<-100 and batt>100 and -grid>pv+100 and stamp>max(self.record.get('last_export',0),self.record.get('sell_enabled_at',0)):
    self.record.setdefault('first_export',stamp);self.record['last_export']=stamp;self.record['count']=self.record.get('count',0)+1
    self.record['observed']=self.record['count']>=3 and stamp-self.record['first_export']>=20
  elif grid>=-100 and stamp>=self.record['end']:
   # Read hardware clock/program after the boundary, before any stop write.
   if self.record['observed'] and self.record.get('last_export',0)>=self.record['end']-15 and not self.record['native_expiry_observed']:
    native=await self.native_read();r=native['registers']
    expected_mode=0 if self.record.get('selling_first') else 2
    next_soc_ok=not self.record.get('selling_first') or r.get(168)==100 and batt<=100
    if native['clock'].timestamp()>=self.record['end'] and r.get(142)==expected_mode and r.get(145)==(1 if self.record.get('solar_sell') else 0) and r.get(174)==0 and next_soc_ok:
     self.record['native_expiry_observed']=True;self.record['phase']='expiry_observed'
     await self.event('native_window_expiry',{'id':self.record['id'],'clock':native['clock'].isoformat(),'grid_w':grid,'battery_w':batt,'soc':soc,'next_soc':r.get(168)})
  if now>=self.record['end']+20:await self.stop('deadline');return
  await self.save(copy.deepcopy(self.record))
 async def stop(self,reason='manual'):
  if not self.active:return
  self.record['phase']='stopping';self.record.setdefault('stop_issued',self.clock());self.record.setdefault('stop_reason',reason)
  self.record.setdefault('stop_context',{'captured_at':self.clock(),**self.telemetry()})
  try:await self.save(copy.deepcopy(self.record))
  except Exception:pass
  failures=[]
  # Independent protections must all be attempted, even if an earlier one fails.
  for a,v in [(142,2),(143,0),(145,0),*((172+i,0) for i in range(6))]:
   try:await self._set(a,v,True)
   except Exception as exc:failures.append(f'{a}: {type(exc).__name__}')
  s=self.telemetry();grid=number(s.get('grid_w'));stamp=number(s.get('reported_at'))
  if failures or grid is None or grid<-100 or stamp is None or stamp<=self.record['stop_issued'] or not 0<=self.clock()-stamp<30:
   self.error='Native cleanup awaits verified stop: '+', '.join(failures);await self.save(copy.deepcopy(self.record));return
  try:
   before=self.record['before']
   for a in sorted(WRITABLE-{142,143,145,146,109}):await self._set(a,int(before[str(a)]))
   await self._set(146,int(before['146']));await self._set(109,int(before['109']));await self._set(143,9300)
   snapshot=(await self.native_read())['registers']
   expected={int(a):v for a,v in before.items()};expected.update({142:2,143:9300,145:0})
   if any(snapshot.get(a)!=v for a,v in expected.items()):raise ValueError('Full native snapshot does not confirm restoration')
   proof={k:self.record.get(k) for k in ('id','observed','native_expiry_observed','production_verified','start','end','solar_sell','selling_first','stop_context')}
   proof.update(reason=self.record['stop_reason'],stop_verified=True)
   await self.event('native_window_stop',proof);await self.save({});self.record={};self.error=''
  except Exception as exc:
   self.error='Native restoration awaits retry: '+type(exc).__name__;await self.save(copy.deepcopy(self.record))

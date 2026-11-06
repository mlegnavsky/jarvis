"""Serialized durable export transaction. A connected timer is not a hardware watchdog."""
import asyncio
import copy
import time
try:from .sales import EXPORT_LIMIT,number
except ImportError:from sales import EXPORT_LIMIT,number

MODE='select.inverter_work_mode'
ENABLE='switch.inverter_export_surplus'
CAP='number.inverter_export_surplus_power'

def same_setting(actual,expected):
 a,b=number(actual),number(expected)
 return a==b if a is not None and b is not None else actual==expected

class SaleController:
 def __init__(self,read,write,save,event,clock=time.time,healthy=lambda:True,price=lambda:None,saved=None,reported=None):
  self.read,self.write,self.save,self.event=read,write,save,event
  self.clock,self.healthy,self.price=clock,healthy,price
  self.record=copy.deepcopy(saved or {});self.lock=asyncio.Lock();self.error='';self.observed=False
  self.reported=reported or (lambda:None);self.last_stop=None
 @property
 def active(self):return bool(self.record.get('before'))
 def _validate_write(self):
  price=number(self.price())
  if not self.healthy() or price is None or price<=0 and self.record.get('mode')!='bias':raise ValueError('Chybí aktuální měření nebo kladná výkupní cena.')
  if self.clock()>=self.record['deadline']:raise ValueError('Příprava překročila časové okno prodeje.')
 async def _persist_write(self,guard):
  try:await self.save(copy.deepcopy(self.record))
  except Exception:
   if guard:raise
 def _conflicts(self,states):
  conflicts=self.record.setdefault('conflicts',{})
  expected=self.record.get('expected',{})
  pending=self.record.get('pending',{})
  for entity,value in list(expected.items()):
   actual=states.get(entity)
   if entity in pending and same_setting(actual,pending[entity]):
    expected[entity]=pending.pop(entity);continue
   if not same_setting(actual,value):
    conflicts[entity]={'expected':value,'actual':actual}
    if entity==CAP:
     cap=number(actual)
     if cap is not None and cap>=0:self.record['restore_cap']=min(self.record.get('restore_cap',EXPORT_LIMIT),cap,EXPORT_LIMIT)
  return conflicts
 def _restore_safe(self,issued=None):
  states=self.read();changed=False
  for entity,value in ((MODE,'Zero Export To CT'),(ENABLE,'off')):
   if not same_setting(states.get(entity),value):
    self.record.setdefault('conflicts',{})[entity]={'expected':value,'actual':states.get(entity)}
    changed=True
  if changed:
   self.record['protection_conflict']=True
   self.record['inhibited']=True
   self.record['stop_reason']='external_override'
   raise ValueError('Ochranný režim se během obnovy změnil; znovu ukončuji dodávku.')
  grid=number(states.get('sensor.inverter_grid_power'));stamp=number(self.reported())
  issued=self.record.get('stop_issued',float('inf')) if issued is None else issued
  if grid is None or grid<-100 or stamp is None or stamp<=issued or not 0<=self.clock()-stamp<30:
   raise ValueError('Obnova vyžaduje čerstvé měření zastavené dodávky.')
 async def _confirm_stopped(self,issued):
  for attempt in range(20):
   try:
    self._restore_safe(issued)
    return
   except ValueError:
    if self.record.get('protection_conflict') or attempt==19:raise
   await asyncio.sleep(1)
 async def _set(self,entity,value,guard=True,owned=False):
  previous=self.record.get('expected',{}).get(entity)
  previous_pending=self.record.get('pending',{}).get(entity)
  if guard:self._validate_write()
  try:await self.event('write_intent',{'entity':entity,'before':self.read().get(entity),'value':value,'sale_id':self.record.get('id')})
  except Exception:
   if guard:raise
   self.error='Historie je nedostupná; provádím bezpečné ukončení.'
  if guard:self._validate_write()
  self.record.setdefault('pending',{})[entity]=value
  await self._persist_write(guard)
  if guard:self._validate_write()
  if guard and ((entity==ENABLE and value=='on') or (entity==MODE and value=='Export First')):
   # Audit/storage awaits may admit an owner edit after preflight. Never enable
   # export over a changed mode, SOC floor, charging flag or other owned setting.
   if self._conflicts(self.read()):
    self.record['stop_reason']='external_override'
    raise ValueError('Nastavení měniče změnil jiný držitel řízení; prodej nespouštím.')
  if owned:self._restore_safe()
  if owned and previous is not None:
   actual=self.read().get(entity)
   if not same_setting(actual,previous) and not (previous_pending is not None and same_setting(actual,previous_pending)):
    self.record.setdefault('conflicts',{})[entity]={'expected':previous,'actual':actual}
    self.record['pending'].pop(entity,None)
    await self._persist_write(False)
    return
  try:await self.write(entity,value)
  except Exception as exc:
   await self.event('write_failed',{'entity':entity,'error':str(exc),'sale_id':self.record.get('id')});raise
  self.record.setdefault('expected',{})[entity]=value
  self.record['pending'].pop(entity,None)
  await self._persist_write(guard)
  try:await self.event('write_confirmed',{'entity':entity,'value':self.read().get(entity),'sale_id':self.record.get('id')})
  except Exception:
   if guard:raise
 async def start(self,mode,power_w,duration_minutes,minimum_soc=62,purpose='manual',promote_auto=False):
  async with self.lock:
   if self.active:raise ValueError('Nejprve dokončím předchozí prodej.')
   power=number(power_w);minutes=number(duration_minutes);floor=number(minimum_soc)
   bias=mode=='bias' and purpose in ('bias_probe','automatic') and power==2 and floor==30
   if (not bias and (mode not in ('pv','battery') or power is None or not 100<=power<=EXPORT_LIMIT or floor is None or not 60<=floor<=100)) or minutes is None or not 1<=minutes<=60:
    raise ValueError('Neplatný výkon, délka nebo rezerva prodeje.')
   if not self.healthy() or number(self.price()) is None or self.price()<=0 and not bias:raise ValueError('Čekám na aktuální měření a kladnou cenu.')
   states=self.read()
   if states.get(MODE)!='Zero Export To CT' or states.get(ENABLE)!='off':raise ValueError('Výchozí režim musí být bez přetoků.')
   keys=[CAP,ENABLE,MODE];steps=[(CAP,int(power))]
   soc=number(states.get('sensor.inverter_battery'))
   if soc is None:raise ValueError('Nabití baterie je nedostupné.')
   if states.get('select.inverter_time_of_use') not in ('Week','Enabled'):raise ValueError('Vyžaduji ověřený aktivní týdenní program.')
   for i in range(1,7):
    if states.get(f'select.inverter_program_{i}_charging')!='Disabled':raise ValueError('Současně je povolené nabíjení v časovém programu.')
   if bias:
    if soc<32:raise ValueError('Malý přetok vyžaduje baterii alespoň32 %.')
    for i in range(1,7):
     target=f'number.inverter_program_{i}_soc';p=f'number.inverter_program_{i}_power'
     if number(states.get(target))!=30 or number(states.get(p)) is None or number(states.get(p))<500:raise ValueError('Malý přetok vyžaduje běžný domácí program s rezervou30 %.')
    steps.append((MODE,'Export First'))
   elif mode=='battery':
    if soc<=floor:raise ValueError('Baterie je na rezervě pro prodej.')
    if states.get('select.inverter_time_of_use') not in ('Week','Enabled'):raise ValueError('Vyžaduji ověřený aktivní týdenní program.')
    for i in range(1,7):
     target=f'number.inverter_program_{i}_soc';p=f'number.inverter_program_{i}_power';charge=f'select.inverter_program_{i}_charging'
     if states.get(charge)!='Disabled':raise ValueError('Současně je povolené nabíjení v časovém programu.')
     keys.extend((target,p));steps.extend(((target,floor),(p,int(power))))
    steps.append((MODE,'Export First'))
   else:
    for i in range(1,7):
     target=f'number.inverter_program_{i}_soc';keys.append(target);steps.append((target,100))
    steps.append((ENABLE,'on'))
   if any(states.get(k) in (None,'unknown','unavailable') for k in keys):raise ValueError('Nastavení měniče není dostupné.')
   self.record={'id':str(time.time_ns()),'before':{k:states[k] for k in keys},'mode':mode,'power_w':int(power),'purpose':purpose,'promote_auto':bool(promote_auto),
    'baseline_export_w':max(0,-(number(states.get('sensor.inverter_grid_power')) or 0)),
    'minimum_soc':floor,'started':self.clock(),'deadline':self.clock()+minutes*60,'phase':'starting',
    'expected':{k:v for k,v in states.items() if k in keys or k=='select.inverter_time_of_use' or k.startswith(('time.inverter_program_','select.inverter_program_','number.inverter_program_')) or k in ('number.inverter_battery_max_discharging_current','number.inverter_battery_max_charging_current')},
    'restore_cap':min(number(states.get(CAP)),EXPORT_LIMIT),'conflicts':{},'pending':{}}
   await self.save(copy.deepcopy(self.record))
   try:
    await self.event('sale_start',dict(self.record))
    for entity,value in steps:await self._set(entity,value)
    self.record['phase']='awaiting_power';self.record['enabled_at']=self.clock();await self.save(copy.deepcopy(self.record))
    self.observed=False;self.error=''
   except Exception as exc:
    self.error=str(exc);await self._stop('start_failed');raise
 async def stop(self,reason='manual'):
  async with self.lock:await self._stop(reason)
 async def _stop(self,reason='manual'):
  if not self.active:return
  if number(self.reported()) is not None and number(self.reported())>self.record.get('enabled_at',float('inf')):
   self._conflicts(self.read())
  self.record.setdefault('stop_reason',reason)
  self.record['phase']='stopping'
  self.record['protection_conflict']=False
  try:await self.save(copy.deepcopy(self.record))
  except Exception:pass # still attempt physical safe stop with original durable record
  issued=self.clock();self.record['stop_issued']=issued;failures=[];ack={}
  # Attempt independent protective commands even if the preceding write failed.
  for entity,value in ((CAP,0),(MODE,'Zero Export To CT'),(ENABLE,'off')):
   try:await self._set(entity,value,False);ack[entity]=True
   except Exception as exc:failures.append(entity+': '+str(exc));ack[entity]=False
  try:
   if not ack.get(MODE) or not ack.get(ENABLE):raise RuntimeError('; '.join(failures))
   await self._confirm_stopped(issued)
   for entity,value in self.record['before'].items():
    if entity in (CAP,MODE,ENABLE) or entity in self.record.get('conflicts',{}):continue
    # Compare each field again immediately before restoring it. A durable expected
    # value follows our own partial restores, including restart/retry recovery.
    expected=self.record.get('expected',{}).get(entity)
    pending=self.record.get('pending',{}).get(entity)
    actual=self.read().get(entity)
    if expected is not None and not same_setting(actual,expected) and not (pending is not None and same_setting(actual,pending)):
     self.record.setdefault('conflicts',{})[entity]={'expected':expected,'actual':actual};continue
    await self._set(entity,value,False,owned=True)
   await self._set(CAP,self.record.get('restore_cap',EXPORT_LIMIT),False,owned=True)
   # Re-acknowledge both native protections after every SOC/CAP restoration.
   # The write callback must confirm the physical device, not optimistic HA state.
   final_issued=self.clock()
   await self._set(MODE,'Zero Export To CT',False)
   await self._set(ENABLE,'off',False)
   await self._confirm_stopped(final_issued)
   proof={'id':self.record.get('id'),'mode':self.record.get('mode'),'purpose':self.record.get('purpose'),
    'promote_auto':self.record.get('promote_auto',False),'reason':'stop_recovery' if failures or self.record.get('stop_attempt_failed') else self.record['stop_reason'],
    'observed':self.observed,'stop_verified':True,'power_w':self.record.get('power_w'),'minimum_soc':self.record.get('minimum_soc'),
    'sustained':self.record.get('export_count',0)>=3 and self.record.get('export_last',0)-self.record.get('export_first',0)>=20,
    'error':self.error,'failures':failures,'context':self.record.get('stop_context'),'conflicts':copy.deepcopy(self.record.get('conflicts',{}))}
   await self.event('sale_stop',proof)
   self._restore_safe(final_issued)
   await self.save({})
   self._restore_safe(final_issued)
   self.record={};self.observed=False;self.last_stop=proof
  except Exception as exc:
   self.record['stop_attempt_failed']=True
   self.error='Ukončení prodeje není potvrzené: '+str(exc)
   if self.record.get('protection_conflict'):
    # A competing writer invalidates restoration. Keep cleanup latched and
    # independently reapply protections; no SOC restore or CAP increase follows.
    for entity,value in ((CAP,0),(MODE,'Zero Export To CT'),(ENABLE,'off')):
     try:await self._set(entity,value,False)
     except Exception:pass
   try:await self.save(copy.deepcopy(self.record))
   except Exception:pass
 def _bias_sample(self,stamp,grid):
  if stamp is None or grid is None or not self.record.get('enabled_at',float('inf'))<stamp or not 0<=self.clock()-stamp<30:
   self.observed=False;return
  if stamp<=self.record.get('bias_last',0):return
  self.record['bias_last']=stamp
  samples=self.record.setdefault('bias_samples',[]);samples.append([stamp,grid]);del samples[:-12]
  mean=sum(v for _,v in samples)/len(samples);self.record['bias_average_w']=mean
  self.observed=len(samples)>=3 and samples[-1][0]-samples[0][0]>=20 and -50<=mean<0
  if self.observed:
   self.record['bias_confirmed_at']=self.clock()
   self.record['phase']='running';self.record.setdefault('export_first',samples[0][0]);self.record['export_last']=stamp;self.record['export_count']=len(samples)
  else:
   for k in ('export_first','export_last','export_count'):self.record.pop(k,None)
 async def tick(self):
  if not self.active or self.lock.locked():return
  states=self.read();grid=number(states.get('sensor.inverter_grid_power'));batt=number(states.get('sensor.inverter_battery_power'));soc=number(states.get('sensor.inverter_battery'))
  price=number(self.price());mode=self.record['mode']
  stamp=number(self.reported());fresh=stamp is not None and stamp>self.record.get('enabled_at',float('inf'))
  conflicts=self._conflicts(states) if fresh and self.record.get('phase')!='stopping' and self.healthy() else self.record.get('conflicts',{})
  no_surplus=False
  if mode=='pv' and fresh and self.healthy() and stamp>self.record.get('deficit_last',0):
   self.record['deficit_last']=stamp
   if grid is not None and grid>50:
    self.record.setdefault('deficit_first',stamp)
    no_surplus=stamp-self.record['deficit_first']>=5
   else:self.record.pop('deficit_first',None)
  if mode=='bias' and self.record.get('phase')!='stopping':self._bias_sample(stamp,grid)
  wrong_mode=states.get(MODE)!=('Export First' if mode in ('battery','bias') else 'Zero Export To CT')
  triggers=[]
  if not self.healthy():triggers.append('measurement_or_health')
  if price is None or price<=0 and mode!='bias':triggers.append('price')
  if grid is None or soc is None:triggers.append('missing_measurement')
  if wrong_mode:triggers.append('mode_changed')
  if mode=='pv' and grid is not None and grid<-100 and batt is not None and batt>200:triggers.append('battery_discharge')
  bias_excess=False
  if mode=='bias' and stamp is not None and stamp>self.record.get('bias_guard_last',0) and self.record.get('enabled_at',float('inf'))<stamp and 0<=self.clock()-stamp<30:
   self.record['bias_guard_last']=stamp
   if grid is not None and grid<-50:
    self.record.setdefault('bias_excess_first',stamp);bias_excess=stamp-self.record['bias_excess_first']>=20
   else:self.record.pop('bias_excess_first',None)
  if grid is not None and (-grid>self.record['power_w']+300 or bias_excess):triggers.append('export_limit')
  deadline=self.clock()>=self.record['deadline']
  reserve=soc is not None and (mode in ('battery','bias') and soc<=self.record['minimum_soc'] or mode=='pv' and self.record.get('purpose')=='automatic' and soc<97)
  if triggers or conflicts or no_surplus or deadline or reserve or self.record.get('phase')=='stopping':
   self.record.setdefault('stop_context',{'triggers':triggers,'grid_w':grid,'battery_w':batt,'soc':soc,
    'pv_w':number(states.get('sensor.inverter_pv_power')),'requested_w':self.record['power_w'],
    'reported_at':number(self.reported()),'price_net':price,'captured_at':self.clock()})
   if 'export_limit' in triggers:self.error=f"Dodávka {-grid:g} W překročila výkonovou ochranu pro režim{mode}."
   elif triggers:self.error='Ochrana prodeje: '+', '.join(triggers)
   reason='external_override' if conflicts else 'price' if triggers==['price'] and price is not None else 'guard' if triggers else 'no_surplus' if no_surplus else 'deadline' if deadline else 'reserve'
   if reason in ('price','no_surplus'):self.error=''
   await self.stop(reason);return
  stamp=number(self.reported())
  if stamp is not None and stamp>self.record.get('sample_last',0):
   await self.event('sale_measurement',{'sale_id':self.record.get('id'),'source_t':stamp,'grid_w':grid,'battery_w':batt,'soc':soc,'pv_w':number(states.get('sensor.inverter_pv_power')),'requested_w':self.record['power_w']})
   self.record['sample_last']=stamp
  if mode=='bias':
   if self.clock()-self.record.get('bias_confirmed_at',self.record['started'])>=180 and not self.observed:
    self.error='Malý přetok se nepotvrdil; požadované2 W nepovažuji za skutečný export.'
    await self.stop('no_export')
   return
  threshold=max(100,self.record.get('baseline_export_w',0)+100)
  if grid is not None and grid < -threshold and stamp is not None and stamp>self.record.get('enabled_at',float('inf')):
   if stamp>self.record.get('export_last',0):
    self.record.setdefault('export_first',stamp);self.record['export_last']=stamp;self.record['export_count']=self.record.get('export_count',0)+1
   resumed=self.observed and self.record.get('phase')!='running'
   if not self.observed or resumed:
    self.observed=True;self.record['phase']='running'
    await self.event('export_observed',{'sale_id':self.record.get('id'),'grid_w':grid,'battery_w':batt,'soc':soc})
    await self.save(copy.deepcopy(self.record))
  elif mode=='pv' and (self.observed or self.record.get('purpose')!='commission' and self.clock()-self.record['started']>60):
   if self.record.get('phase')!='awaiting_surplus':
    self.record['phase']='awaiting_surplus';await self.save(copy.deepcopy(self.record))
  elif self.clock()-self.record['started']>60:
   self.error='Dodávka se nepotvrdila měřením; prodej ukončuji.';await self.stop('no_export')

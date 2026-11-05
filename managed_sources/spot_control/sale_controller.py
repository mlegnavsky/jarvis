"""Serialized durable export transaction. A connected timer is not a hardware watchdog."""
import asyncio
import copy
import time
try:from .sales import EXPORT_LIMIT,number
except ImportError:from sales import EXPORT_LIMIT,number

MODE='select.inverter_work_mode'
ENABLE='switch.inverter_export_surplus'
CAP='number.inverter_export_surplus_power'

class SaleController:
 def __init__(self,read,write,save,event,clock=time.time,healthy=lambda:True,price=lambda:None,saved=None,reported=None):
  self.read,self.write,self.save,self.event=read,write,save,event
  self.clock,self.healthy,self.price=clock,healthy,price
  self.record=copy.deepcopy(saved or {});self.lock=asyncio.Lock();self.error='';self.observed=False
  self.reported=reported or (lambda:None);self.last_stop=None
 @property
 def active(self):return bool(self.record.get('before'))
 async def _set(self,entity,value,guard=True):
  if guard and (not self.healthy() or number(self.price()) is None or self.price()<=0):
   raise ValueError('Chybí aktuální měření nebo kladná výkupní cena.')
  if guard and self.clock()>=self.record['deadline']:raise ValueError('Příprava překročila časové okno prodeje.')
  try:await self.event('write_intent',{'entity':entity,'before':self.read().get(entity),'value':value,'sale_id':self.record.get('id')})
  except Exception:
   if guard:raise
   self.error='Historie je nedostupná; provádím bezpečné ukončení.'
  try:await self.write(entity,value)
  except Exception as exc:
   await self.event('write_failed',{'entity':entity,'error':str(exc),'sale_id':self.record.get('id')});raise
  try:await self.event('write_confirmed',{'entity':entity,'value':self.read().get(entity),'sale_id':self.record.get('id')})
  except Exception:
   if guard:raise
 async def start(self,mode,power_w,duration_minutes,minimum_soc=62,purpose='manual',promote_auto=False):
  async with self.lock:
   if self.active:raise ValueError('Nejprve dokončím předchozí prodej.')
   power=number(power_w);minutes=number(duration_minutes);floor=number(minimum_soc)
   if mode not in ('pv','battery') or power is None or not 100<=power<=EXPORT_LIMIT or minutes is None or not 1<=minutes<=60 or floor is None or not 60<=floor<=100:
    raise ValueError('Neplatný výkon, délka nebo rezerva prodeje.')
   if not self.healthy() or number(self.price()) is None or self.price()<=0:raise ValueError('Čekám na aktuální měření a kladnou cenu.')
   states=self.read()
   if states.get(MODE)!='Zero Export To CT' or states.get(ENABLE)!='off':raise ValueError('Výchozí režim musí být bez přetoků.')
   keys=[CAP,ENABLE,MODE];steps=[(CAP,int(power))]
   soc=number(states.get('sensor.inverter_battery'))
   if soc is None:raise ValueError('Nabití baterie je nedostupné.')
   if mode=='battery':
    if soc<=floor:raise ValueError('Baterie je na rezervě pro prodej.')
    if states.get('select.inverter_time_of_use') not in ('Week','Enabled'):raise ValueError('Vyžaduji ověřený aktivní týdenní program.')
    for i in range(1,7):
     target=f'number.inverter_program_{i}_soc';p=f'number.inverter_program_{i}_power';charge=f'select.inverter_program_{i}_charging'
     if states.get(charge)!='Disabled':raise ValueError('Současně je povolené nabíjení v časovém programu.')
     keys.extend((target,p));steps.extend(((target,floor),(p,int(power))))
    steps.append((MODE,'Export First'))
   else:steps.append((ENABLE,'on'))
   if any(states.get(k) in (None,'unknown','unavailable') for k in keys):raise ValueError('Nastavení měniče není dostupné.')
   self.record={'id':str(time.time_ns()),'before':{k:states[k] for k in keys},'mode':mode,'power_w':int(power),'purpose':purpose,'promote_auto':bool(promote_auto),
    'baseline_export_w':max(0,-(number(states.get('sensor.inverter_grid_power')) or 0)),
    'minimum_soc':floor,'started':self.clock(),'deadline':self.clock()+minutes*60,'phase':'starting'}
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
  self.record.setdefault('stop_reason',reason)
  self.record['phase']='stopping'
  try:await self.save(copy.deepcopy(self.record))
  except Exception:pass # still attempt physical safe stop with original durable record
  issued=self.clock();failures=[];ack={}
  # Attempt independent protective commands even if the preceding write failed.
  for entity,value in ((CAP,0),(MODE,'Zero Export To CT'),(ENABLE,'off')):
   try:await self._set(entity,value,False);ack[entity]=True
   except Exception as exc:failures.append(entity+': '+str(exc));ack[entity]=False
  try:
   if not ack.get(MODE) or not ack.get(ENABLE):raise RuntimeError('; '.join(failures))
   stopped=False
   for _ in range(20):
    grid=number(self.read().get('sensor.inverter_grid_power'));stamp=number(self.reported())
    if grid is not None and grid>=-100 and stamp is not None and stamp>issued:
     stopped=True;break
    await asyncio.sleep(1)
   if not stopped:raise RuntimeError('Čekám na čerstvé měření zastavené dodávky.')
   for entity,value in self.record['before'].items():
    if entity not in (CAP,MODE,ENABLE):await self._set(entity,value,False)
   await self._set(CAP,EXPORT_LIMIT,False)
   proof={'id':self.record.get('id'),'mode':self.record.get('mode'),'purpose':self.record.get('purpose'),
    'promote_auto':self.record.get('promote_auto',False),'reason':'stop_recovery' if failures or self.record.get('stop_attempt_failed') else self.record['stop_reason'],
    'observed':self.observed,'stop_verified':True,
    'sustained':self.record.get('export_count',0)>=3 and self.record.get('export_last',0)-self.record.get('export_first',0)>=20,
    'error':self.error,'failures':failures,'context':self.record.get('stop_context')}
   await self.event('sale_stop',proof)
   await self.save({})
   self.record={};self.observed=False;self.last_stop=proof
  except Exception as exc:
   self.record['stop_attempt_failed']=True
   self.error='Ukončení prodeje není potvrzené: '+str(exc)
   try:await self.save(copy.deepcopy(self.record))
   except Exception:pass
 async def tick(self):
  if not self.active or self.lock.locked():return
  states=self.read();grid=number(states.get('sensor.inverter_grid_power'));batt=number(states.get('sensor.inverter_battery_power'));soc=number(states.get('sensor.inverter_battery'))
  price=number(self.price());mode=self.record['mode']
  wrong_mode=states.get(MODE)!=('Export First' if mode=='battery' else 'Zero Export To CT')
  triggers=[]
  if not self.healthy():triggers.append('measurement_or_health')
  if price is None or price<=0:triggers.append('price')
  if grid is None or soc is None:triggers.append('missing_measurement')
  if wrong_mode:triggers.append('mode_changed')
  if mode=='pv' and grid is not None and grid<-100 and batt is not None and batt>200:triggers.append('battery_discharge')
  if grid is not None and -grid>self.record['power_w']+300:triggers.append('export_limit')
  deadline=self.clock()>=self.record['deadline']
  reserve=mode=='battery' and soc is not None and soc<=self.record['minimum_soc']
  if triggers or deadline or reserve or self.record.get('phase')=='stopping':
   self.record.setdefault('stop_context',{'triggers':triggers,'grid_w':grid,'battery_w':batt,'soc':soc,
    'pv_w':number(states.get('sensor.inverter_pv_power')),'requested_w':self.record['power_w'],
    'reported_at':number(self.reported()),'price_net':price,'captured_at':self.clock()})
   if 'export_limit' in triggers:self.error=f"Dodávka {-grid:g} W překročila nastavených {self.record['power_w']} W a ochrannou odchylku 300 W."
   elif triggers:self.error='Ochrana prodeje: '+', '.join(triggers)
   reason='guard' if triggers else 'deadline' if deadline else 'reserve'
   await self.stop(reason);return
  stamp=number(self.reported())
  if stamp is not None and stamp>self.record.get('sample_last',0):
   await self.event('sale_measurement',{'sale_id':self.record.get('id'),'source_t':stamp,'grid_w':grid,'battery_w':batt,'soc':soc,'pv_w':number(states.get('sensor.inverter_pv_power')),'requested_w':self.record['power_w']})
   self.record['sample_last']=stamp
  threshold=max(100,self.record.get('baseline_export_w',0)+100)
  if grid is not None and grid < -threshold and stamp is not None and stamp>self.record.get('enabled_at',float('inf')):
   if stamp>self.record.get('export_last',0):
    self.record.setdefault('export_first',stamp);self.record['export_last']=stamp;self.record['export_count']=self.record.get('export_count',0)+1
   if not self.observed:
    self.observed=True;self.record['phase']='running'
    await self.event('export_observed',{'sale_id':self.record.get('id'),'grid_w':grid,'battery_w':batt,'soc':soc})
    await self.save(copy.deepcopy(self.record))
  elif self.clock()-self.record['started']>60:
   self.error='Dodávka se nepotvrdila měřením; prodej ukončuji.';await self.stop('no_export')

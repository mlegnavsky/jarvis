"""Owned low-power grid charge; temporary goals never lower the30% reserve."""
import math
from datetime import datetime
from zoneinfo import ZoneInfo

CURRENT='number.inverter_battery_grid_charging_current'
SWITCH='switch.inverter_battery_grid_charging'

def number(v):
 try:
  n=float(v);return n if math.isfinite(n) else None
 except (ValueError,TypeError):return None

def same(a,b):
 x,y=number(a),number(b)
 return x==y if x is not None and y is not None else a==b

def slot_at(states,minute):
 starts=[]
 for i in range(1,7):
  try:h,m=map(int,states[f'time.inverter_program_{i}_time'].split(':')[:2])
  except (KeyError,ValueError,AttributeError):raise ValueError('Chybí časový program měniče.')
  if not 0<=h<24 or not 0<=m<60:raise ValueError('Neplatný čas programu.')
  starts.append(h*60+m)
 if starts!=sorted(set(starts)):raise ValueError('Časový program není vzestupný.')
 return max((i+1 for i,t in enumerate(starts) if t<=minute),default=6)

class HeatingChargeMixin:
 def heating_ready(self,include_pending=False):
  r=self.record
  if not (self.active and r.get('purpose')=='heating' and r.get('phase')=='running'):return False
  live=self.read();pending=r.get('pending')
  if pending and not include_pending:return False
  if pending and not (same(live.get(pending['entity']),pending['value']) or same(live.get(pending['entity']),r['applied'].get(pending['entity'],r['before'][pending['entity']]))):return False
  return all(same(live.get(e),v) for e,v in r.get('applied',{}).items() if not pending or e!=pending['entity'])

 async def _heat_write(self,entity,value):
  r=self.record;live=self.read()
  if not self.healthy():raise ValueError('Měření nebo souběžný prodej nedovoluje nabíjení.')
  expected=r['applied'].get(entity,r['before'][entity])
  if not same(live.get(entity),expected):raise ValueError('heating_setting_conflict: '+entity)
  r['pending']={'entity':entity,'value':str(value)}
  if entity not in r['order']:r['order'].append(entity)
  await self.save(r)
  await self.write(entity,str(value))
  r['applied'][entity]=str(value);r['pending']=None;await self.save(r)

 async def _heat_slot(self,slot):
  target=f'number.inverter_program_{slot}_soc';charge=f'select.inverter_program_{slot}_charging'
  if slot in self.record['slots']:return
  await self._heat_write(target,self.record['target'])
  await self._heat_write(charge,'Grid')
  self.record['slots'].append(slot);self.record['slot']=slot;await self.save(self.record)

 async def _resize_heating(self,heaters):
  r=self.record
  if r.get('heaters',1)==heaters and r.get('target_w')==1000*heaters:return
  s=self.read();voltage=number(s.get('sensor.inverter_battery_voltage'));cap=number(s.get('number.inverter_battery_max_charging_current'))
  if not self.healthy() or voltage is None or not 44<=voltage<=58 or cap is None or cap<1:raise ValueError('Chybí bezpečné napětí nebo nabíjecí limit.')
  amps=max(1,min(math.floor(heaters*1000/voltage+.5),math.floor(cap)))
  r.update(heaters=heaters,target_w=1000*heaters,amps=amps,power_changed_at=self.clock())
  await self.save(r);await self._heat_write(CURRENT,amps)

 async def resize_heating(self,heaters):
  if type(heaters) is not int or heaters not in (1,2):raise ValueError('Počet radiátorů musí být1nebo2.')
  async with self.lock:
   if not self.active or self.record.get('purpose')!='heating':return
   if not self.heating_ready():raise ValueError('Dobíjení není připravené na změnu výkonu.')
   try:await self._resize_heating(heaters)
   except Exception as exc:self.error=str(exc);await self._restore_heating();raise

 async def start_heating(self,minute,heaters=1):
  if type(heaters) is not int or heaters not in (1,2):raise ValueError('Počet radiátorů musí být1nebo2.')
  async with self.lock:
   if self.active:
    if self.heating_ready():
     try:await self._resize_heating(heaters)
     except Exception as exc:self.error=str(exc);await self._restore_heating();raise
     return
    raise ValueError('Nejprve ukonči předchozí nabíjení nebo obnovu.')
   s=self.read();voltage=number(s.get('sensor.inverter_battery_voltage'));cap=number(s.get('number.inverter_battery_max_charging_current'));temp=number(s.get('sensor.inverter_battery_temperature'));soc=number(s.get('sensor.inverter_battery'))
   if not self.healthy() or temp is None or not 0<=temp<45 or voltage is None or not 44<=voltage<=58 or cap is None or cap<=0 or soc is None or not 0<=soc<=100:raise ValueError('Čekám na bezpečné měření baterie a napětí.')
   if s.get('select.inverter_work_mode')!='Zero Export To CT' or s.get('switch.inverter_export_surplus')!='off' or s.get('select.inverter_time_of_use') not in ('Week','Enabled'):raise ValueError('Nabíjení vyžaduje běžný domácí režim bez přetoků.')
   fields=[CURRENT,SWITCH]
   if number(s.get(CURRENT)) is None or s.get(SWITCH) not in ('on','off'):raise ValueError('Chybí nastavení nabíjení.')
   for i in range(1,7):
    target=f'number.inverter_program_{i}_soc';charge=f'select.inverter_program_{i}_charging';floor=number(s.get(target))
    if floor is None or not 30<=floor<=100 or s.get(charge)!='Disabled':raise ValueError('Předchozí nabíjení nebo bezpečná rezerva není potvrzena.')
    fields.extend((target,charge))
   slot=slot_at(s,minute);amps=max(1,min(math.floor(heaters*1000/voltage+.5),math.floor(cap)))
   r={'purpose':'heating','phase':'starting','before':{e:s[e] for e in fields},'applied':{},'pending':None,'order':[],'slots':[],'target':max(90,math.ceil(soc)),'target_w':1000*heaters,'heaters':heaters,'amps':amps,'started_at':self.clock(),'power_changed_at':self.clock()}
   # Failure to save intent must leave no in-memory active transaction either.
   await self.save(r);self.record=r
   try:
    await self._heat_write(CURRENT,amps)
    await self._heat_write(SWITCH,'on')
    await self._heat_slot(slot)
    r['phase']='running';await self.save(r);self.error='';self.observed=False
   except Exception as exc:
    self.error=str(exc);await self._restore_heating();raise

 async def _restore_heating(self):
  r=self.record
  if not self.active:return
  r['phase']='restoring'
  try:await self.save(r)
  except Exception:pass
  pending=r.get('pending') or {};owned=dict(r.get('applied',{}))
  if pending:owned[pending['entity']]=pending['value']
  order=[e for e in reversed(r.get('order',[])) if e.startswith('select.')]+[e for e in reversed(r.get('order',[])) if e.startswith('number.inverter_program_')]+[e for e in (SWITCH,CURRENT) if e in r.get('order',[])]
  conflicts=[]
  for entity in order:
   current=self.read().get(entity);before=r['before'][entity]
   if not same(current,before):
    if not same(current,owned.get(entity)):
     conflicts.append(entity)
     if entity.startswith('select.'):break
     continue
    try:await self.write(entity,before)
    except Exception as exc:self.error='heating_restore_pending: '+str(exc);return
   r['applied'].pop(entity,None)
   if pending.get('entity')==entity:r['pending']=None
  if conflicts:self.error='heating_restore_conflict: '+','.join(conflicts);return
  try:await self.save({})
  except Exception:self.error='heating_restore_journal_pending';return
  self.record={};self.error=''

 async def tick_heating(self,healthy=True,minute=None):
  if not self.active or self.record.get('purpose')!='heating':return
  s=self.read();temp=number(s.get('sensor.inverter_battery_temperature'))
  if not healthy or temp is None or not 0<=temp<45 or s.get('select.inverter_work_mode')!='Zero Export To CT' or s.get('switch.inverter_export_surplus')!='off' or self.record.get('phase')=='restoring':
   await self.stop();return
  async with self.lock:
   if not self.heating_ready():
    self.error='heating_setting_conflict';await self._restore_heating();return
   stamp=datetime.fromtimestamp(self.clock(),ZoneInfo('Europe/Prague'))
   minute=stamp.hour*60+stamp.minute if minute is None else minute
   try:await self._heat_slot(slot_at(s,minute))
   except Exception as exc:self.error=str(exc);await self._restore_heating();return
   power=number(s.get('sensor.inverter_battery_power'));grid=number(s.get('sensor.inverter_grid_power'))
   if power is not None and grid is not None and power<-100 and grid>100:self.observed=True

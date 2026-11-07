"""Read-only solar supervision. Notifications never run in the control path."""
import asyncio
import math
import time
from datetime import datetime

CODES=('cycle_failure','house_measurement','measurements','control_error','inhibited','capacity','no_export','overdue','grid_target','flow_mismatch','charge_mismatch','monitor_measurements')

LABELS={'sensor.inverter_grid_power':'Síť měniče','sensor.inverter_battery_power':'Výkon baterie',
        'sensor.inverter_pv_power':'Panely','sensor.inverter_battery':'Nabití baterie',
        'sensor.inverter_battery_temperature':'Teplota baterie'}

def timestamp(value):
 if isinstance(value,str):
  try:return datetime.fromisoformat(value.replace('Z','+00:00')).timestamp()
  except (ValueError,OverflowError,OSError):return None
 return finite(value)

class Monitor:
 """Passive evidence only; no device service calls or extra inverter queries."""
 def __init__(self,started_at=0):self.started_at=started_at;self.waiting={};self.last_check=None
 def update(self,body,now):
  if self.last_check is not None and not 0<=now-self.last_check<30:self.waiting={}
  self.last_check=now
  measurements={};alerts=[]
  samples=body.get('telemetry') or {}
  for entity,label in LABELS.items():
   sample=samples.get(entity) or {};value=finite(sample.get('state'));stamp=timestamp(sample.get('source_reported'))
   age=now-stamp if stamp is not None else None
   status='invalid' if value is None else 'timestamp' if age is None or age<0 else 'stale' if age>=30 else 'fresh'
   unit='%' if entity=='sensor.inverter_battery' else '°C' if entity.endswith('temperature') else 'W'
   measurements[entity]={'label':label,'value':value,'unit':unit,'age_seconds':round(age,1) if age is not None else None,'status':status}
  bad=[v['label'] for v in measurements.values() if v['status']!='fresh']
  if bad and body.get('ready') and now-self.started_at>=60:
   alerts.append({'code':'monitor_measurements','level':'error','message':'Chybí platná čerstvá měření: '+', '.join(bad)+'. Skutečný tok nelze potvrdit.'})
  mode='charging' if body.get('charging_active') else body.get('mode') if body.get('active') else 'waiting'
  stopping=body.get('phase')=='stopping'
  names={'charging':'Nabíjení baterie ze sítě','bias':'Malý trvalý přetok','pv':'Prodej přebytků panelů','battery':'Prodej z baterie','battery_commission':'Ruční ověření baterie','waiting':'Čekání podle plánu'}
  result='unknown' if bad else 'waiting';grid=measurements['sensor.inverter_grid_power']['value'];battery=measurements['sensor.inverter_battery_power']['value']
  code=None
  if not stopping and not bad:
   if mode=='charging':
    result='measured_charging' if battery < -100 else 'awaiting_charging'
    if battery>=-100:code='charge_mismatch'
   elif body.get('active'):
    threshold=0 if mode=='bias' else -100
    result='measured_export' if grid<threshold else 'awaiting_export'
    if grid>=threshold:code='flow_mismatch'
  if stopping:result='stopping'
  # A different operation or any missing evidence resets the persistence window.
  key=(code,mode,body.get('native_start')) if code else None
  self.waiting={key:self.waiting.get(key,now)} if key else {}
  if key and now-self.waiting[key]>=90:
   message='Nabíjení je vyžádané, ale nejméně90 sekund se neměří nabíjecí výkon baterie nad100 W.' if code=='charge_mismatch' else 'Prodej je aktivní, ale nejméně90 sekund měnič nepotvrzuje odpovídající dodávku do sítě.'
   alerts.append({'code':code,'level':'warning','message':message})
  return {'measurements':measurements,'alerts':alerts,'operation':{'mode':mode,'label':names.get(mode,'Řízení soláru'),
   'result':result,'reason':str(body.get('reason') or '')[:400],'requested_w':finite(body.get('power_w')),
   'grid_w':grid,'battery_w':battery,'deadline':finite(body.get('deadline')),
   'evidence_notice':'Tok hlásí měnič; skutečný přetok v předávacím místě zatím není nezávisle ověřen.'}}

def finite(value):
 try:
  v=float(value)
  return v if not isinstance(value,bool) and math.isfinite(v) else None
 except (ValueError,TypeError,OverflowError):return None

def evaluate(body,now,started_at=0):
 alerts=[]
 def add(code,level,message):alerts.append({'code':code,'level':level,'message':message})
 if now-started_at>=60 and not body.get('charging_active') and body.get('healthy') is not True:
  add('measurements','error','Měření soláru není čerstvé nebo neprošlo kontrolou; nový prodej musí čekat.')
 if body.get('ready') and now-started_at>=60 and not body.get('charging_active') and finite(body.get('house_power_w')) is None:
  add('house_measurement','warning','Chybí čerstvá spotřeba domu; nelze doložit přebytky panelů ani přesný odhad dostupné energie.')
 if body.get('last_cycle',{}).get('failed'):
  add('cycle_failure','error','Nativní časový konec prodeje se nepotvrdil. Automatický bateriový prodej musí zůstat pozastavený do nového úspěšného ověření.')
 error=body.get('error') or body.get('battery_sale_error') or body.get('native_test_error')
 if error:add('control_error','error','Řízení hlásí: '+str(error)[:240])
 if body.get('settings',{}).get('inhibited'):
  add('inhibited','error','Automatický prodej pozastavila ochrana. Zkontroluj důvod před obnovením.')
 if body.get('ready') and finite(body.get('capacity',{}).get('capacity_kwh')) is None:
  add('capacity','warning','Chybí platná kapacita baterie; odhad energie a rozpočet ručního prodeje nejsou dostupné. Automatický plán stále hlídá měřený stav nabití.')
 sale=body.get('battery_sale') or body.get('native_test') or {}
 start=finite(sale.get('start'));end=finite(sale.get('end') or body.get('deadline'))
 if body.get('active'):
  if end is not None and now>end+90:
   add('overdue','error','Prodej není potvrzeně ukončený ani90 sekund po konci. Řízení musí dokončit ochranné obnovení.')
  if start is not None and now>=start+90 and end is not None and now<end and sale.get('observed') is not True:
   add('no_export','warning','Po začátku bateriového prodeje se nepotvrdila dodávka do sítě.')
 actual=finite(body.get('native_program',{}).get('register_104'));target=finite(body.get('grid_target_w'))
 if not body.get('active') and not body.get('bias_policy',{}).get('enabled') and actual is not None and target is not None and actual!=target:
  add('grid_target','warning',f'Měnič hlásí cíl běžného odběru{actual:g} W místo požadovaných{target:g} W.')
 return alerts

class Changes:
 def __init__(self):self.current={}
 def update(self,alerts):
  current={a['code']:dict(a) for a in alerts}
  added=[a for k,a in current.items() if self.current.get(k)!=a]
  cleared=[k for k in self.current if k not in current]
  self.current=current
  return added,cleared

class Supervisor:
 def __init__(self,hass,clock=time.time,incidents=None):
  self.hass=hass;self.clock=clock;self.started=clock();self.changes=Changes()
  self.pending={};self.notifying=False;self.next_attempt=0;self.notification_error='';self.initial=True
  self.monitor=Monitor(self.started);self.incidents=list(incidents or [])[-20:];self.pending_history=[]
 def publish(self,body):
  now=self.clock();evidence=self.monitor.update(body,now)
  alerts=evaluate(body,now,self.started)+evidence['alerts'];added,cleared=self.changes.update(alerts)
  changes=[{'at':now,'event':'raised',**a} for a in added]+[{'at':now,'event':'cleared','code':code} for code in cleared]
  self.incidents.extend(changes);self.pending_history.extend(changes)
  self.incidents=self.incidents[-20:]
  if self.initial:
   cleared+=list(set(CODES)-{a['code'] for a in alerts});self.initial=False
  for code in cleared:self.pending[code]=None
  for a in added:self.pending[a['code']]=dict(a)
  if self.pending and not self.notifying and now>=self.next_attempt:
   self.notifying=True;self.hass.async_create_task(self._notify())
  state='error' if any(a['level']=='error' for a in alerts) else 'warning' if alerts else 'ready' if body.get('ready') else 'starting'
  result={'version':'1.1.1','status':state,'checked_at':now,'alerts':alerts,'last_cycle':body.get('last_cycle',{}),
          'measurements':evidence['measurements'],'operation':evidence['operation'],'recent_incidents':list(self.incidents),
          'notification_error':self.notification_error,'notification_pending':len(self.pending),
          'notice':'Dohled sleduje důkazy; nenahrazuje nativní ochrany měniče.'}
  self.hass.states.async_set('sensor.jarvis_solar_dohled',state,{'friendly_name':'Dohled nad solárem',**result})
  return result
 async def _notify(self):
  try:
   for code,value in list(self.pending.items()):
    data={'notification_id':'jarvis_solar_'+code}
    if value is not None:data.update(title='Jarvis · solár',message=value['message'])
    try:
     async with asyncio.timeout(4):
      await self.hass.services.async_call('persistent_notification','create' if value is not None else 'dismiss',data,blocking=True)
    except Exception as exc:
     self.notification_error=type(exc).__name__;self.next_attempt=self.clock()+60;return
    if code in self.pending and self.pending[code]==value:self.pending.pop(code)
   self.notification_error=''
  finally:self.notifying=False

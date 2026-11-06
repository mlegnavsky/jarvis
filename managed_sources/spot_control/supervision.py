"""Read-only solar supervision. Notifications never run in the control path."""
import asyncio
import math
import time

CODES=('cycle_failure','house_measurement','measurements','control_error','inhibited','capacity','no_export','overdue','grid_target')

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
  add('house_measurement','error','Chybí čerstvá spotřeba domu; bateriový prodej čeká, aby nebral energii určenou domácnosti.')
 if body.get('last_cycle',{}).get('failed'):
  add('cycle_failure','error','Nativní časový konec prodeje se nepotvrdil. Automatický bateriový prodej musí zůstat pozastavený do nového úspěšného ověření.')
 error=body.get('error') or body.get('battery_sale_error') or body.get('native_test_error')
 if error:add('control_error','error','Řízení hlásí: '+str(error)[:240])
 if body.get('settings',{}).get('inhibited'):
  add('inhibited','error','Automatický prodej pozastavila ochrana. Zkontroluj důvod před obnovením.')
 if body.get('ready') and finite(body.get('capacity',{}).get('capacity_kwh')) is None:
  add('capacity','error','Chybí platná nastavená kapacita baterie; bateriový prodej není povolen.')
 sale=body.get('battery_sale') or body.get('native_test') or {}
 start=finite(sale.get('start'));end=finite(sale.get('end') or body.get('deadline'))
 if body.get('active'):
  if end is not None and now>end+90:
   add('overdue','error','Prodej není potvrzeně ukončený ani90 sekund po konci. Řízení musí dokončit ochranné obnovení.')
  if start is not None and now>=start+90 and end is not None and now<end and sale.get('observed') is not True:
   add('no_export','warning','Po začátku bateriového prodeje se nepotvrdila dodávka do sítě.')
 actual=finite(body.get('native_program',{}).get('register_104'));target=finite(body.get('grid_target_w'))
 if not body.get('active') and actual is not None and target is not None and actual!=target:
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
 def __init__(self,hass,clock=time.time):
  self.hass=hass;self.clock=clock;self.started=clock();self.changes=Changes()
  self.pending={};self.notifying=False;self.next_attempt=0;self.notification_error='';self.initial=True
 def publish(self,body):
  now=self.clock();alerts=evaluate(body,now,self.started);added,cleared=self.changes.update(alerts)
  if self.initial:
   cleared+=list(set(CODES)-{a['code'] for a in alerts});self.initial=False
  for code in cleared:self.pending[code]=None
  for a in added:self.pending[a['code']]=dict(a)
  if self.pending and not self.notifying and now>=self.next_attempt:
   self.notifying=True;self.hass.async_create_task(self._notify())
  state='error' if any(a['level']=='error' for a in alerts) else 'warning' if alerts else 'ready' if body.get('ready') else 'starting'
  result={'version':'1.0.0','status':state,'alerts':alerts,'last_cycle':body.get('last_cycle',{}),
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

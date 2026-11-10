"""Share the existing owned charge transaction; no independent inverter writer."""
import asyncio
import time
import math
from datetime import datetime
from zoneinfo import ZoneInfo

class ChargeLink:
 def __init__(self,hass):self.hass=hass;self.confirmed_start=None;self.flow_lost_since=None
 def controller(self):
  c=self.hass.data.get('jarvis_spot_control')
  if c is None or not callable(getattr(c,'start_heating',None)):raise ValueError('Řízení dobíjení zatím není připravené.')
  return c
 def settings_ready(self):
  try:
   c=self.controller();return c.heating_ready(include_pending=True) and c.healthy()
  except Exception:return False
 def flow_ok(self):
  try:
   c=self.controller();readings={}
   for name in ('battery_power','grid_power','battery'):
    state=self.hass.states.get('sensor.inverter_'+name)
    stamp=(getattr(state,'last_reported',None) or getattr(state,'last_updated',None)) if state else None
    if stamp is None or not c.record.get('power_changed_at',c.record['started_at'])<=stamp.timestamp()<=time.time() or time.time()-stamp.timestamp()>60:return False
    readings[name]=float(state.state)
   if not all(math.isfinite(v) for v in readings.values()):return False
   return readings['grid_power']>100 and (readings['battery_power']<=-max(200,c.record.get('target_w',1000)*.7) or readings['battery']>=c.record['target'])
  except (KeyError,ValueError,TypeError,AttributeError):return False
 def ready(self):
  if not self.settings_ready():return False
  if self.confirmed_start!=self.controller().record.get('started_at'):return False
  if self.flow_ok():self.flow_lost_since=None;return True
  if self.flow_lost_since is None:self.flow_lost_since=time.time()
  return time.time()-self.flow_lost_since<30
 def status(self):
  try:
   c=self.controller();r=c.record
   return {'phase':r.get('phase','idle'),'purpose':r.get('purpose'),'target_w':r.get('target_w'),'heaters':r.get('heaters'),'amps':r.get('amps'),'error':c.error,'observed':c.observed}
  except Exception:return {'phase':'unavailable'}
 async def start(self,heaters=1):
  if self.ready() and self.flow_ok() and self.controller().record.get('heaters',1)==heaters:return
  c=self.controller();now=datetime.now(ZoneInfo('Europe/Prague'))
  previous_change=c.record.get('power_changed_at')
  await c.start_heating(now.hour*60+now.minute,heaters=heaters)
  if c.record.get('power_changed_at')!=previous_change:self.flow_lost_since=None
  try:
   for _ in range(90):
    if not self.settings_ready():raise ValueError('Dobíjení baterie nebo jeho bezpečné nastavení nebylo potvrzeno.')
    if self.flow_ok():
     self.confirmed_start=c.record['started_at'];self.flow_lost_since=None
     c.observed=float(self.hass.states.get('sensor.inverter_battery_power').state)<-200;return
    await asyncio.sleep(1)
   raise ValueError('Měnič nepotvrdil skutečné dobíjení ze sítě; radiátor nezapínám.')
  except BaseException:
   await c.stop();raise
 async def stop(self):
  c=self.controller()
  if c.active and c.record.get('purpose')=='heating':
   await c.stop()
   if c.active:raise ValueError(c.error or 'Obnova nabíjení čeká na potvrzení měniče.')
 async def resize(self,heaters):
  c=self.controller()
  if c.active and c.record.get('purpose')=='heating':
   previous_change=c.record.get('power_changed_at')
   await c.resize_heating(heaters)
   if c.record.get('power_changed_at')!=previous_change:self.flow_lost_since=None

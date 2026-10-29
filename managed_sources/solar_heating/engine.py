"""Pure, persisted two-radiator policy; watts positive for battery discharge."""
import math

ROOMS=('child','living')
DEFAULTS=dict(temp_on=22,temp_off=23.5,child_on_w=1200,child_off_w=1000,living_on_w=3500,living_off_w=3100,battery_on=90,battery_off=85,manual_stop_soc=50,min_off_s=300,living_delay_s=120,discharge_w=300,living_shed_s=120,child_shed_s=240)

def numeric(value):
 return isinstance(value,(float,int)) and not isinstance(value,bool) and math.isfinite(value)

def mean_power(samples, now):
 points=sorted((float(t),float(p)) for t,p in samples if numeric(t) and numeric(p) and t<=now)
 if not points:return None
 start=max(now-300,points[0][0]);area=0;duration=now-start
 if duration<=0:return points[-1][1]
 for i,(t,p) in enumerate(points):
  end=points[i+1][0] if i+1<len(points) else now
  area+=max(0,end-max(t,start))*p
 return area/duration

class Controller:
 def __init__(self,saved=None):
  s=saved or {};self.settings=dict(DEFAULTS);self.configure(s.get('settings',{}));self.samples=s.get('samples',[])
  self.manual={r:bool(s.get('manual',{}).get(r,False)) for r in ROOMS}
  self.off_until={r:float(s.get('off_until',{}).get(r,0)) for r in ROOMS}
  self.on_since={r:float(s.get('on_since',{}).get(r,0)) for r in ROOMS}
  self.full=bool(s.get('full',False));self.demand=bool(s.get('demand',False));self.discharge_since=s.get('discharge_since')
 def configure(self,changes):
  if not isinstance(changes,dict) or set(changes)-set(DEFAULTS):raise ValueError('invalid_settings')
  new={**self.settings,**changes}
  if not all(numeric(v) for v in new.values()):raise ValueError('invalid_settings')
  if not (5<=new['temp_on']<new['temp_off']<=28 and new['temp_off']-new['temp_on']>=.5):raise ValueError('invalid_temperature_settings')
  if not (0<=new['child_off_w']<new['child_on_w']<=new['living_on_w']<=20000 and 0<=new['living_off_w']<new['living_on_w']):raise ValueError('invalid_power_settings')
  if not (20<=new['manual_stop_soc']<new['battery_off']<new['battery_on']<=100):raise ValueError('invalid_battery_settings')
  if not all(60<=new[k]<=3600 for k in ('min_off_s','living_delay_s','living_shed_s','child_shed_s')) or new['child_shed_s']<=new['living_shed_s'] or not 50<=new['discharge_w']<=3000:raise ValueError('invalid_timing_settings')
  self.settings=new
 def dump(self):
  return {k:getattr(self,k) for k in ('settings','samples','manual','off_until','on_since','full','demand','discharge_since')}
 def external(self,room,on,now):
  self.manual[room]=on
  if not on:self.off_until[room]=now+self.settings['min_off_s'];self.on_since[room]=0
  else:self.on_since[room]=now
 def evaluate(self,now,*,temp,pv,soc,discharge,load,child,living):
  cfg=self.settings
  actual={'child':child,'living':living}
  self.samples=[s for s in self.samples if now-600<=s[0]<=now]
  if numeric(pv) and 0<=pv<=50000:
   if self.samples and self.samples[-1][0]==now:self.samples[-1]=[now,pv]
   else:self.samples.append([now,pv])
  # Retain one preceding sample for exact left-edge weighting, bound storage.
  older=[s for s in self.samples if s[0]<now-300]
  self.samples=older[-1:]+[s for s in self.samples if s[0]>=now-300]
  self.samples=self.samples[-2048:]
  average=mean_power(self.samples,now) if numeric(pv) else None
  temp_ok=numeric(temp) and -20<=temp<=60
  energy_ok=all(numeric(v) for v in (pv,soc,discharge,load)) and 0<=soc<=100 and pv>=0 and load>=0
  if not numeric(soc):self.full=False
  elif soc>=cfg['battery_on']:self.full=True
  elif soc<cfg['battery_off']:self.full=False
  if temp_ok:
   if temp<cfg['temp_on']:self.demand=True
   elif temp>=cfg['temp_off']:self.demand=False
  if energy_ok and discharge>cfg['discharge_w'] and not self.full:
   if self.discharge_since is None:self.discharge_since=now
  else:self.discharge_since=None
  elapsed=now-self.discharge_since if self.discharge_since is not None else 0
  out={}
  for room,on_threshold,off_threshold,watts in [('child',cfg['child_on_w'],cfg['child_off_w'],950),('living',cfg['living_on_w'],cfg['living_off_w'],2200)]:
   on=actual[room];desired=on;reason='Čeká na slunce'
   if not temp_ok:
    desired=False;reason='Chybí teplota';self.manual[room]=False
   elif temp>=cfg['temp_off']:
    desired=False;reason='Dosaženo '+str(cfg['temp_off']).replace('.',',')+' °C';self.manual[room]=False
   elif self.manual[room]:
    if not numeric(soc) or soc<=cfg['manual_stop_soc']:
     desired=False;reason='Limit baterie '+str(cfg['manual_stop_soc'])+' %' if numeric(soc) else 'Chybí stav baterie';self.manual[room]=False
    else:desired=True;reason='Ručně'
   elif not self.demand:
    desired=False;reason='Teplota vyhovuje'
   elif not energy_ok:
    desired=False;reason='Chybí energetická data'
   elif on:
    if not self.full and elapsed >= (cfg['living_shed_s'] if room=='living' else cfg['child_shed_s']):
     desired=False;reason='Ochrana baterie'
    elif not self.full and (average is None or average<off_threshold):
     desired=False;reason='Málo slunce'
    else:desired=True;reason='Z baterie' if self.full else 'Ze soláru'
   elif now<self.off_until[room]:desired=False;reason='Pauza po vypnutí'
   elif not self.full and (average is None or average<=on_threshold):desired=False
   elif room=='living' and (not child or now-self.on_since['child']<cfg['living_delay_s']):
    desired=False;reason='Přednost dětského pokoje'
   elif not self.full and (discharge>cfg['discharge_w'] or pv-load<watts):
    desired=False;reason='Čeká na volný výkon'
   else:desired=True;reason='Z baterie' if self.full else 'Ze soláru'
   if on and not desired:
    self.off_until[room]=now+self.settings['min_off_s'];self.on_since[room]=0
   elif desired and not on:
    # Actual on_since is recorded on confirmed state change by HA adapter.
    pass
   out[room]={'on':desired,'reason':reason,'manual':self.manual[room],'actual_on':on}
  out['average']=round(average,1) if average is not None else None
  out['coverage_seconds']=min(300,max(0,now-self.samples[0][0])) if self.samples else 0
  out['full_battery']=self.full
  return out

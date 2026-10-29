"""Pure, persisted two-radiator policy; watts positive for battery discharge."""
import math

ROOMS=('child','living')

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
  s=saved or {};self.samples=s.get('samples',[])
  self.manual={r:bool(s.get('manual',{}).get(r,False)) for r in ROOMS}
  self.off_until={r:float(s.get('off_until',{}).get(r,0)) for r in ROOMS}
  self.on_since={r:float(s.get('on_since',{}).get(r,0)) for r in ROOMS}
  self.full=bool(s.get('full',False));self.demand=bool(s.get('demand',False));self.discharge_since=s.get('discharge_since')
 def dump(self):
  return {k:getattr(self,k) for k in ('samples','manual','off_until','on_since','full','demand','discharge_since')}
 def external(self,room,on,now):
  self.manual[room]=on
  if not on:self.off_until[room]=now+300;self.on_since[room]=0
  else:self.on_since[room]=now
 def evaluate(self,now,*,temp,pv,soc,discharge,load,child,living):
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
  elif soc>=90:self.full=True
  elif soc<85:self.full=False
  if temp_ok:
   if temp<22:self.demand=True
   elif temp>=23.5:self.demand=False
  if energy_ok and discharge>300 and not self.full:
   if self.discharge_since is None:self.discharge_since=now
  else:self.discharge_since=None
  elapsed=now-self.discharge_since if self.discharge_since is not None else 0
  out={}
  for room,on_threshold,off_threshold,watts in [('child',1200,1000,950),('living',3500,3100,2200)]:
   on=actual[room];desired=on;reason='Čeká na slunce'
   if not temp_ok:
    desired=False;reason='Chybí teplota';self.manual[room]=False
   elif temp>=23.5:
    desired=False;reason='Dosaženo 23,5 °C';self.manual[room]=False
   elif self.manual[room]:
    if not numeric(soc) or soc<=50:
     desired=False;reason='Limit baterie 50 %' if numeric(soc) else 'Chybí stav baterie';self.manual[room]=False
    else:desired=True;reason='Ručně'
   elif not self.demand:
    desired=False;reason='Teplota vyhovuje'
   elif not energy_ok:
    desired=False;reason='Chybí energetická data'
   elif on:
    if not self.full and elapsed >= (120 if room=='living' else 240):
     desired=False;reason='Ochrana baterie'
    elif not self.full and (average is None or average<off_threshold):
     desired=False;reason='Málo slunce'
    else:desired=True;reason='Z baterie' if self.full else 'Ze soláru'
   elif now<self.off_until[room]:desired=False;reason='Pauza po vypnutí'
   elif not self.full and (average is None or average<=on_threshold):desired=False
   elif room=='living' and (not child or now-self.on_since['child']<120):
    desired=False;reason='Přednost dětského pokoje'
   elif not self.full and (discharge>300 or pv-load<watts):
    desired=False;reason='Čeká na volný výkon'
   else:desired=True;reason='Z baterie' if self.full else 'Ze soláru'
   if on and not desired:
    self.off_until[room]=now+300;self.on_since[room]=0
   elif desired and not on:
    # Actual on_since is recorded on confirmed state change by HA adapter.
    pass
   out[room]={'on':desired,'reason':reason,'manual':self.manual[room],'actual_on':on}
  out['average']=round(average,1) if average is not None else None
  out['coverage_seconds']=min(300,max(0,now-self.samples[0][0])) if self.samples else 0
  out['full_battery']=self.full
  return out

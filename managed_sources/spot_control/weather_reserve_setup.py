"""Local durable load learning and explanatory reserve snapshots; no device I/O."""
from datetime import datetime,timedelta
import time
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.storage import Store
from .weather_reserve import calculate_reserve,number,TZ
KEY='jarvis_weather_reserve'

async def async_setup_weather_reserve(hass):
 store=Store(hass,1,KEY);saved=await store.async_load() or {}
 days=saved.get('days') or {};verified=saved.get('verified_days_v2') or {};history=saved.get('history') or [];previous=None;error='';last_save=0
 def read(entity,max_age=120):
  state=hass.states.get(entity)
  reported=(getattr(state,'last_reported',None) or getattr(state,'last_updated',None)) if state else None
  if not reported or not -5<=time.time()-reported.timestamp()<=max_age:return None
  return number(state.state)
 def observe():
  nonlocal previous
  now=time.time();day=datetime.fromtimestamp(now,TZ).date().isoformat()
  data=days.setdefault(day,{'counter_kwh':0,'integrated_kwh':0,'covered_seconds':0})
  measured=verified.setdefault(day,{'integrated_kwh':0,'covered_seconds':0})
  counter=read('sensor.inverter_today_load_consumption')
  if counter is not None and 0<=counter<=150:data['counter_kwh']=max(data['counter_kwh'],counter)
  power=read('sensor.jarvis_spotreba_domu',30)
  if power is not None and not 0<=power<=36000:power=None
  if power is not None and previous:
   before,p,old_day=previous;dt=now-before
   if 0<dt<=30 and old_day==day:
    data['integrated_kwh']+=(power+p)/2*dt/3600000;data['covered_seconds']+=dt
    measured['integrated_kwh']+=(power+p)/2*dt/3600000;measured['covered_seconds']+=dt
  previous=(now,power,day) if power is not None else None
  for collection in (days,verified):
   for key in sorted(collection)[:-14]:collection.pop(key,None)
 def snapshot(block,capacity_kwh,owner_floor=60,charge_limit_kw=0):
  observe();now=time.time();local=datetime.fromtimestamp(now,TZ);day=local.date().isoformat();entry=days.get(day,{})
  observed=max(entry.get('counter_kwh',0),entry.get('integrated_kwh',0))
  completed=[]
  for key,data in verified.items():
   if key>=day:continue
   try:
    midnight=datetime.fromisoformat(key).replace(tzinfo=TZ);duration=(midnight+timedelta(days=1)).timestamp()-midnight.timestamp()
    covered=number(data.get('covered_seconds'));energy=number(data.get('integrated_kwh'))
    if covered is not None and .9*duration<=covered<=duration and energy is not None and 0<=energy<=150:completed.append(energy*duration/covered)
   except (ValueError,TypeError):continue
  daily=max([6]+completed)
  state=hass.states.get('sensor.jarvis_pocasi_zitenice')
  weather=dict(state.attributes) if state and state.state=='ready' else {}
  result=calculate_reserve(weather,block,now,capacity_kwh,daily,owner_floor,charge_limit_kw=charge_limit_kw)
  result.update(version='2.0.0',calculated_at=datetime.fromtimestamp(now,TZ).isoformat(),load_source='owner6_and_verified_complete_canonical_days',load_quality='complete_measured_days' if completed else 'owner_baseline',observed_today_house_kwh=round(observed,3),load_covered_hours=round(verified[day]['covered_seconds']/3600,2),learning_days=len(completed),storage_error=error)
  signature=(result.get('forecast_day'),result['required_soc'],result.get('forecast_issued_at'),round(daily,1),block.get('start') if isinstance(block,dict) else None)
  if not history or tuple(history[-1].get('signature',[]))!=signature:
   history.append({'at':result['calculated_at'],'signature':list(signature),'reserve_soc':result['required_soc'],'forecast_day':result.get('forecast_day'),'forecast_pv_kwh':result.get('forecast_pv_kwh'),'forecast_days':result.get('forecast_days',[]),'house_daily_kwh':round(daily,2),'reason':result['reason']})
   del history[:-48]
  result['recent_decisions']=[dict(v) for v in history[-12:]]
  return result
 async def sample(_now=None):
  nonlocal error,last_save
  observe()
  if time.time()-last_save<900:return
  try:await store.async_save({'days':days,'verified_days_v2':verified,'history':history});last_save=time.time();error=''
  except Exception as exc:error=type(exc).__name__
 async_track_time_interval(hass,sample,timedelta(seconds=20))
 observe();hass.data[KEY]={'snapshot':snapshot,'sample':sample}
 return hass.data[KEY]

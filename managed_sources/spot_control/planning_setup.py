"""Read-only archive/forecast adapter. It never commands the inverter."""
import asyncio
from datetime import datetime,timedelta,timezone
import time
from zoneinfo import ZoneInfo
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.storage import Store
from .planning import build_history,reserve_for_home
from .solar_inputs import capacity_basis

KEY='jarvis_house_energy_plan'
TZ=ZoneInfo('Europe/Prague')

async def async_setup_planning(hass):
 store=Store(hass,1,KEY);saved=await store.async_load() or {}
 model=saved.get('model') or {};model_date=saved.get('date');error='';last_attempt=0.;lock=asyncio.Lock()
 def snapshot():
  state=hass.states.get('sensor.jarvis_pocasi_zitenice')
  weather=dict(state.attributes) if state and state.state=='ready' else {}
  setting=hass.states.get('number.inverter_battery_capacity')
  stamp=(getattr(setting,'last_reported',None) or setting.last_updated).timestamp() if setting else None
  ah=setting.state if stamp is not None and 0<=time.time()-stamp<600 else None
  capacity=capacity_basis(ah,None)['capacity_kwh']
  result=reserve_for_home(model,weather,time.time(),capacity_kwh=capacity)
  return {**result,'history_error':error,'model_date':model_date,'complete_days':model.get('complete_days',[]),'model_as_of':model.get('as_of')}
 def busy():
  sales=hass.data.get('jarvis_spot_control_sales',{})
  return any(getattr(sales.get(key),'active',False) for key in ('controller','window'))
 async def refresh(_now=None):
  nonlocal model,model_date,error,last_attempt
  now=time.time();today=datetime.fromtimestamp(now,TZ).replace(hour=0,minute=0,second=0,microsecond=0)
  if busy() or lock.locked() or now-last_attempt<900:return
  if model_date==today.date().isoformat() and model.get('quality')!='insufficient':return
  async with lock:
   last_attempt=now
   read=hass.data.get('jarvis_energy_archive',{}).get('read_window')
   if read is None:error='Plán čeká na energetický archiv.';return
   try:
    windows=[]
    for back in (4,3,2,1):
     if busy():return
     start=today-timedelta(days=back);end=start+timedelta(days=1)
     data=await read(start.timestamp(),end.timestamp())
     if not data.get('complete'):raise ValueError('Incomplete archive window')
     windows.append((start,end,data))
    days=[]
    for index in range(1,len(windows)):
     start,end,data=windows[index]
     previous=windows[index-1][2].get('publications',{}).get('weather',{})
     weather=dict(previous.get('attributes',{}))
     if previous.get('issued_at'):weather.setdefault('fetched_at',previous['issued_at'])
     days.append({'date':start.date().isoformat(),'start':start.timestamp(),'end':end.timestamp(),'samples':data.get('samples',[]),'weather':weather})
    candidate=await hass.async_add_executor_job(build_history,days)
    await store.async_save({'model':candidate,'date':today.date().isoformat()})
    model=candidate;model_date=today.date().isoformat();error=''
   except Exception as exc:
    error='Plán čeká na úplný archiv ('+type(exc).__name__+').'
 result={'snapshot':snapshot,'refresh':refresh}
 hass.data[KEY]=result
 async_track_time_interval(hass,refresh,timedelta(hours=1))
 if hass.is_running:hass.async_create_task(refresh())
 else:hass.bus.async_listen_once('homeassistant_started',refresh)
 return result

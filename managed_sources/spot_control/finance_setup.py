"""Independent five-second accounting. It never writes inverter controls."""
import asyncio
from datetime import datetime,timedelta,timezone
import json
from pathlib import Path
import time
from homeassistant.helpers.event import async_track_time_interval
from .finance import Ledger,archive_points,day_bounds
from .sales import number
KEY='jarvis_energy_finance'

async def async_setup_finance(hass):
 book=await hass.async_add_executor_job(Ledger,Path(hass.config.path('.storage','jarvis_energy_finance.sqlite')))
 lock=asyncio.Lock();history_lock=asyncio.Lock();loaded=False;history_day=None;watermark=None;last_attempt=0.;history_error='';latest={}
 def quote():
  state=hass.states.get('sensor.jarvis_spot_ote')
  return dict(state.attributes) if state else {}
 def point():
  grid=hass.states.get('sensor.inverter_grid_power');now=time.time()
  if not grid:return None
  stamp=(getattr(grid,'last_reported',None) or grid.last_updated).timestamp();power=number(grid.state)
  if power is None or not 0<=now-stamp<=30:return None
  out={'t':stamp,'grid_w':power}
  for kind in ('import','export'):
   state=hass.states.get('sensor.inverter_today_energy_'+kind)
   if not state:continue
   reported=(getattr(state,'last_reported',None) or state.last_updated).timestamp()
   if 0<=now-reported<=120:
    out[kind+'_kwh']=number(state.state)
    out[kind+'_changed']=state.last_changed.timestamp()
  return out
 def write_report(body):
  path=Path(hass.config.path('jarvis_workspace','finance-runtime.json'));path.parent.mkdir(exist_ok=True)
  temp=path.with_suffix('.tmp');temp.write_text(json.dumps(body,ensure_ascii=False,allow_nan=False));temp.replace(path)
 async def capture(_now=None):
  nonlocal latest
  if lock.locked():return
  async with lock:
   try:
    sample=point()
    if sample:await hass.async_add_executor_job(book.add,[sample])
    a=quote();now=time.time()
    rates=hass.data.get('jarvis_spot_control_sales',{}).get('settings',{}).get('rate_history',[])
    body=await hass.async_add_executor_job(book.today,a.get('rows',[]),a.get('rate'),now,a.get('rate_date'),rates)
    if not (loaded and history_day==body['date']):body.update(sale_czk=None,quality='partial')
    body['cash_balance_czk']=body['sale_czk']-body['purchase_czk'] if body['sale_czk'] is not None and body['purchase_czk'] is not None else None
    body['known_cash_balance_czk']=body['known_sale_czk']-body['known_purchase_czk']
    body.update(archive_loaded=loaded and history_day==body['date'],archive_synced_through=watermark,history_error=history_error,live=sample is not None,version='1.1.0')
    latest=body
    common={'date':body['date'],'as_of':body['as_of'],'quality':body['quality'],'rate_date':body['rate_date'],
     'fx_provisional':body['fx_provisional'],'archive_loaded':body['archive_loaded'],'history_error':history_error,
     'import_kwh':body['import_kwh'],'export_kwh':body['export_kwh'],'cash_balance_czk':body['cash_balance_czk'],'known_cash_balance_czk':body['known_cash_balance_czk'],'gap_seconds':body['gap_seconds'],
     'purchase_rate':body['purchase_rate'],'sale_fee':body['sale_fee'],'version':'1.1.0','unit_of_measurement':'CZK','device_class':'monetary','notice':'Průběžný odhad; konečné vyúčtování dle distributora a EnerSpotu.'}
    for id,field,name in [('sensor.jarvis_dnes_nakoupeno_za','purchase_czk','Dnes nakoupeno za'),('sensor.jarvis_dnes_prodano_za','sale_czk','Dnes prodáno za'),('sensor.jarvis_dnes_bilance_site','cash_balance_czk','Dnešní peněžní bilance sítě')]:
     value=body[field]
     hass.states.async_set(id,round(value,2) if value is not None else 'unknown',{'friendly_name':name,**common,'known_sale_czk':body['known_sale_czk'],'unpriced_export_kwh':body['unpriced_export_kwh'],'unaccounted_export_kwh':body['unaccounted_export_kwh']})
    await hass.async_add_executor_job(write_report,{'captured_at':datetime.now(timezone.utc).isoformat(),**body})
   except Exception as exc:
    for id in ('sensor.jarvis_dnes_nakoupeno_za','sensor.jarvis_dnes_prodano_za','sensor.jarvis_dnes_bilance_site'):
     hass.states.async_set(id,'unavailable',{'error':type(exc).__name__,'notice':'Výpočet čeká; uložené záznamy zůstávají zachované.'})
  if not history_lock.locked() and (day_bounds(time.time())[0]!=history_day or time.time()-last_attempt>=60):hass.async_create_task(backfill())
 async def backfill():
  nonlocal loaded,history_day,watermark,last_attempt,history_error
  if history_lock.locked():return
  async with history_lock:
   last_attempt=time.time();read=hass.data.get('jarvis_energy_archive',{}).get('read_window')
   if not read:
    history_error='Čekám na energetický archiv.';return
   try:
    day,start,end=day_bounds(time.time())
    if history_day!=day:loaded=False;watermark=None;history_day=day
    low=start-30 if watermark is None else max(start-30,watermark-60)
    data=await read(low,min(end,time.time()))
    if not data.get('complete'):raise ValueError('Archive window is incomplete')
    points=archive_points(data['samples']);await hass.async_add_executor_job(book.add,points)
    if points:watermark=max(p['t'] for p in points)
    publication=data.get('publications',{}).get('spot',{}).get('attributes',{})
    if not quote().get('rows') and publication:
     await hass.async_add_executor_job(book.remember_prices,day,publication.get('rows',[]),publication.get('rate'),publication.get('rate_date'))
    loaded=True;history_error=''
   except Exception as exc:history_error=type(exc).__name__+': '+str(exc)[:200]
  await capture()
 async def started(_event=None):
  await capture()
 hass.data[KEY]={'ledger':book,'capture':capture,'backfill':backfill,'snapshot':lambda:dict(latest)}
 async_track_time_interval(hass,capture,timedelta(seconds=5))
 if hass.is_running:hass.async_create_task(started())
 else:hass.bus.async_listen_once('homeassistant_started',started)
 return hass.data[KEY]

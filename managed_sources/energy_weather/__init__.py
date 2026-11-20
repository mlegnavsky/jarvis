"""Read-only energy and weather data for the explicitly requested dashboard."""
import asyncio
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import math
import voluptuous as vol
from astral import Observer
from astral.sun import elevation
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_time_interval, async_track_time_change
from .data import parse_ote, ote_url
DOMAIN='jarvis_energy_weather'
VERSION='1.0.1'
CONFIG_SCHEMA=vol.Schema({vol.Optional(DOMAIN):vol.Schema({})},extra=vol.ALLOW_EXTRA)
TZ=ZoneInfo('Europe/Prague')
async def async_setup(hass, config):
 from .retention import setup_retention
 await setup_retention(hass)
 session=async_get_clientsession(hass)
 async def fetch(url, text=False):
  async with session.get(url,timeout=30) as resp:
   resp.raise_for_status()
   return await resp.text() if text else await resp.json(content_type=None)
 async def update(_now=None):
  now=datetime.now(TZ)
  stamp=now.isoformat()
  try:
   txt=await fetch('https://www.cnb.cz/cs/financni_trhy/devizovy_trh/kurzy_devizoveho_trhu/denni_kurz.txt',True)
   rate=next(float(r.split('|')[-1].replace(',','.'))/int(r.split('|')[2]) for r in txt.splitlines() if '|EUR|' in r)
   rate_day=txt.splitlines()[0].split()[0]
   if (now.date()-datetime.strptime(rate_day,'%d.%m.%Y').date()).days>7: raise ValueError('Kurz ČNB je zastaralý')
   rows=[]; tomorrow_error=None
   for delta in (0,1):
    day=(now.date()+timedelta(days=delta)).isoformat()
    try:
     raw=await fetch(ote_url(day))
     rows.extend(parse_ote(raw,day,rate))
    except Exception as exc:
     if not delta: raise
     tomorrow_error=str(exc)
   current=next((r for r in rows if datetime.fromisoformat(r['time'])<=now<datetime.fromisoformat(r['time'])+timedelta(minutes=15)),None)
   if current is None: raise ValueError('Chybí aktuální interval')
   hass.states.async_set('sensor.jarvis_spot_ote',current['price'],{'friendly_name':'Spot OTE · bez DPH','unit_of_measurement':'Kč/kWh','rows':rows,'fetched_at':stamp,'version':VERSION,'source':'OTE denní trh; kurz ČNB','rate':rate,'rate_date':rate_day,'tomorrow_status':tomorrow_error or 'published','contract_price_configured':False,'notice':'Tržní cena bez DPH, před poplatky obchodníka. Kurz ČNB pro zítřek je orientační.'})
  except Exception as exc:
   hass.states.async_set('sensor.jarvis_spot_ote','unavailable',{'friendly_name':'Spot OTE','error':str(exc),'attempted_at':stamp})
  try:
   # Explicit locality requested by user; not the geographic centre of HA's home zone.
   lat,lon=50.555,14.156
   url=f'https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=temperature_2m,relative_humidity_2m,precipitation_probability,precipitation,cloud_cover,wind_speed_10m,shortwave_radiation,weather_code&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,sunrise,sunset&forecast_days=7&timezone=Europe%2FPrague&timeformat=unixtime'
   raw=await fetch(url)
   h=raw['hourly']; d=raw['daily']
   if not h['time'] or max(h['time'])<now.timestamp()+86400: raise ValueError('Předpověď je zastaralá')
   rows=[dict(time=datetime.fromtimestamp(t,TZ).isoformat(),**{k:v[i] for k,v in h.items() if k!='time'}) for i,t in enumerate(h['time'])]
   daily=[dict(time=datetime.fromtimestamp(t,TZ).date().isoformat(),**{k:datetime.fromtimestamp(v[i],TZ).isoformat() if k in ('sunrise','sunset') else v[i] for k,v in d.items() if k!='time'}) for i,t in enumerate(d['time'])]
   observer=Observer(lat,lon)
   start=now.replace(hour=0,minute=0,second=0,microsecond=0).astimezone(timezone.utc)
   end=(now.replace(hour=0,minute=0,second=0,microsecond=0)+timedelta(days=1)).astimezone(timezone.utc)
   sun=[]
   while start<end:
    sun.append({'time':start.astimezone(TZ).isoformat(),'elevation':round(elevation(observer,start),2)})
    start+=timedelta(minutes=15)
   hass.states.async_set('sensor.jarvis_pocasi_zitenice','ready',{'friendly_name':'Žitenice · předpověď','rows':rows,'daily':daily,'sun':sun,'fetched_at':stamp,'version':VERSION,'source':'Open-Meteo Best Match; poloha Slunce Astral','latitude':lat,'longitude':lon,'units':raw.get('hourly_units',{})})
  except Exception as exc:
   hass.states.async_set('sensor.jarvis_pocasi_zitenice','unavailable',{'friendly_name':'Žitenice · předpověď','error':str(exc),'attempted_at':stamp})
 hass.async_create_task(update())
 async def current_interval(_now):
  entity=hass.states.get('sensor.jarvis_spot_ote')
  if entity is None or entity.state=='unavailable': return
  now=datetime.now(TZ)
  if (now-datetime.fromisoformat(entity.attributes['fetched_at'])).total_seconds()>2100:
   hass.states.async_set('sensor.jarvis_spot_ote','unavailable',{'error':'Data jsou zastaralá'})
   return
  current=next((r for r in entity.attributes.get('rows',[]) if datetime.fromisoformat(r['time'])<=now<datetime.fromisoformat(r['time'])+timedelta(minutes=15)),None)
  if current is not None: hass.states.async_set(entity.entity_id,current['price'],dict(entity.attributes))
 async_track_time_change(hass,current_interval,minute='*',second=0)
 async_track_time_interval(hass,update,timedelta(minutes=15))
 return True

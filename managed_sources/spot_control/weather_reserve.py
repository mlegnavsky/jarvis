"""Conservative sale reserve. Pure, no device writes or future storage credit."""
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
import math
TZ=ZoneInfo('Europe/Prague')
PEAK_KWP=10.12
REFERENCE_FACTOR=.8054584854081006
FORECAST_FACTOR=.8
HOUSE_FACTOR=1.25

def number(v):
 if isinstance(v,bool):return None
 try:n=float(v);return n if math.isfinite(n) else None
 except (ValueError,TypeError,OverflowError):return None

def stamp(v):
 try:
  d=datetime.fromisoformat(v)
  return d.timestamp() if d.tzinfo is not None and d.utcoffset() is not None else None
 except (ValueError,TypeError,OverflowError):return None

def calculate_reserve(weather,block,now,capacity_kwh,daily_house_kwh,owner_floor=60):
 now=number(now);capacity=number(capacity_kwh);load=number(daily_house_kwh);owner=number(owner_floor)
 out={'required_soc':100,'quality':'unavailable','reason':'Chybí platná čerstvá předpověď nebo podklady pro rezervu.','forecast_pv_kwh':None,'conservative_pv_kwh':None,'forecast_day':None,'capacity_kwh':capacity,'house_daily_kwh':load,'house_with_margin_kwh':None,'house_margin_percent':25,'forecast_haircut_percent':20,'forecast_factor':REFERENCE_FACTOR,'reference_date':'2026-11-06','reference_quality':'single_day_estimated_bootstrap','forecast_issued_at':None,'forecast_age_seconds':None,'horizon_start':None,'horizon_end':None,'direct_pv_kwh':0,'battery_charge_credit_kwh':0,'intervals':[]}
 if now is None or capacity is None or not 0<capacity<=102.4 or load is None or not 0<=load<=150 or owner is None or not 60<=owner<=95:return out
 if not isinstance(block,dict):return out
 start,end=number(block.get('start')),number(block.get('end'))
 if start is None or end is None or not 0<end-start<=14400 or not now-86400<start<now+172800:return out
 following=(datetime.fromtimestamp(start,TZ).date()+timedelta(days=1)).isoformat()
 out.update(forecast_day=following,horizon_start=end,horizon_end=end+86400,house_with_margin_kwh=load*HOUSE_FACTOR)
 if not isinstance(weather,dict):return out
 issued=stamp(weather.get('fetched_at'));out.update(forecast_issued_at=weather.get('fetched_at'),forecast_age_seconds=now-issued if issued is not None else None)
 if issued is None or not -5<=now-issued<=3600:return out
 rows={}
 for row in weather.get('rows',[]):
  t=stamp(row.get('time')) if isinstance(row,dict) else None
  g=number(row.get('global_tilted_irradiance')) if isinstance(row,dict) else None
  if t is None or t%3600 or t in rows or g is None or not 0<=g<=1600:return out
  rows[t]=g/1000*PEAK_KWP*REFERENCE_FACTOR
 midnight=datetime.fromisoformat(following).replace(tzinfo=TZ);day_end=midnight+timedelta(days=1)
 needed_hours=range(int(midnight.timestamp())+3600,int(day_end.timestamp())+1,3600)
 if any(t not in rows for t in needed_hours):return out
 pv=sum(rows[t] for t in needed_hours);guarded=pv*FORECAST_FACTOR
 padded=load*HOUSE_FACTOR
 tier=60 if guarded>=2*padded else 75 if guarded>=padded else 90 if guarded>=.25*padded else 100
 # Hourly baseline is explicitly approximate; 25% cushion covers ordinary variation.
 # Credit only simultaneous household PV, never assume tomorrow's surplus charges.
 intervals=[];cursor=end;deficit=0;direct_sum=0
 while cursor<end+86400:
  stop=min(end+86400,(math.floor(cursor/3600)+1)*3600);key=(math.floor(cursor/3600)+1)*3600
  if key not in rows:return out
  hours=(stop-cursor)/3600;house=padded/24*hours;production=rows[key]*FORECAST_FACTOR*hours
  direct=min(house,production);direct_sum+=direct;deficit+=(house-direct)/math.sqrt(.9)
  intervals.append({'start':cursor,'end':stop,'house_kwh':round(house,4),'pv_kwh':round(production,4),'direct_pv_kwh':round(direct,4)})
  cursor=stop
 energy_floor=30+deficit/capacity*100
 needed=max(tier,owner,energy_floor)
 reserve=next((v for v in (60,75,90,100) if v>=needed),100)
 reason='Velmi slabá výroba; baterii ponechávám domu.' if tier==100 else 'Rezerva podle výroby dalšího dne, spotřeby domu a25% zásoby.'
 if energy_floor>tier:reason='Vyšší potřeba domu zvyšuje rezervu nad režim počasí.'
 if energy_floor>100:reason='Energie pro dům přesahuje kapacitu; prodej baterie blokován.'
 out.update(required_soc=reserve,quality='estimated',reason=reason,forecast_pv_kwh=round(pv,3),conservative_pv_kwh=round(guarded,3),weather_tier_soc=tier,energy_floor_soc=round(energy_floor,2),owner_floor_soc=owner,direct_pv_kwh=round(direct_sum,3),expected_battery_for_home_kwh=round(deficit,3),intervals=intervals,house_profile='uniform_hourly_estimate_with_25_percent_margin')
 return out

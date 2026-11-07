"""Conservative sale reserve. Pure, chronological48h model with bounded future charging."""
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

def calculate_reserve(weather,block,now,capacity_kwh,daily_house_kwh,owner_floor=60,charge_limit_kw=0):
 now=number(now);capacity=number(capacity_kwh);load=number(daily_house_kwh);owner=number(owner_floor);charge=number(charge_limit_kw)
 out={'required_soc':100,'quality':'unavailable','reason':'Chybí platná čerstvá předpověď nebo podklady pro rezervu.','forecast_pv_kwh':None,'conservative_pv_kwh':None,'forecast_day':None,'forecast_days':[],'capacity_kwh':capacity,'house_daily_kwh':load,'house_with_margin_kwh':None,'house_margin_percent':25,'forecast_haircut_percent':20,'forecast_factor':REFERENCE_FACTOR,'reference_date':'2026-11-06','reference_quality':'single_day_estimated_bootstrap','forecast_issued_at':None,'forecast_age_seconds':None,'horizon_start':None,'horizon_end':None,'direct_pv_kwh':0,'battery_charge_credit_kwh':0,'night_usage_soc':20,'night_with_margin_soc':25,'intervals':[]}
 if now is None or capacity is None or not 0<capacity<=102.4 or load is None or not 0<=load<=150 or owner is None or not 60<=owner<=95:return out
 charge=max(0,min(charge or 0,6))
 if not isinstance(block,dict):return out
 start,end=number(block.get('start')),number(block.get('end'))
 if start is None or end is None or not 0<end-start<=14400 or not now-86400<start<now+172800:return out
 following=datetime.fromtimestamp(start,TZ).date()+timedelta(days=1)
 out.update(forecast_day=following.isoformat(),horizon_start=end,horizon_end=end+172800,house_with_margin_kwh=load*HOUSE_FACTOR,charge_limit_kw=charge)
 if not isinstance(weather,dict):return out
 issued=stamp(weather.get('fetched_at'));out.update(forecast_issued_at=weather.get('fetched_at'),forecast_age_seconds=now-issued if issued is not None else None)
 if issued is None or not -5<=now-issued<=3600:return out
 rows={}
 for row in weather.get('rows',[]):
  t=stamp(row.get('time')) if isinstance(row,dict) else None
  g=number(row.get('global_tilted_irradiance')) if isinstance(row,dict) else None
  if t is None or t%3600 or t in rows or g is None or not 0<=g<=1600:return out
  rows[t]=g/1000*PEAK_KWP*REFERENCE_FACTOR
 # Full-night budget is spread over sunset through sunrise+2h. Missing solar
 # times use an explicit18:00-10:00 assumption, never a whole night per hour.
 solar={d.get('time'):d for d in weather.get('daily',[]) if isinstance(d,dict)}
 eta=math.sqrt(.9);padded=load*HOUSE_FACTOR
 def house_energy(begin,finish):
  base=padded/24;energy=base*(finish-begin)/3600
  first=datetime.fromtimestamp(begin,TZ).date()-timedelta(days=1)
  last=datetime.fromtimestamp(finish,TZ).date()
  for offset in range((last-first).days+1):
   date=first+timedelta(days=offset);nextdate=date+timedelta(days=1)
   setting=stamp(solar.get(date.isoformat(),{}).get('sunset'))
   rising=stamp(solar.get(nextdate.isoformat(),{}).get('sunrise'))
   sunset=setting if setting is not None else datetime.combine(date,datetime.min.time(),TZ).replace(hour=18).timestamp()
   sunrise=rising+7200 if rising is not None else datetime.combine(nextdate,datetime.min.time(),TZ).replace(hour=10).timestamp()
   if 0<sunrise-sunset<=86400:
    overlap=max(0,min(finish,sunrise)-max(begin,sunset))/3600
    night_rate=capacity*.25*eta/((sunrise-sunset)/3600)
    energy+=max(0,night_rate-base)*overlap
  return energy

 forecasts=[]
 for i in range(2):
  date=following+timedelta(days=i);midnight=datetime.combine(date,datetime.min.time(),TZ);day_end=midnight+timedelta(days=1)
  hours=list(range(int(midnight.timestamp())+3600,int(day_end.timestamp())+1,3600))
  if any(t not in rows for t in hours):return out
  pv=sum(rows[t] for t in hours);demand=sum(house_energy(t-3600,t) for t in hours)
  forecasts.append({'day':date.isoformat(),'forecast_pv_kwh':round(pv,3),'conservative_pv_kwh':round(pv*FORECAST_FACTOR,3),'modeled_house_kwh':round(demand,3),'weak':pv*FORECAST_FACTOR<demand})
 weak=sum(d['weak'] for d in forecasts)
 tier=60 if weak==0 else 75 if weak==1 else 100 if all(d['conservative_pv_kwh']<.25*d['modeled_house_kwh'] for d in forecasts) else 90
 intervals=[];cursor=end
 while cursor<end+172800:
  stop=min(end+172800,(math.floor(cursor/3600)+1)*3600);key=(math.floor(cursor/3600)+1)*3600
  if key not in rows:return out
  hours=(stop-cursor)/3600;house=house_energy(cursor,stop);production=rows[key]*FORECAST_FACTOR*hours
  direct=min(house,production);charging=min(max(0,production-house),charge*hours)
  intervals.append({'start':cursor,'end':stop,'house_kwh':house,'pv_kwh':production,'direct_pv_kwh':direct,'charge_kwh':charging,'discharge_dc_kwh':(house-direct)/eta})
  cursor=stop
 floor=capacity*.3;needed=floor;feasible=True
 for row in reversed(intervals):
  needed=max(floor,needed+row['discharge_dc_kwh']-row['charge_kwh']*eta)
  if needed>capacity+1e-8:feasible=False
 energy_floor=needed/capacity*100
 target=max(tier,owner,energy_floor)
 reserve=next((v for v in (60,75,90,100) if v+1e-8>=target),100)
 if not feasible:reserve=100
 energy=capacity*reserve/100;lowest=energy;credit=0;direct_sum=0
 for row in intervals:
  actual_charge=min(row['charge_kwh']*eta,max(0,capacity-energy))
  energy+=actual_charge-row['discharge_dc_kwh'];lowest=min(lowest,energy);credit+=actual_charge;direct_sum+=row['direct_pv_kwh']
  row['battery_soc']=energy/capacity*100
  if energy<floor-1e-8:feasible=False
  for key in list(row):row[key]=round(row[key],4)
 reason='Dva dobré dny; ponechávám základní rezervu.' if tier==60 else 'Slabší den ve dvoudenním výhledu; ponechávám nejméně75 %.' if tier==75 else 'Dva slabé dny; ponechávám nejméně90 %.' if tier==90 else 'Dva velmi slabé dny; baterii ponechávám domu.'
 if energy_floor>tier:reason+=' Noční spotřeba a hodinový průběh zvyšují rezervu.'
 if not feasible:reason='Dvoudenní potřebu nelze bezpečně pokrýt; prodej baterie blokován.';reserve=100
 out.update(required_soc=reserve,quality='estimated',reason=reason,forecast_days=forecasts,forecast_pv_kwh=forecasts[0]['forecast_pv_kwh'],conservative_pv_kwh=forecasts[0]['conservative_pv_kwh'],weather_tier_soc=tier,energy_floor_soc=round(energy_floor,2),owner_floor_soc=owner,direct_pv_kwh=round(direct_sum,3),battery_charge_credit_kwh=round(credit,3),expected_battery_for_home_kwh=round(sum(r['discharge_dc_kwh'] for r in intervals),3),lowest_soc=round(lowest/capacity*100,2),feasible=feasible,intervals=intervals,house_profile='owner6_or_complete_measured_day_and_night20_with_25_percent_margin',night_timing='sunset_to_sunrise_plus2h_or_assumed18_to10',solar_times=[{'time':d.get('time'),'sunrise':d.get('sunrise'),'sunset':d.get('sunset')} for d in solar.values()])
 return out

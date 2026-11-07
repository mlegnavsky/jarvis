"""Five-minute evidence snapshots, not power averages or inferred full days."""
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
import re
try:
 from .supervision import finite,timestamp
except ImportError:
 from supervision import finite,timestamp
TZ=ZoneInfo('Europe/Prague')
COUNTERS={'production':'sensor.inverter_today_production','house':'sensor.inverter_today_load_consumption',
 'import':'sensor.inverter_today_energy_import','export':'sensor.inverter_today_energy_export',
 'battery_charge':'sensor.inverter_today_battery_charge','battery_discharge':'sensor.inverter_today_battery_discharge'}
ELECTRICAL={'pv_w':'sensor.inverter_pv_power','battery_w':'sensor.inverter_battery_power',
 'battery_a':'sensor.inverter_battery_current','battery_v':'sensor.inverter_battery_voltage',
 'battery_c':'sensor.inverter_battery_temperature','inverter_c':'sensor.inverter_temperature',
 'grid_w':'sensor.inverter_grid_power','external_w':'sensor.inverter_external_power',
 'ac_w':'sensor.inverter_power','loss_residual_w':'sensor.inverter_power_losses','soc':'sensor.inverter_battery'}

def date_bounds(day):
 if not isinstance(day,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',day):raise ValueError('Invalid date')
 start=datetime.strptime(day,'%Y-%m-%d').replace(tzinfo=TZ)
 return start.timestamp(),(start+timedelta(days=1)).timestamp()

def daily_snapshot(get,body,finance,now):
 day=datetime.fromtimestamp(now,TZ).date().isoformat();start,_=date_bounds(day)
 def read(entity,age):
  state=get(entity)
  if state is None:return None
  reported=getattr(state,'last_reported',None) or getattr(state,'last_updated',None)
  stamp=reported.timestamp() if isinstance(reported,datetime) else timestamp(reported)
  if stamp is None or not 0<=now-stamp<age:return None
  return finite(state.state)
 energy={key:read(entity,120) for key,entity in COUNTERS.items()}
 # Ignore yesterday's daily counters during midnight reset ambiguity.
 if now-start<120:energy={key:None for key in energy}
 for key,value in energy.items():
  state=get(COUNTERS[key]);changed=getattr(state,'last_changed',None) if state else None
  changed=changed.timestamp() if isinstance(changed,datetime) else timestamp(changed)
  plausible=36*max(0,now-start)/3600+.11
  if value is not None and (value<0 or value>plausible or value>0 and (changed is None or changed<start)):energy[key]=None
 f=None
 if isinstance(finance,dict) and finance.get('date')==day:
  at=finite(finance.get('as_of'))
  if at is not None and 0<=now-at<120:
   f={key:finance.get(key) for key in ('date','as_of','quality','purchase_czk','sale_czk','known_purchase_czk','known_sale_czk','cash_balance_czk','import_kwh','export_kwh','gap_seconds','sale_fee','purchase_rate','history_error')}
 weather=body.get('weather_reserve') or {};plan=body.get('selected_block') or {}
 return {'schema_version':1,'date':day,'as_of':now,'quality':'partial','energy_kwh':energy,
  'electrical':{key:read(entity,30) for key,entity in ELECTRICAL.items()},'finance':f,
  'plan':{key:plan.get(key) for key in ('day','start','end','average_net')},
  'operation':{'active':bool(body.get('active')),'mode':body.get('mode'),'phase':body.get('phase'),'reason':body.get('reason'),'error':body.get('error'),'minimum_soc':body.get('sale_floor_soc'),'completed':body.get('completed_battery_plan')},
  'forecast':{key:weather.get(key) for key in ('forecast_day','forecast_pv_kwh','forecast_issued_at','house_daily_kwh','required_soc','load_quality','learning_days')},
  'notice':'Průběžné denní čítače a okamžité hodnoty po5 minutách; nejde o5minutové průměry ani úplný den. Ztráty jsou bilanční rozdíl, nikoli měřená účinnost.'}

"""Read-only next-day price readiness; never a promise of battery readiness."""
from datetime import datetime,timedelta,time
import math
try:
 from .simple_sales import choose_daily_block,LOCAL
except ImportError:
 from simple_sales import choose_daily_block,LOCAL

def _finite(value):
 if isinstance(value,bool):return None
 try:
  number=float(value)
  return number if math.isfinite(number) else None
 except (TypeError,ValueError,OverflowError):return None

def _quarters(rows,start,end):
 result={}
 for row in rows if isinstance(rows,(list,tuple)) else []:
  if not isinstance(row,dict):continue
  lo=_finite(row.get('start'))
  if lo is None or not start<=lo<end:continue
  hi=_finite(row.get('end'));net=_finite(row.get('net'))
  result.setdefault(lo,[]).append(net if hi==lo+900 else None)
 return result

def _day_plan(rows,day,block_minutes):
 start=datetime.combine(day,time(),LOCAL).timestamp()
 end=datetime.combine(day+timedelta(days=1),time(),LOCAL).timestamp()
 result={'day':day.isoformat(),'status':'waiting_prices','block':None,'block_minutes':block_minutes}
 quarters=_quarters(rows,start,end)
 expected=set(range(int(start),int(end),900))
 if set(quarters)!=expected or any(len(v)!=1 or v[0] is None for v in quarters.values()):return result
 block=choose_daily_block(rows,day.isoformat(),start,block_minutes)
 result.update(status='ready' if block else 'no_window',block=block)
 return result

def build_next_plan(rows,now,block_minutes=120):
 day=datetime.fromtimestamp(now,LOCAL).date()+timedelta(days=1)
 return _day_plan(rows,day,block_minutes)

def valid_prepared_block(block,rows,now,block_minutes=120):
 if not isinstance(block,dict):return False
 start,end,average=(_finite(block.get(k)) for k in ('start','end','average_net'))
 if any(v is None for v in (start,end,average)) or end-start!=block_minutes*60 or now>=end:return False
 day=datetime.fromtimestamp(now,LOCAL).date().isoformat()
 if block.get('day')!=day or datetime.fromtimestamp(start,LOCAL).date().isoformat()!=day:return False
 quarters=_quarters(rows,start,end)
 expected=set(range(int(start),int(end),900))
 if set(quarters)!=expected or any(len(v)!=1 or v[0] is None or v[0]<=0 for v in quarters.values()):return False
 best=_day_plan(rows,datetime.fromtimestamp(now,LOCAL).date(),block_minutes).get('block')
 return (bool(best) and best['start']==start and best['end']==end
         and math.isclose(best['average_net'],average,rel_tol=1e-12,abs_tol=1e-9))

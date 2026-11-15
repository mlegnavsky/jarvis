"""Read one private archive accounting day; no arbitrary entity, URL or writes."""
from datetime import date
import math
import re
from .policy import APIError

NUMBERS=('export_kwh','import_kwh','priced_export_kwh','unpriced_export_kwh',
 'known_sale_czk','sale_czk','known_purchase_czk','purchase_czk','cash_balance_czk',
 'samples','built_at','last_export_measurement','last_import_measurement')

async def read(sup,target):
 if not isinstance(target,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',target):raise APIError(400,'invalid_accounting_date')
 try:date.fromisoformat(target)
 except ValueError:raise APIError(400,'invalid_accounting_date') from None
 state=await sup.request('GET','/core/api/states/sensor.jarvis_energy_archive')
 report=state.get('attributes',{}).get('server',{}).get('finance',{})
 rows=report.get('days',[])
 row=next((r for r in rows[:400] if isinstance(r,dict) and r.get('date')==target),None) if isinstance(rows,list) else None
 day=None
 if row is not None:
  day={'date':target,'quality':row.get('quality') if row.get('quality') in ('estimate','partial') else 'partial',
       'counter_reset':row.get('counter_reset') is True}
  for name in NUMBERS:
   value=row.get(name);day[name]=value if type(value) in (int,float) and math.isfinite(value) else None
 return {'date':target,'status':'available' if day is not None else 'not_available',
  'archive_state':state.get('state') if state.get('state') in ('ready','retrying','uploading','error') else 'unknown',
  'day':day,'source':'authenticated_private_archive_daily_meter_and_quarter_prices',
  'device_writes':False}

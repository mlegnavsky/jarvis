"""Daily cash estimates from dated prices and measured signed grid power.

No integration across missing data. Import is anchored by the daily meter;
export revenue always uses the price of the delivery quarter, never today's
current price for the entire day. The billing authority remains the DSO.
"""
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
import json
import math
import os
try:
 from .journal import Journal
 from .sales import market_rows,number
except ImportError:
 from journal import Journal
 from sales import market_rows,number
TZ=ZoneInfo('Europe/Prague')

def day_bounds(now):
 local=datetime.fromtimestamp(now,TZ);start=local.replace(hour=0,minute=0,second=0,microsecond=0)
 return local.date().isoformat(),start.timestamp(),(start+timedelta(days=1)).timestamp()

def totals(points,quotes,rate,now):
 day,start,end=day_bounds(now);stop=min(end,now)
 prices={}
 for row in market_rows(quotes,rate):
  k=row['start'];prices[k]=None if k in prices else row['net']
 imported=0.;integrated_import=0.;anchor_offset=0.;valid_import=False;valid_export=False;first=None;raw_import=None;raw_export=None;exported=0.;known_sale=0.;unpriced=0.;gaps=0.;export_gaps=0;last=None;counter_export=0.;counter_import=None;reset=False;count=0
 for item in sorted(points,key=lambda p:p['t']):
  t=number(item.get('t'));p=number(item.get('grid_w'))
  if t is None or p is None or t<start-30 or t>stop:continue
  if last and t>last['t']:
   a=max(start,last['t']);b=min(stop,t);duration=t-last['t']
   if b>a and duration<=30:
    cuts=[a,b]
    q=math.floor(a/900)*900+900
    while q<b:cuts.append(q);q+=900
    if last['p']*p<0:
     zero=last['t']-last['p']*duration/(p-last['p'])
     if a<zero<b:cuts.append(zero)
    cuts=sorted(cuts)
    for lo,hi in zip(cuts,cuts[1:]):
     pa=last['p']+(p-last['p'])*(lo-last['t'])/duration
     pb=last['p']+(p-last['p'])*(hi-last['t'])/duration
     inc=(max(0,pa)+max(0,pb))/2*(hi-lo)/3600000
     out=(max(0,-pa)+max(0,-pb))/2*(hi-lo)/3600000
     integrated_import+=inc;imported=integrated_import+anchor_offset;exported+=out
     price=prices.get(math.floor(lo/900)*900)
     if price is None:unpriced+=out
     else:known_sale+=out*price
   elif b>a:
    gaps+=b-a
    if p<0 or last['p']<0:export_gaps+=1
  if t>=start:
   count+=1
   ci=number(item.get('import_kwh'));ce=number(item.get('export_kwh'))
   if first is None:first=t
   # A delayed midnight reset must remove the previous day's anchor, even
   # when that reading is small enough to look physically plausible.
   if ci is not None and raw_import is not None and ci<raw_import-.05:
    if t-start<600:anchor_offset=0.;imported=integrated_import;valid_import=False
    else:reset=True
   if ce is not None and raw_export is not None and ce<raw_export-.05 and t-start<600:
    counter_export=0.;valid_export=False
   plausible=25*max(0,t-start)/3600+.11
   def valid_counter(value,kind):
    changed=number(item.get(kind+'_changed'))
    if value is None or not 0<=value<=plausible:return False
    if value==0:return True
    if t-start<120:return False
    if changed is not None and changed<start:return False
    return True
   if valid_counter(ci,'import'):
    valid_import=True;counter_import=ci
    anchor_offset=max(anchor_offset,ci-integrated_import)
    imported=integrated_import+anchor_offset
   if valid_counter(ce,'export'):
    counter_export=max(counter_export,ce);valid_export=True
   if ci is not None:raw_import=ci
   if ce is not None:raw_export=ce
  elif t<start:
   raw_import=number(item.get('import_kwh'));raw_export=number(item.get('export_kwh'))
  last={'t':t,'p':p}
 full_coverage=first is not None and first<=start+30 and gaps==0 and count>=2
 unaccounted=counter_export if exported<1e-9 and counter_export>0 else max(0,counter_export-exported-.100001)
 complete=unpriced<1e-9 and unaccounted<1e-9 and export_gaps==0 and (valid_export or full_coverage)
 return {'date':day,'purchase_czk':imported*5 if count and (valid_import or full_coverage) and not reset else None,'known_purchase_czk':imported*5,
  'sale_czk':known_sale if count and complete else None,'known_sale_czk':known_sale,
  'import_kwh':imported,'export_kwh':exported,'unpriced_export_kwh':unpriced,
  'unaccounted_export_kwh':unaccounted,'missing_export_periods':export_gaps,
  'gap_seconds':gaps,'counter_reset':reset,'samples':count,'as_of':last['t'] if last else None,
  'quality':'estimate' if complete and (valid_import or full_coverage) and not reset else 'partial','purchase_rate':5,'sale_fee':.30}

class Ledger(Journal):
 def __init__(self,path):
  super().__init__(path)
  with self.db() as db:
   db.execute('CREATE TABLE IF NOT EXISTS points(t REAL PRIMARY KEY,grid_w REAL NOT NULL,import_kwh REAL,export_kwh REAL,import_changed REAL,export_changed REAL)')
   columns={r[1] for r in db.execute('PRAGMA table_info(points)')}
   for name in ('import_changed','export_changed'):
    if name not in columns:db.execute('ALTER TABLE points ADD COLUMN '+name+' REAL')
   db.execute('CREATE TABLE IF NOT EXISTS pricebooks(day TEXT PRIMARY KEY,body TEXT NOT NULL)')
  os.chmod(self.path,0o600)
 def add(self,points):
  rows=[]
  for p in points:
   t=number(p.get('t'));w=number(p.get('grid_w'))
   if t is not None and t>=0 and w is not None:rows.append((t,w,number(p.get('import_kwh')),number(p.get('export_kwh')),number(p.get('import_changed')),number(p.get('export_changed'))))
  with self.db() as db:db.executemany('INSERT INTO points VALUES(?,?,?,?,?,?) ON CONFLICT(t) DO UPDATE SET import_kwh=COALESCE(points.import_kwh,excluded.import_kwh),export_kwh=COALESCE(points.export_kwh,excluded.export_kwh),import_changed=COALESCE(points.import_changed,excluded.import_changed),export_changed=COALESCE(points.export_changed,excluded.export_changed)',rows)
 def remember_prices(self,day,rows,rate,rate_date=None):
  body={'rows':rows,'rate':rate,'rate_date':rate_date}
  valid=[r for r in market_rows(rows,rate) if datetime.fromtimestamp(r['start'],TZ).date().isoformat()==day]
  if not valid:return
  encoded=json.dumps(body,sort_keys=True,allow_nan=False)
  with self.db() as db:
   old=db.execute('SELECT body FROM pricebooks WHERE day=?',(day,)).fetchone()
   if not old or old[0]!=encoded:db.execute('INSERT OR REPLACE INTO pricebooks VALUES(?,?)',(day,encoded))
 def today(self,quotes,rate,now,rate_date=None):
  day,start,end=day_bounds(now)
  self.remember_prices(day,quotes,rate,rate_date)
  with self.db() as db:
   rows=db.execute('SELECT t,grid_w,import_kwh,export_kwh,import_changed,export_changed FROM points WHERE t>=? AND t<=? ORDER BY t',(start-30,min(now,end))).fetchall()
   book=db.execute('SELECT body FROM pricebooks WHERE day=?',(day,)).fetchone()
  price=json.loads(book[0]) if book else {'rows':[],'rate':None,'rate_date':None}
  out=totals([dict(zip(('t','grid_w','import_kwh','export_kwh','import_changed','export_changed'),r)) for r in rows],price['rows'],price['rate'],now)
  stamp=price.get('rate_date')
  try:fxday=datetime.strptime(stamp,'%d.%m.%Y').date().isoformat()
  except (ValueError,TypeError):fxday=stamp
  return {**out,'rate':price['rate'],'rate_date':stamp,'fx_provisional':fxday!=day}

def archive_points(samples):
 result=[]
 for sample in samples:
  values=sample.get('values',{});grid=values.get('sensor.inverter_grid_power',{})
  try:t=datetime.fromisoformat(grid['source_updated']).timestamp()
  except (TypeError,ValueError,KeyError):continue
  captured=number(sample.get('t'));power=number(grid.get('value'))
  if captured is None or power is None or not 0<=captured-t<=30:continue
  out={'t':t,'grid_w':power}
  for kind in ('import','export'):
   item=values.get('sensor.inverter_today_energy_'+kind,{})
   try:stamp=datetime.fromisoformat(item['source_updated']).timestamp()
   except (TypeError,ValueError,KeyError):continue
   if 0<=captured-stamp<=120:out[kind+'_kwh']=number(item.get('value'))
   try:out[kind+'_changed']=datetime.fromisoformat(item['source_changed']).timestamp()
   except (TypeError,ValueError,KeyError):pass
  result.append(out)
 return result

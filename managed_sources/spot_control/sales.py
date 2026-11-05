"""Deterministic sales policy. Power targets never claim unmeasured PV headroom."""
from datetime import datetime
import math

EXPORT_LIMIT=9300
CONTRACT_LIMIT=9500
SALE_RESERVE=60

def after_stop(settings,outcome):
 result=dict(settings)
 result['handled_stop_id']=outcome.get('id')
 reason=outcome.get('reason')
 normal=reason in ('deadline','manual','price','reserve') or reason=='recovery' and outcome.get('purpose')=='automatic' and outcome.get('stop_verified')
 if not normal:
  result.update(automatic=False,inhibited=True)
 if reason=='manual':result.update(automatic=False,commission_cancelled=True)
 complete=(reason=='deadline' and outcome.get('purpose')=='commission' and outcome.get('mode')=='pv'
  and outcome.get('observed') and outcome.get('sustained') and outcome.get('stop_verified') and not result.get('commission_cancelled'))
 if complete:
  result['pv_verified']=True
  if outcome.get('promote_auto'):result['automatic']=True
 return result

def number(value):
 try:
  value=float(value)
  return value if math.isfinite(value) else None
 except (TypeError,ValueError):return None

def market_rows(rows,rate):
 rate=number(rate)
 if rate is None or rate<=0:return []
 result=[]
 for row in rows:
  try:
   date=datetime.fromisoformat(row['time'])
   if date.tzinfo is None:continue
   start=date.timestamp(); eur=number(row.get('eur_mwh'))
   if eur is None:continue
   result.append({'start':start,'end':start+900,'eur_mwh':eur,'gross':eur*rate/1000,'net':eur*rate/1000-.30})
  except (KeyError,TypeError,ValueError,OverflowError):continue
 return sorted(result,key=lambda r:r['start'])

def price_at(rows,now,rate):
 matches=[r for r in market_rows(rows,rate) if r['start']<=now<r['end']]
 return matches[0] if len(matches)==1 else None

def decide(soc,price,future,now,required_soc=60,capacity_kwh=23.5):
 soc=number(soc);reserve=number(required_soc)
 hold={'mode':'hold','power_w':0,'minimum_soc':max(60,reserve or 60),'reason':'Čekám na aktuální cenu a stav baterie.'}
 if soc is None or not 0<=soc<=100 or price is None or number(price.get('net')) is None:return hold
 if not price['start']<=now<price['end'] or price['net']<=0:
  return {**hold,'reason':'Výkup po poplatku není kladný nebo chybí aktuální interval.'}
 if reserve is None or not 0<=reserve<=100:return hold
 reserve=max(60,reserve)
 # A small SOC margin protects the sale floor between native reports.
 floor=min(100,reserve+2)
 budget=max(0,(soc-floor)/100*capacity_kwh*math.sqrt(.90))
 later=[r for r in future if r.get('start',0)>=price['end'] and r.get('end',0)>now and number(r.get('net')) is not None]
 # Conservative battery threshold: alternative household supply5 + wear.5 + margin.5.
 # This is a policy assumption; PV overflow does not inherit a5 Kč acquisition cost.
 if soc>floor and price['net']>=6 and not any(r['net']>price['net'] for r in later):
  remaining=(price['end']-now)/3600
  power=min(EXPORT_LIMIT,int(budget/max(remaining,1/3600)*1000))
  if power>=100:
   return {'mode':'battery','power_w':power,'minimum_soc':floor,'budget_kwh':budget,'reason':'Výhodný interval · dostupná baterie nad rezervou.'}
 if soc>=98:
  return {'mode':'pv','power_w':EXPORT_LIMIT,'minimum_soc':floor,'available_pv_w':None,'reason':'Baterie je téměř plná · povoluji dostupné přebytky panelů.'}
 return {**hold,'reason':'Energii ponechávám domu nebo na výhodnější interval.','minimum_soc':floor}

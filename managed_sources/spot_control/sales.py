"""Deterministic sales policy. Power targets never claim unmeasured PV headroom."""
from datetime import datetime
import math
import time

EXPORT_LIMIT=9300
CONTRACT_LIMIT=9500
SALE_RESERVE=60

def measurement_guard(outcome):
 failures=outcome.get('failures') or []
 # A completed retry may retain a timeout of an earlier restoration write.
 # Recovery still independently audits the complete idle native profile.
 known_retry=outcome.get('reason')=='stop_recovery' and all(isinstance(f,str) and any(f.startswith(prefix) for prefix in (
  'number.inverter_export_surplus_power: ','select.inverter_work_mode: ','switch.inverter_export_surplus: ')) for f in failures)
 return (outcome.get('purpose') in ('automatic','manual') and outcome.get('reason') in ('guard','stop_recovery')
  and outcome.get('stop_verified') is True and not outcome.get('conflicts') and (not failures or known_retry)
  and (outcome.get('context') or {}).get('triggers')==['measurement_or_health'])

def restore_measurement_intent(settings,events):
 result=dict(settings)
 if not settings.get('requested_automatic'):return result
 stops=[e.get('payload',{}) for e in events if e.get('kind')=='sale_stop']
 if not stops or stops[-1].get('id')!=settings.get('handled_stop_id') or not measurement_guard(stops[-1]):return result
 result['measurement_recovery']={'pending':True,'stop_id':stops[-1]['id']}
 probes=[p for p in stops[:-1] if p.get('purpose')=='bias_probe' and p.get('mode')=='bias']
 if probes and after_stop({'bias_verified':False},probes[-1]).get('bias_verified'):result['bias_verified']=True
 return result

def after_stop(settings,outcome):
 result=dict(settings)
 result['handled_stop_id']=outcome.get('id')
 result['last_sale_stop']=dict(outcome)
 result['recent_sale_stops']=[*(settings.get('recent_sale_stops') or [])[-9:],dict(outcome)]
 recover=bool(settings.get('requested_automatic') and measurement_guard(outcome))
 if recover:result['measurement_recovery']={'pending':True,'stop_id':outcome.get('id')}
 reason=outcome.get('reason')
 # A fully confirmed cleanup retry preserves a normal automatic PV stop.
 # Unconfirmed restoration, owner conflicts and safety guards still inhibit.
 if reason=='stop_recovery' and outcome.get('purpose')=='automatic' and outcome.get('mode')=='pv' and outcome.get('stop_verified') is True and not outcome.get('conflicts') and outcome.get('original_reason') in ('recovery','deadline','no_surplus','house_support','price','reserve'):
  reason=outcome['original_reason']
 no_surplus=reason in ('no_surplus','house_support') and outcome.get('mode')=='pv' and outcome.get('stop_verified')
 if no_surplus:result['cooldown_until']=time.time()+30
 normal=no_surplus or reason in ('deadline','manual','price','reserve') or reason=='recovery' and outcome.get('purpose')=='automatic' and outcome.get('stop_verified')
 if outcome.get('conflicts'):normal=False
 if not normal:
  result.update(automatic=False,inhibited=True)
 if reason=='manual':result.update(automatic=False,commission_cancelled=True)
 if outcome.get('mode')=='bias':
  verified=(reason=='deadline' and outcome.get('purpose')=='bias_probe' and outcome.get('power_w')==2 and outcome.get('minimum_soc')==30
   and all(outcome.get(k) is True for k in ('observed','sustained','stop_verified')) and not outcome.get('conflicts'))
  if outcome.get('purpose')=='bias_probe':
   result.update(bias_verified=verified,automatic=False,inhibited=not verified)
   if not verified:result['inhibited']=True
  elif not normal and not recover:result['bias_verified']=False
 complete=(reason=='deadline' and outcome.get('purpose')=='commission' and outcome.get('mode')=='pv'
  and not outcome.get('conflicts') and outcome.get('observed') and outcome.get('sustained') and outcome.get('stop_verified') and not result.get('commission_cancelled'))
 if complete:
  result['pv_verified']=True
  if outcome.get('promote_auto'):result['automatic']=True
 return result

def number(value):
 try:
  value=float(value)
  return value if math.isfinite(value) else None
 except (TypeError,ValueError):return None

def market_rows(rows,rate,fee=.30):
 rate=number(rate)
 if rate is None or rate<=0:return []
 result=[]
 for row in rows:
  try:
   date=datetime.fromisoformat(row['time'])
   if date.tzinfo is None:continue
   start=date.timestamp(); eur=number(row.get('eur_mwh'))
   if eur is None:continue
   result.append({'start':start,'end':start+900,'eur_mwh':eur,'gross':eur*rate/1000,'net':eur*rate/1000-fee})
  except (KeyError,TypeError,ValueError,OverflowError):continue
 return sorted(result,key=lambda r:r['start'])

def price_at(rows,now,rate,fee=.30):
 matches=[r for r in market_rows(rows,rate,fee) if r['start']<=now<r['end']]
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
 if soc>=97:
  return {'mode':'pv','power_w':EXPORT_LIMIT,'minimum_soc':floor,'available_pv_w':None,'reason':'Baterie je téměř plná · povoluji dostupné přebytky panelů.'}
 return {**hold,'reason':'Energii ponechávám domu nebo na výhodnější interval.','minimum_soc':floor}

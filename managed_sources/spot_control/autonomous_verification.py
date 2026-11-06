"""Pure admission and completion for owner-requested HA verification."""
from datetime import datetime
from zoneinfo import ZoneInfo
try:
 from .solar_inputs import finite
 from .native_plan import next_native_start
except ImportError:
 from solar_inputs import finite
 from native_plan import next_native_start

TZ=ZoneInfo('Europe/Prague')

def candidate(settings,state,quotes,now):
 def wait(reason):return {'due':False,'state':'waiting','reason':reason}
 if not settings.get('automatic') or settings.get('inhibited'):return wait('Automatika je vypnutá nebo ji pozastavila ochrana.')
 if not state.get('ready') or not state.get('healthy') or state.get('charging') or state.get('pending_stop'):
  return wait('Ověření čeká na čerstvé zdravé měření a dokončenou obnovu.')
 if state.get('active_kind') not in (None,'bias'):return wait('Nejprve doběhne současný prodej nebo nabíjení.')
 price=finite(state.get('net_price'));soc=finite(state.get('soc'))
 if price is None or soc is None:return wait('Chybí aktuální cena nebo nabití baterie.')
 a=settings.get('auto_verification') or {};local=datetime.fromtimestamp(now,TZ);day=local.date().isoformat()
 attempts=(finite(a.get('attempts')) or 0) if a.get('day')==day else 0
 if attempts>=2:return wait('Dnešní limit dvou ověřovacích pokusů je vyčerpán; další může proběhnout zítra.')
 if (finite(a.get('not_before')) or 0)>now:return wait('Čekám na odstup po neprůkazném nebo přerušeném ověření.')
 if settings.get('bias_enabled') and not settings.get('bias_verified'):
  if soc<32:return wait('Malý přetok čeká na alespoň32 % baterie.')
  return {'due':True,'state':'due','kind':'bias','power_w':2,'minutes':3,'minimum_soc':30,'day':day,'attempts':int(attempts),'reason':'HA samo ověří malý přetok.'}
 if settings.get('battery_verified'):return wait('Potřebná ověření jsou hotová; HA řídí běžný provoz.')
 pv=finite(state.get('pv_w'));capacity=finite(state.get('capacity_kwh'))
 if price<=0:return wait('Bateriové ověření čeká na kladný výkup.')
 if pv is None or pv>1700:return wait('Bateriové ověření čeká na výrobu panelů nejvýše1,7 kW, aby měření prokázalo použití baterie.')
 if (finite(state.get('pv_low_seconds')) or 0)<120:return wait('Čekám, až nižší výroba panelů vydrží alespoň dvě minuty.')
 if soc<63 or capacity is None or capacity<=0 or capacity*max(0,soc-60)/100<.3:
  return wait('Bateriové ověření čeká na dostatek energie nad rezervou60 %.')
 start=next_native_start(local,now)
 if start.timestamp()-now<120 or start.date()!=local.date() or start.hour*60+start.minute+15>=1435:
  return wait('Čekám na dostatečný čas k bezpečné přípravě nativního okna.')
 quarter=start.timestamp()//900*900;end=start.timestamp()+360
 while quarter<=end:
  matches=[q for q in quotes if isinstance(q,dict) and finite(q.get('start'))==quarter and finite(q.get('end'))==quarter+900]
  if len(matches)!=1 or finite(matches[0].get('net')) is None or finite(matches[0].get('net'))<=0:
   return wait('Chybí jednoznačné kladné ceny přes celý test a ukončení.')
  quarter+=900
 return {'due':True,'state':'due','kind':'battery','power_w':2000,'minutes':5,'minimum_soc':60,'day':day,'attempts':int(attempts),'reason':'HA samo ověří bateriový prodej a nativní konec.'}

def finish(settings,proof,accepted,now):
 result=dict(settings)
 if not settings.get('verification_resume_auto'):return result
 a=dict(settings.get('auto_verification') or {});result['verification_resume_auto']=False
 if settings.get('requested_automatic') is False:
  result.update(automatic=False);return result
 if accepted is True:
  result.update(automatic=True,inhibited=False);a.update(state='verified',reason='Ověření dokončeno; HA obnovilo automatický provoz.')
 else:
  inconclusive=(proof.get('stop_verified') is True and not proof.get('conflicts') and
   (proof.get('reason') in ('recovery','price','reserve') or proof.get('reason')=='deadline' and proof.get('observed') is not True))
  if a.get('kind')=='battery' and inconclusive:
   result.update(automatic=True,inhibited=False);a.update(state='waiting',not_before=now+1800,reason='Obnova je potvrzená; bateriový důkaz zatím chybí. HA počká na další vhodné podmínky.')
  else:
   result.update(automatic=False,inhibited=True);a.update(state='failed',reason='Ověření neprošlo. Prodej je zastavený; HA provedlo ochrannou obnovu a hlásí chybu.')
 result['auto_verification']=a
 return result

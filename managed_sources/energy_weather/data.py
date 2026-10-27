from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
TZ = ZoneInfo('Europe/Prague')
def parse_ote(raw, day, rate):
 expected=datetime.fromisoformat(day).strftime('%d.%m.%Y')
 if expected not in raw.get('graph',{}).get('title',''):
  raise ValueError('OTE zatím nezveřejnilo požadovaný den')
 start=datetime.fromisoformat(day).replace(tzinfo=TZ).astimezone(timezone.utc)
 end=(datetime.fromisoformat(day)+timedelta(days=1)).replace(tzinfo=TZ).astimezone(timezone.utc)
 n=int((end-start).total_seconds()/900)
 lines=[x for x in raw['data']['dataLine'] if x['title']=='15min cena (EUR/MWh)']
 if len(lines)!=1 or len(lines[0]['point'])!=n: raise ValueError('Neúplná čtvrthodinová data OTE')
 points=lines[0]['point']
 if [int(p['x']) for p in points]!=list(range(1,n+1)): raise ValueError('Nesprávné intervaly OTE')
 return [{'time':(start+timedelta(minutes=15*i)).astimezone(TZ).isoformat(),'price':round(float(p['y'])*rate/1000,6),'eur_mwh':float(p['y'])} for i,p in enumerate(points)]

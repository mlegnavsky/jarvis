"""Read every page of an immutable-time archive day; never silently truncate."""
import math

async def fetch_day(read,start,end):
 cursor=start;result={'samples':[],'publications':{},'complete':False}
 for _ in range(16):
  page=await read(cursor,end);rows=page.get('samples')
  if not isinstance(rows,list):raise ValueError('Invalid archive samples')
  publications=page.get('publications',{})
  if publications==[]:publications={}
  if not isinstance(publications,dict):raise ValueError('Invalid archive publications')
  if not result['publications']:result['publications']=publications
  previous=cursor
  for index,row in enumerate(rows):
   values=row.get('values',{})
   if values==[]:row={**row,'values':{}};rows[index]=row
   elif not isinstance(values,dict):raise ValueError('Invalid archive values')
   stamp=float(row['t'])
   if not math.isfinite(stamp) or stamp<cursor or stamp>=end or index and stamp<=previous:raise ValueError('Archive page did not advance')
   previous=stamp
  result['samples'].extend(rows)
  if len(rows)<10000:
   result['complete']=True;return result
  cursor=math.nextafter(previous,math.inf)
 raise ValueError('Archive day exceeds safe page budget; completeness not confirmed')

async def fetch_window(read,start,end):
 """Bound response memory on the PHP server as well as in the HA client."""
 if not math.isfinite(start) or not math.isfinite(end) or not 0<end-start<=90060:raise ValueError('Invalid archive window')
 cursor=start;result={'samples':[],'publications':{},'complete':False}
 while cursor<end:
  stop=min(end,cursor+900)
  data=await fetch_day(read,cursor,stop)
  result['samples'].extend(data['samples']);result['publications'].update(data['publications'])
  cursor=stop
 result['complete']=True
 return result

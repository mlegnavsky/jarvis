"""Read every page of an immutable-time archive day; never silently truncate."""
import math

async def fetch_day(read,start,end):
 cursor=start;result={'samples':[],'publications':{},'complete':False}
 for _ in range(16):
  page=await read(cursor,end);rows=page.get('samples')
  if not isinstance(rows,list):raise ValueError('Invalid archive samples')
  if not result['publications']:result['publications']=page.get('publications',{})
  previous=cursor
  for index,row in enumerate(rows):
   stamp=float(row['t'])
   if not math.isfinite(stamp) or stamp<cursor or stamp>=end or index and stamp<=previous:raise ValueError('Archive page did not advance')
   previous=stamp
  result['samples'].extend(rows)
  if len(rows)<10000:
   result['complete']=True;return result
  cursor=math.nextafter(previous,math.inf)
 raise ValueError('Archive day exceeds safe page budget; completeness not confirmed')

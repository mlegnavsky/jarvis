"""A read-only native snapshot holds the existing Solarman transport once."""
import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo

CHUNKS=((0,1),(98,14),(130,1),(142,36),(212,8),(62,3))

async def read_snapshot(device,timeout_seconds=25):
 modbus=getattr(device,'modbus',None)
 lock=getattr(modbus,'_semaphore',None);response=getattr(modbus,'get_response',None)
 if lock is None or not callable(response):raise ValueError('Atomic native transport unavailable')
 registers={};address=count=0
 try:
  async with asyncio.timeout(timeout_seconds):
   async with lock:
    for address,count in CHUNKS:
     raw=await response(3,address,count=count)
     if not isinstance(raw,list) or len(raw)!=count or any(type(v) is not int or not 0<=v<=65535 for v in raw):
      raise ValueError(f'Incomplete native snapshot at{address}/{count}')
     registers.update({address+i:v for i,v in enumerate(raw)})
 except TimeoutError as exc:raise TimeoutError(f'Native snapshot timeout at{address}/{count}') from exc
 values=[registers[i] for i in (62,63,64)]
 date=datetime(2000+(values[0]>>8),values[0]&255,values[1]>>8,values[1]&255,values[2]>>8,values[2]&255,tzinfo=ZoneInfo('Europe/Prague'))
 return {'clock':date,'registers':registers}

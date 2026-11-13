"""Fixed native grid-bias maintenance; never changes modes or export limits."""
import asyncio
import time

GRID_TARGET_W=1


def _value(raw,count):
 if not isinstance(raw,list) or len(raw)!=count or any(type(v)is not int or not 0<=v<=65535 for v in raw):raise ValueError('Incomplete native zero-target read')
 return raw

async def _snapshot(response):
 r={}
 for a,n in ((0,1),(98,14),(130,1),(142,36)):
  raw=_value(await response(3,a,count=n),n);r.update({a+i:v for i,v in enumerate(raw)})
 soc=[r[166+i] for i in range(6)]
 if r[0] not in (5,1280) or (r[98],r[111],r[130],r[142],r[145],r[146])!=(1,1,0,2,0,255) or len(set(soc))!=1 or not 0<soc[0]<60 or any(r[172+i]!=0 for i in range(6)):
  raise ValueError('Zero target requires the inactive ordinary house program')
 return r

async def set_zero_target(device,ready,event,now=time.time,sleep=asyncio.sleep):
 """Only104=GRID_TARGET_W, with serialized native admission and delayed proof.

 ready() must prove healthy measurements and exclusive inactive controller
 ownership. The caller holds its application lock for the entire operation.
 """
 result={'supported':False,'verified':False,'target_w':GRID_TARGET_W,'before_w':None,'actual_w':None,'reads':[],'read_shapes':[],'error':None}
 modbus=getattr(device,'modbus',None);semaphore=getattr(modbus,'_semaphore',None);response=getattr(modbus,'get_response',None)
 if semaphore is None or not callable(response) or not callable(getattr(device,'execute',None)):
  result['error']='Unsupported native zero-target transport';return result
 result['supported']=True
 try:
  async with asyncio.timeout(25):
   if ready() is not True:raise ValueError('Fresh healthy idle control is required')
   async with semaphore:
    before=await _snapshot(response);result['before_w']=before[104]
    await event('native_zero_target_intent',{'before_w':before[104],'target_w':GRID_TARGET_W})
    current=await _snapshot(response)
    if current!=before or ready() is not True:raise ValueError('Native settings or control changed during zero-target audit')
    await response(16,104,data=[GRID_TARGET_W])
    await sleep(1)
    result['reads'].append(_value(await response(3,104,count=1),1)[0])
   for delay in (3,5):
    await sleep(delay)
    async with semaphore:
     first=_value(await response(3,104,count=1),1)[0]
     bulk=_value(await response(3,98,count=14),14)[6]
     last=_value(await response(3,104,count=1),1)[0]
    result['read_shapes'].append({'captured_at':now(),'single_before':first,'bulk':bulk,'single_after':last})
    result['reads'].extend((first,bulk,last))
    result['actual_w']=bulk
   result['verified']=all(v==GRID_TARGET_W for v in result['reads']) and ready() is True
   result['error']=None if result['verified'] else 'Native zero target did not remain confirmed'
   result['captured_at']=now()
 except Exception as exc:result['error']=type(exc).__name__+': '+str(exc)
 return result

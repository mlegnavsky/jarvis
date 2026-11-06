"""Pure production rules. This module cannot call HA or write inverter settings."""
import math
import json
from datetime import datetime
from zoneinfo import ZoneInfo


def finite(value):
 if isinstance(value,bool):return None
 try:
  value=float(value);return value if math.isfinite(value) else None
 except (ValueError,TypeError,OverflowError):return None


def block_key(block):
 day=block.get('day') or datetime.fromtimestamp(block['start'],ZoneInfo('Europe/Prague')).date().isoformat()
 return json.dumps([day,float(block["start"]),float(block["end"])],separators=(",",":"))


def completed_selection(block,day,now):
 return isinstance(block,dict) and block.get('day')==day and finite(block.get('end')) is not None and now>=block['end']


def home_profile(registers,floor=30):
 """Check the existing ordinary program. Never migrate or repair it implicitly."""
 expected={0:(5,1280),98:(1,),111:(1,),130:(0,),142:(2,),145:(0,),146:(255,)}
 expected.update({166+i:(floor,) for i in range(6)});expected.update({172+i:(0,) for i in range(6)})
 differences=[]
 for address,values in expected.items():
  actual=registers.get(address)
  if actual not in values:differences.append({'field':f'register_{address}','expected':values[0],'actual':actual})
 powers=[registers.get(154+i) for i in range(6)]
 if any(finite(v) is None or v<500 for v in powers) or len(set(powers))!=1:
  differences.append({'field':'house_program_power','expected':'uniform >= 500 W','actual':powers})
 return {'ok':not differences,'mismatches':differences}


def decide_production(*,policy,settings,block,price,now,soc,pv_available,profile_ready):
 hold={'mode':'hold','power_w':0,'minimum_soc':policy['sale_soc'],'reason':'Čekám na platný plán, cenu a stav baterie.'}
 soc=finite(soc)
 if soc is None or not 0<=soc<=100:return hold
 valid_price=isinstance(price,dict) and all(finite(price.get(k)) is not None for k in ('start','end','net')) and price['start']<=now<price['end']
 if valid_price and price['net']>0:
  eligible=isinstance(block,dict) and all(finite(block.get(k)) is not None for k in ('start','end')) and block['start']<=now<block['end']-10
  done=eligible and block_key(block) in settings.get('completed_blocks',{})
  if eligible and not done and soc>policy['sale_soc']:
   return {'mode':'battery','power_w':policy['max_w'],'minimum_soc':policy['sale_soc'],'reason':f"Prodej podle plánu · baterie nad {policy['sale_soc']:g} %."}
  if settings.get('pv_verified') and soc>=policy['pv_soc'] and pv_available and now>=float(settings.get('cooldown_until',0)):
   return {'mode':'pv','power_w':policy['max_w'],'minimum_soc':policy['sale_soc'],'reason':'Baterie je téměř plná · dostupné přebytky.'}
 if valid_price and settings.get('bias_enabled') and settings.get('bias_verified') and soc>=policy['resume_soc'] and profile_ready:
  return {'mode':'bias','power_w':policy['bias_w'],'minimum_soc':policy['home_soc'],'reason':f"Malý trvalý přetok · cíl {policy['bias_w']:g} W, rezerva {policy['home_soc']:g} %."}
 return hold


def record_completion(settings,proof,now):
 block=proof.get('business_block')
 if (proof.get('purpose')=='automatic' and proof.get('stop_verified') is True
     and not proof.get('conflicts') and isinstance(block,dict)
     and finite(block.get('start')) is not None and finite(block.get('end')) is not None
     and (proof.get('reason')=='reserve' or proof.get('reason')=='deadline' and now>=block['end'])):
  settings.setdefault('completed_blocks',{})[block_key(block)]={'reason':proof['reason'],'stopped_at':now,'sale_id':proof.get('id')}

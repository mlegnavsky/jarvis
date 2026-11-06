"""Owner-editable production policy; no commands, flags or proof mutation."""
import hashlib
import json
import math

DEFAULTS={'pv_soc':97,'bias_w':20,'home_soc':30,'resume_soc':31,'sale_soc':60,
          'block_minutes':120,'max_w':9300,'purchase_rate':5,'sale_fee':.30}
RANGES={'pv_soc':(90,100),'bias_w':(1,50),'home_soc':(30,59),'resume_soc':(31,60),
        'sale_soc':(60,95),'block_minutes':(15,240),'max_w':(100,9300),
        'purchase_rate':(0,30),'sale_fee':(0,10)}

def validate(current,changes):
 if not isinstance(changes,dict) or not changes or set(changes)-set(DEFAULTS):raise ValueError('Neplatné položky nastavení.')
 out={**DEFAULTS,**current,**changes}
 for key,(lo,hi) in RANGES.items():
  v=out[key]
  if type(v) not in (int,float) or not math.isfinite(v) or not lo<=v<=hi:raise ValueError('Hodnota '+key+' je mimo povolený rozsah.')
  if key not in ('purchase_rate','sale_fee') and v%1:raise ValueError('Tato hodnota musí být celé číslo.')
 if not out['home_soc']<out['resume_soc']<=out['sale_soc']<out['pv_soc']:raise ValueError('Rezervy musí splňovat: domácnost < obnovení ≤ plán < přebytky.')
 if out['block_minutes']%15:raise ValueError('Délka plánu musí být násobkem 15 minut.')
 return out

def revision(value):return hashlib.sha256(json.dumps(value,sort_keys=True,allow_nan=False).encode()).hexdigest()

def rate_at(history,stamp):
 result={'purchase_rate':5,'sale_fee':.30}
 for row in sorted(history or [],key=lambda r:r['at']):
  if row['at']<=stamp:result={k:row[k] for k in result}
 return result

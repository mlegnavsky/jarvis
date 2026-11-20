"""Model-only operator policy for one microphone; never credentials or actions."""
import json
import os
from pathlib import Path
import re
import stat

SATELLITE='assist_satellite.home_assistant_voice_0a8bde_assist_satellite'
DEVICE='6275b9b88bb104060b637664f4cc7be8'
MODELS=frozenset(('configured','gpt-4.1-mini','gpt-4o-mini'))

def primary_voice(user):
 return getattr(user,'satellite_id',None)==SATELLITE or getattr(user,'device_id',None)==DEVICE

def safe_model(model):
 return model if isinstance(model,str) and re.fullmatch(r'(?:gpt-[a-zA-Z0-9_.-]{1,60}|o[134](?:-[a-zA-Z0-9_.-]{1,60})?)',model) else 'custom_model'

def read_policy(path):
 fallback={'status':'configured_default','model':None}
 try:
  path=Path(path)
  if path.parent.is_symlink():return {**fallback,'status':'invalid_configured_fallback'}
  fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
  with os.fdopen(fd,'r') as stream:
   info=os.fstat(stream.fileno())
   if not stat.S_ISREG(info.st_mode) or info.st_size>4096:raise ValueError('policy_size')
   value=json.loads(stream.read(4097))
  if not isinstance(value,dict) or set(value)!={'schema','model'} or type(value['schema']) is not int or value['schema']!=1 or value['model'] not in MODELS:raise ValueError('policy_schema')
  return {'status':'selected' if value['model']!='configured' else 'configured_default','model':None if value['model']=='configured' else value['model']}
 except FileNotFoundError:return fallback
 except (OSError,ValueError,TypeError):return {**fallback,'status':'invalid_configured_fallback'}

def request_policy(user,model,max_tokens,policy):
 if not primary_voice(user):return model,max_tokens,'not_targeted'
 if policy and policy.get('status')=='selected' and policy.get('model') in MODELS-{'configured'}:
  return policy['model'],max(512,max_tokens) if type(max_tokens) is int and max_tokens>0 else 512,'selected'
 return model,max_tokens,(policy or {}).get('status','configured_default')

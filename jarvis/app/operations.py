"""Bounded backup housekeeping and durable deployment ownership."""
import json
import math
import re
import time
from datetime import datetime
from .policy import APIError

FIELDS={
 'heating_settings':{'changes','expected_revision'},
 'backup_delete':{'backup_slug','expected_revision'},
 'deployment_acquire':{'owner','ttl_seconds','deployment_token'},
 'deployment_release':{'deployment_token'},
}
READS={'backup','storage','backup_retention','deployment_status','heating_settings'}

def setup(admin):
 with admin.db() as db:
  db.execute('CREATE TABLE IF NOT EXISTS deployment_lease (id INTEGER PRIMARY KEY CHECK(id=1),owner TEXT,token TEXT,expires REAL)')

def validate(operation,args):
 if operation=='heating_settings':
  if not isinstance(args['changes'],dict) or not args['changes'] or len(args['changes'])>20 or any(not isinstance(k,str) or not re.fullmatch(r'[a-z_]+',k) or type(v) not in (int,float) or not math.isfinite(v) for k,v in args['changes'].items()):raise APIError(400,'invalid_heating_settings')
 if operation=='deployment_acquire':
  if not isinstance(args['owner'],str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',args['owner']):raise APIError(400,'invalid_deployment_owner')
  if type(args['ttl_seconds']) is not int or not 60<=args['ttl_seconds']<=3600:raise APIError(400,'invalid_deployment_ttl')
 if 'deployment_token' in args and (not isinstance(args['deployment_token'],str) or not re.fullmatch(r'[a-f0-9]{32}',args['deployment_token'])):raise APIError(400,'invalid_deployment_token')

def lease(admin):
 with admin.db() as db:row=db.execute('SELECT owner,token,expires FROM deployment_lease WHERE id=1').fetchone()
 return row if row and row[2]>time.time() else None

def guard(admin,operation,args):
 current=lease(admin)
 if current and operation!='deployment_acquire' and args.get('deployment_token')!=current[1]:raise APIError(409,'deployment_owned_by_another_work')
 if operation!='deployment_acquire' and not current and args.get('deployment_token'):raise APIError(409,'deployment_lease_expired')

async def backups(admin):
 value=await admin.sup.request('GET','/backups')
 items=value.get('backups')
 if not isinstance(items,list):raise APIError(502,'invalid_backup_inventory')
 return items

def metadata(item):
 return {k:item.get(k) for k in ('slug','name','date','size','protected','type')}

async def read(admin,query,target):
 from .admin import revision
 if query=='heating_settings':
  value=await admin.sup.request('GET','/core/api/states/sensor.jarvis_topeni_child')
  attrs=value.get('attributes',{});settings=attrs.get('settings')
  if not isinstance(settings,dict):raise APIError(409,'heating_settings_not_available')
  return {'settings':settings,'revision':revision(settings),'runtime_version':attrs.get('version')}
 if query=='storage':
  info=await admin.sup.request('GET','/host/info')
  result={k:info.get(k) for k in ('disk_free','disk_total','disk_used')}
  if not all(type(v) in (int,float) and math.isfinite(v) and v>=0 for v in result.values()):raise APIError(502,'invalid_storage_response')
  return {**result,'unit':'GiB','backup_minimum_free_gib':2.0,'backup_ready':result['disk_free']>=2.0}
 if query=='deployment_status':
  current=lease(admin)
  return {'locked':bool(current),'owner':current[0] if current else None,'expires_at_epoch':current[2] if current else None}
 items=await backups(admin)
 if query=='backup':
  item=next((i for i in items if i.get('slug')==target),None)
  if item is None:raise APIError(404,'backup_not_found')
  public=metadata(item);return {**public,'revision':revision(public)}
 keep=3 if not target else int(target) if target.isdigit() and 1<=int(target)<=20 else None
 if keep is None:raise APIError(400,'invalid_retention_count')
 ordered=sorted(items,key=lambda i:i.get('date',''),reverse=True)
 preserved={i.get('slug') for i in ordered[:keep]}
 return {'dry_run':True,'keep_latest':keep,'automatic_delete_enabled':False,
  'preserved':[metadata(i) for i in ordered if i.get('protected') is not False or i.get('slug') in preserved],
  'candidates':[{**metadata(i),'revision':revision(metadata(i))} for i in ordered if i.get('protected') is False and i.get('slug') not in preserved],
  'notice':'Candidate preview only; each deletion requires its explicit slug and revision.'}

async def perform(admin,key,operation,args):
 from .admin import revision
 if operation=='heating_settings':
  before=await read(admin,'heating_settings','')
  if before['revision']!=args['expected_revision']:raise APIError(409,'heating_settings_changed')
  admin.remember(key,before)
  await admin.sup.request('POST','/core/api/services/jarvis_solar_heating/configure',{'settings':args['changes'],'expected_revision':args['expected_revision']})
  after=await read(admin,'heating_settings','')
  return {**after,'verified':all(after['settings'].get(k)==v for k,v in args['changes'].items()),'restart_required':False}
 if operation=='deployment_acquire':
  current=lease(admin)
  if current:raise APIError(409,'deployment_already_locked')
  token=args['deployment_token'];expires=time.time()+args['ttl_seconds']
  with admin.db() as db:db.execute('INSERT OR REPLACE INTO deployment_lease VALUES (1,?,?,?)',(args['owner'],token,expires))
  return {'verified':True,'owner':args['owner'],'expires_at_epoch':expires}
 if operation=='deployment_release':
  with admin.db() as db:db.execute('DELETE FROM deployment_lease WHERE id=1 AND token=?',(args['deployment_token'],))
  return {'verified':lease(admin) is None}
 items=await backups(admin)
 try:
  for candidate in items:
   if not isinstance(candidate.get('slug'),str) or not isinstance(candidate.get('date'),str) or type(candidate.get('protected')) is not bool:raise ValueError()
   datetime.fromisoformat(candidate['date'].replace('Z','+00:00'))
 except (ValueError,TypeError):raise APIError(409,'incomplete_backup_metadata') from None
 item=next((i for i in items if i.get('slug')==args['backup_slug']),None)
 if item is None:raise APIError(404,'backup_not_found')
 if revision(metadata(item))!=args['expected_revision']:raise APIError(409,'backup_revision_changed')
 if item.get('protected') is not False:raise APIError(409,'protected_backup')
 if item.get('date')==max((i.get('date','') for i in items),default=''):raise APIError(409,'latest_backup_protected')
 admin.remember(key,metadata(item))
 await admin.sup.request('DELETE','/backups/'+args['backup_slug'])
 remaining=await backups(admin)
 return {'verified':not any(i.get('slug')==args['backup_slug'] for i in remaining),'deleted_slug':args['backup_slug'],'recoverable':False}

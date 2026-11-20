"""Prepared, revision-bound config bundles, explicit activation and CAS rollback."""
import hashlib
import json
import re
from .policy import APIError
from . import operations
FIELDS={'deployment_prepare':{'bundle'},'deployment_apply':{'plan_id','expected_revision'},'deployment_rollback':{'plan_id','expected_revision'}}

def setup(admin):
 with admin.db() as db:db.execute('CREATE TABLE IF NOT EXISTS deployment_plans (id TEXT PRIMARY KEY,revision TEXT,bundle TEXT,before_data TEXT,phase TEXT,receipt TEXT)')

def validate(admin,operation,args):
 if operation!='deployment_prepare':
  if not isinstance(args['plan_id'],str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}',args['plan_id']):raise APIError(400,'invalid_deployment_plan')
  return
 b=args['bundle']
 if not isinstance(b,dict) or set(b)!={'source_commit','core_version','activation','files','checks'}:raise APIError(400,'invalid_deployment_bundle')
 if not isinstance(b['source_commit'],str) or not re.fullmatch(r'[a-f0-9]{40}',b['source_commit']):raise APIError(400,'invalid_source_commit')
 if not isinstance(b['core_version'],str) or not re.fullmatch(r'[0-9][0-9A-Za-z._-]{1,40}',b['core_version']):raise APIError(400,'invalid_core_version')
 if b['activation'] not in ('none','automations_reload','core_restart'):raise APIError(400,'invalid_activation')
 if not isinstance(b['files'],list) or not 1<=len(b['files'])<=30:raise APIError(400,'invalid_bundle_files')
 paths=[]
 for f in b['files']:
  if not isinstance(f,dict) or set(f)!={'path','content','expected_revision'}:raise APIError(400,'invalid_bundle_file')
  admin.files.parts(f['path']);admin.files.validate(f['path'],f['content'])
  if not isinstance(f['expected_revision'],str) or not re.fullmatch(r'missing|[a-f0-9]{64}',f['expected_revision']):raise APIError(400,'invalid_file_revision')
  paths.append(f['path'])
 if len(set(paths))!=len(paths):raise APIError(400,'duplicate_bundle_path')
 if b['activation']=='automations_reload' and any(p!='automations.yaml' for p in paths):raise APIError(400,'activation_does_not_cover_files')
 if not isinstance(b['checks'],list) or len(b['checks'])>30 or b['activation']!='none' and not b['checks']:raise APIError(400,'runtime_checks_required')
 for check in b['checks']:
  if not isinstance(check,dict) or set(check)!={'entity_id','state','version'}:raise APIError(400,'invalid_runtime_check')
  if not isinstance(check['entity_id'],str) or not re.fullmatch(r'[a-z_]+\.[a-z0-9_]+',check['entity_id']):raise APIError(400,'invalid_check_entity')
  if not check['state'] and not check['version']:raise APIError(400,'empty_runtime_check')
  if not all(v is None or isinstance(v,str) and len(v)<=100 for v in (check['state'],check['version'])):raise APIError(400,'invalid_check_expectation')

def get(admin,plan_id):
 with admin.db() as db:row=db.execute('SELECT revision,bundle,before_data,phase,receipt FROM deployment_plans WHERE id=?',(plan_id,)).fetchone()
 if not row:raise APIError(404,'deployment_not_found')
 return dict(id=plan_id,revision=row[0],bundle=json.loads(row[1]),before=json.loads(row[2]),phase=row[3],receipt=json.loads(row[4]))

def set_phase(admin,plan_id,phase,receipt=None):
 with admin.db() as db:
  if receipt is None:db.execute('UPDATE deployment_plans SET phase=? WHERE id=?',(phase,plan_id))
  else:db.execute('UPDATE deployment_plans SET phase=?,receipt=? WHERE id=?',(phase,json.dumps(receipt),plan_id))

def public(plan):
 b=plan['bundle']
 return {'id':plan['id'],'revision':plan['revision'],'phase':plan['phase'],'source_commit':b['source_commit'],
  'activation':b['activation'],'restart_required':b['activation']=='core_restart','receipt':plan['receipt'],
  'files':[{'path':f['path'],'before_revision':f['expected_revision'],'new_sha256':hashlib.sha256(f['content'].encode()).hexdigest(),
    'old_lines':len(plan['before'][f['path']]['content'].splitlines()) if plan['before'][f['path']]['content'] else 0,'new_lines':len(f['content'].splitlines())} for f in b['files']],
  'checks':b['checks'],'versions':{'source_commit':b['source_commit'],'files_written':plan['phase'] in ('file_written','activation_pending','active_verified'),'runtime_verified':plan['phase']=='active_verified'}}

async def perform(admin,key,operation,args):
 from .admin import revision
 if operation=='deployment_prepare':
  b=args['bundle'];core=await admin.sup.request('GET','/core/info')
  if core.get('version')!=b['core_version']:raise APIError(409,'core_compatibility_mismatch')
  before={}
  for f in b['files']:
   old=admin.files.read(f['path'])
   if old['revision']!=f['expected_revision']:raise APIError(409,'bundle_revision_conflict')
   before[f['path']]=old
  rev=revision(b)
  with admin.db() as db:db.execute('INSERT INTO deployment_plans VALUES (?,?,?,?,?,?)',(key,rev,json.dumps(b),json.dumps(before),'prepared','{}'))
  return {'verified':True,**public(get(admin,key))}
 plan=get(admin,args['plan_id']);b=plan['bundle']
 if plan['revision']!=args['expected_revision']:raise APIError(409,'deployment_plan_changed')
 if not operations.lease(admin) or not args.get('deployment_token'):raise APIError(409,'deployment_lease_required')
 if operation=='deployment_rollback':
  if plan['phase'] not in ('writing','file_written','activation_pending','active_verified','activation_failed'):raise APIError(409,'deployment_not_rollbackable')
  for f in b['files']:
   if admin.files.read(f['path'])['revision'] not in (hashlib.sha256(f['content'].encode()).hexdigest(),plan['before'][f['path']]['revision']):raise APIError(409,'rollback_revision_conflict')
  for f in reversed(b['files']):
   old=plan['before'][f['path']];current=hashlib.sha256(f['content'].encode()).hexdigest()
   if admin.files.read(f['path'])['revision']==old['revision']:continue
   outcome=admin.files.write(f['path'],old['content'],current)
   if outcome.get('verified') is not True:raise APIError(502,'rollback_write_not_verified')
  if any(admin.files.read(f['path'])['revision']!=plan['before'][f['path']]['revision'] for f in b['files']):raise APIError(409,'rollback_readback_mismatch')
  set_phase(admin,plan['id'],'rolled_back_files',{'activation_performed':False,'requires_activation':b['activation']!='none'})
  return {'verified':True,**public(get(admin,plan['id']))}
 if plan['phase']!='prepared':raise APIError(409,'deployment_already_started_reconcile')
 if (await admin.sup.request('GET','/core/info')).get('version')!=b['core_version']:raise APIError(409,'core_compatibility_mismatch')
 for f in b['files']:
  if admin.files.read(f['path'])['revision']!=f['expected_revision']:raise APIError(409,'bundle_revision_conflict')
 if b['activation']=='core_restart':
  storage=await operations.read(admin,'storage','')
  if not storage['backup_ready']:raise APIError(409,'insufficient_backup_space')
 # Save before-images in durable plan before the first write. Partial writes stay
 # explicit and are never automatically replayed after a lost connection.
 set_phase(admin,plan['id'],'writing')
 for f in b['files']:
  outcome=admin.files.write(f['path'],f['content'],f['expected_revision'])
  if outcome.get('verified') is not True:raise APIError(502,'bundle_write_not_verified')
 if any(admin.files.read(f['path'])['revision']!=hashlib.sha256(f['content'].encode()).hexdigest() for f in b['files']):raise APIError(409,'bundle_readback_mismatch')
 set_phase(admin,plan['id'],'file_written')
 if b['activation']=='none':return {'verified':True,**public(get(admin,plan['id']))}
 set_phase(admin,plan['id'],'activation_pending')
 try:
  if b['activation']=='core_restart':activation=await admin.perform(key,'core_restart',{'deployment_token':args['deployment_token']})
  else:activation=await admin.perform(key,'automations_reload',{'expected_revision':admin.files.read('automations.yaml')['revision'],'deployment_token':args['deployment_token']})
  if not activation.get('verified'):raise APIError(502,'activation_not_verified')
  config=await admin.sup.request('GET','/core/api/config')
  if config.get('state')!='RUNNING':raise APIError(502,'core_not_running')
  checks=[]
  for check in b['checks']:
   state=await admin.sup.request('GET','/core/api/states/'+check['entity_id'])
   match=(check['state'] is None or state.get('state')==check['state']) and (check['version'] is None or state.get('attributes',{}).get('version')==check['version'])
   checks.append({'entity_id':check['entity_id'],'state':state.get('state'),'version':state.get('attributes',{}).get('version'),'verified':match})
  if not all(c['verified'] for c in checks):raise APIError(502,'runtime_check_failed')
  if any(admin.files.read(f['path'])['revision']!=hashlib.sha256(f['content'].encode()).hexdigest() for f in b['files']):raise APIError(409,'files_changed_during_activation')
  set_phase(admin,plan['id'],'active_verified',{'checks':checks,'core_version':b['core_version']})
 except Exception:
  set_phase(admin,plan['id'],'activation_failed');raise
 return {'verified':True,**public(get(admin,plan['id']))}

"""Target-scoped private models and native ESPHome firmware jobs."""
import asyncio,base64,hashlib,json,math,re
from pathlib import Path
import yaml
from .workspace_files import WorkspaceFiles
from .config_files import ConfigFiles
from .firmware_client import FirmwareClient
from .policy import APIError
from .ha import UpstreamError

ADDON='5c53de3b_esphome'
FIELDS={'firmware_compile':{'target','expected_revision'},'firmware_install':{'target','expected_revision'},
        'firmware_config_restore':{'target','backup_id','expected_revision'},
        'firmware_model_install':{'target','model_id','model_base64','sha256','manifest','expected_revision'}}

def digest(data):return hashlib.sha256(data).hexdigest()
def identifier(value):return isinstance(value,str) and re.fullmatch(r'[a-z][a-z0-9_]{0,63}',value)

class FirmwareStore(WorkspaceFiles):
 def __init__(self,root,targets):
  super().__init__(root,'firmware');self.targets=set(targets)
 def target(self,target):
  if not isinstance(target,str) or target not in self.targets or not re.fullmatch(r'[a-zA-Z0-9_-]+\.yaml',target):
   raise APIError(403,'firmware_target_not_allowed')
  return 'esphome/'+target
 def parts(self,name):
  if name.startswith('esphome/') and name[8:] in self.targets:
   self.target(name[8:]);return name.split('/')
  if re.fullmatch(r'esphome/jarvis_models/[a-z][a-z0-9_]{0,63}-[a-f0-9]{16}\.(json|tflite)',name):return name.split('/')
  raise APIError(403,'firmware_path_not_allowed')
 def config(self,target):
  path=self.target(target);data=ConfigFiles.read(self,path)
  if data['content'] is None:raise APIError(404,'firmware_config_missing')
  try:
   root=yaml.compose(data['content']);micro=next(v for k,v in root.value if k.value=='micro_wake_word')
   models=next(v for k,v in micro.value if k.value=='models');entries=[]
   for node in models.value:
    values={k.value:v for k,v in node.value};identity=values.get('id');model=values.get('model')
    if identity and model and isinstance(model,yaml.ScalarNode) and model.tag=='tag:yaml.org,2002:str':entries.append((identity.value,model))
  except (ValueError,TypeError,AttributeError,StopIteration,yaml.YAMLError):raise APIError(400,'unsupported_firmware_model_configuration') from None
  return data,entries
 def metadata(self,target):
  data,entries=self.config(target)
  return {'target':target,'revision':data['revision'],'models':[{'id':i,'source':'remote' if re.match(r'https?:|github:',n.value) else 'local'} for i,n in entries],'credentials_exposed':False}
 def install_model(self,args):
  data,entries=self.config(args['target'])
  if data['revision']!=args['expected_revision']:raise APIError(409,'firmware_revision_conflict')
  if any(isinstance(t,(yaml.tokens.AnchorToken,yaml.tokens.AliasToken)) for t in yaml.scan(data['content'])):raise APIError(400,'firmware_model_alias_not_supported')
  if not identifier(args['model_id']):raise APIError(400,'invalid_firmware_model_id')
  nodes=[n for i,n in entries if i==args['model_id']]
  if len(nodes)!=1:raise APIError(400,'firmware_model_id_not_found')
  try:binary=base64.b64decode(args['model_base64'],validate=True)
  except (ValueError,TypeError):raise APIError(400,'invalid_firmware_model') from None
  if not 16<=len(binary)<=256*1024 or binary[4:8]!=b'TFL3' or digest(binary)!=args['sha256']:raise APIError(400,'invalid_firmware_model_digest_or_format')
  manifest=args['manifest']
  if not isinstance(manifest,dict) or set(manifest)!={'wake_word','micro'}:raise APIError(400,'invalid_firmware_manifest')
  word=manifest['wake_word'];micro=manifest['micro']
  if not isinstance(word,str) or not 1<=len(word)<=50 or not word.isprintable():raise APIError(400,'invalid_firmware_manifest')
  if not isinstance(micro,dict) or set(micro)!={'probability_cutoff','sliding_window_size','feature_step_size','tensor_arena_size'}:raise APIError(400,'invalid_firmware_manifest')
  probability=micro['probability_cutoff']
  if type(probability) not in (float,int) or not math.isfinite(probability) or not 0<probability<1:raise APIError(400,'invalid_firmware_manifest')
  if micro['feature_step_size'] not in (10,20):raise APIError(400,'invalid_firmware_manifest')
  for field,low,high in [('sliding_window_size',1,20),('feature_step_size',10,20),('tensor_arena_size',16384,524288)]:
   if type(micro[field]) is not int or not low<=micro[field]<=high:raise APIError(400,'invalid_firmware_manifest')
  metadata={'type':'micro','version':2,'wake_word':word,'author':'Jarvis','trained_languages':['cs'],'micro':{**micro,'minimum_esphome_version':'2024.7.0'}}
  stem='jarvis_models/'+args['model_id']+'-'+digest(binary+json.dumps(metadata,sort_keys=True).encode())[:16]
  manifest_path=stem+'.json';model_path=stem+'.tflite'
  complete={**metadata,'model':Path(model_path).name}
  for path,content in [(model_path,binary),(manifest_path,(json.dumps(complete,ensure_ascii=False,indent=2)+'\n').encode())]:
   path='esphome/'+path;old,_=self.raw(path)
   if old is not None and old!=content:raise APIError(409,'firmware_model_asset_conflict')
   if old is None:self.write_raw(path,content,'missing',0o600)
  node=nodes[0];content=data['content'][:node.start_mark.index]+json.dumps(manifest_path)+data['content'][node.end_mark.index:]
  try:yaml.compose(content)
  except yaml.YAMLError:raise APIError(400,'invalid_firmware_candidate') from None
  result=self.write_raw(data['path'],content.encode(),data['revision'],0o600)
  return {**result,'target':args['target'],'manifest_path':manifest_path,'model_path':model_path,'model_sha256':args['sha256'],'activation_performed':False}

class FirmwareBridge:
 def __init__(self,admin,client=None):self.admin=admin;self.client=client or FirmwareClient(admin.sup)
 def store(self):return FirmwareStore(self.admin.files.root,self.admin.options.get('firmware_targets',[]))
 def validate(self,operation,args):
  self.store().target(args['target'])
 async def read(self,query,target):
  try:return await self._read(query,target)
  except UpstreamError:return {'available':False,'error':'firmware_unavailable','stage':getattr(self.client,'last_failure_stage','native_response')}
 async def _read(self,query,target):
  store=self.store()
  if query=='firmware_config':return store.metadata(target)
  if query=='firmware_job':
   if not re.fullmatch(r'[a-zA-Z0-9_-]{1,128}',target):raise APIError(400,'invalid_firmware_job')
   job=await self.client.call('firmware/get_job',{'job_id':target});job=unwrap(job,'job')
   store.target(job.get('configuration'))
   if job.get('job_id')!=target:raise UpstreamError('firmware_job_identity_mismatch')
   return public_job(job)
  if query=='firmware_jobs':
   store.target(target)
   jobs=unwrap(await self.client.call('firmware/get_jobs',{'configuration':target}),'jobs')
   return {'jobs':[public_job(j) for j in jobs if j.get('configuration')==target][-50:]}
  values=await self.client.call('devices/list');devices=unwrap(values,'devices')
  if not isinstance(devices,list):raise UpstreamError('firmware_device_list_invalid')
  allowed=self.admin.options.get('firmware_targets',[])
  return {'devices':[public_device(d) for d in devices if d.get('configuration') in allowed],
          'allowed_targets':allowed,'browser_login_required':False}
 async def perform(self,key,operation,args):
  store=self.store();meta=store.metadata(args['target'])
  if meta['revision']!=args['expected_revision']:raise APIError(409,'firmware_revision_conflict')
  if operation=='firmware_config_restore':
   with self.admin.db() as db:
    row=db.execute('SELECT operation,before_data FROM jobs WHERE key=?',(args['backup_id'],)).fetchone()
   saved=json.loads(row[1]) if row and row[1] else {}
   before=saved.get('firmware_config',{})
   if not row or row[0]!='firmware_model_install' or before.get('path')!=store.target(args['target']) or not isinstance(before.get('content'),str):raise APIError(404,'firmware_backup_not_found')
   self.admin.remember(key,{'firmware_config':ConfigFiles.read(store,store.target(args['target']))})
   result=store.write_raw(before['path'],before['content'].encode(),args['expected_revision'],0o600)
   return {**result,'activation_performed':False}
  if operation=='firmware_model_install':
   self.admin.remember(key,{'firmware_config':ConfigFiles.read(store,store.target(args['target']))})
   return store.install_model(args)
  if operation=='firmware_install':
   configured=unwrap(await self.client.call('devices/list'),'devices')
   device=next((d for d in configured if d.get('configuration')==args['target']),{})
   if (device.get('runtime_state') or {}).get('state')!='online':
    raise APIError(409,'firmware_device_not_online')
   await self.admin.backup(key,ADDON)
  # Recheck after backup; never compile a config changed while preparing.
  if store.metadata(args['target'])['revision']!=args['expected_revision']:raise APIError(409,'firmware_revision_conflict')
  command='firmware/install' if operation=='firmware_install' else 'firmware/compile'
  payload={'configuration':args['target'],'force_local':True}
  if operation=='firmware_install':payload.update(port='OTA',bootloader=False)
  job=unwrap(await self.client.call(command,payload),'job')
  job_id=job.get('job_id')
  if not isinstance(job_id,str):raise UpstreamError('firmware_job_not_confirmed')
  check_job(job,job_id,args['target'],'compile')
  self.admin.remember(key,{'firmware_job_id':job_id,'target':args['target'],'source_revision':args['expected_revision']})
  with self.admin.db() as db:
   db.execute('UPDATE jobs SET summary=? WHERE key=?',(json.dumps({'operation':operation,'target':args['target'],'firmware_job_id':job_id}),key))
  deadline=asyncio.get_running_loop().time()+3600
  while job.get('status') in ('queued','running'):
   if asyncio.get_running_loop().time()>deadline:raise UpstreamError('firmware_job_timeout')
   await asyncio.sleep(2)
   job=unwrap(await self.client.call('firmware/get_job',{'job_id':job_id}),'job')
   check_job(job,job_id,args['target'],'compile')
  if job.get('status')!='completed' or job.get('exit_code')!=0:
   return {'verified':False,'firmware_job':public_job(job),'physical_result':False}
  if store.metadata(args['target'])['revision']!=args['expected_revision']:
   return {'verified':False,'firmware_job':public_job(job),'error':'firmware_config_changed_during_job'}
  if operation=='firmware_compile':return {'verified':True,'firmware_job':public_job(job),'activation_performed':False}
  # install returns the COMPILE chain head, never the upload itself.
  retained=unwrap(await self.client.call('firmware/get_jobs',{'configuration':args['target']}),'jobs')
  upload=next((j for j in retained if j.get('configuration')==args['target'] and j.get('job_type')=='upload' and j.get('depends_on')==job_id),None)
  if upload is None:
   return {'verified':False,'firmware_job':public_job(job),'error':'firmware_upload_deferred_or_not_confirmed','activation_performed':False}
  upload_id=upload.get('job_id')
  if not isinstance(upload_id,str):raise UpstreamError('firmware_job_not_confirmed')
  check_job(upload,upload_id,args['target'],'upload',job_id)
  self.admin.remember(key,{'firmware_job_id':job_id,'firmware_upload_job_id':upload_id,'target':args['target'],'source_revision':args['expected_revision']})
  while upload.get('status') in ('queued','running'):
   if asyncio.get_running_loop().time()>deadline:raise UpstreamError('firmware_job_timeout')
   await asyncio.sleep(2)
   upload=unwrap(await self.client.call('firmware/get_job',{'job_id':upload_id}),'job')
   check_job(upload,upload_id,args['target'],'upload',job_id)
  job=upload
  if job.get('status')!='completed' or job.get('exit_code')!=0:
   return {'verified':False,'firmware_job':public_job(job),'physical_result':False}
  if store.metadata(args['target'])['revision']!=args['expected_revision']:
   return {'verified':False,'firmware_job':public_job(job),'error':'firmware_config_changed_during_job'}
  # Native job completion is followed by actual device reconnect/hash readback.
  for _ in range(90):
   values=unwrap(await self.client.call('devices/list'),'devices')
   device=next((d for d in values if d.get('configuration')==args['target']),{})
   runtime=device.get('runtime_state') or {}
   expected=device.get('expected_config_hash');deployed=runtime.get('deployed_config_hash')
   if isinstance(expected,str) and re.fullmatch(r'[a-fA-F0-9]{8}',expected) and expected==deployed and runtime.get('state')=='online':
    if store.metadata(args['target'])['revision']!=args['expected_revision']:
     return {'verified':False,'firmware_job':public_job(job),'error':'firmware_config_changed_during_reconnect'}
    return {'verified':True,'firmware_job':public_job(job),'device':public_device(device),'activation_performed':True,'acoustic_test_performed':False}
   await asyncio.sleep(2)
  return {'verified':False,'firmware_job':public_job(job),'error':'firmware_reconnect_or_hash_not_verified'}

def unwrap(value,key):
 if key=='devices' and isinstance(value,dict) and 'configured' in value:return value['configured']
 if isinstance(value,dict) and key in value:return value[key]
 return value

def public_job(job):return {k:job.get(k) for k in ('job_id','configuration','job_type','status','exit_code','progress','created_at','completed_at','depends_on')}
def public_device(d):
 runtime=d.get('runtime_state') or {}
 return {'configuration':d.get('configuration'),'expected_config_hash':d.get('expected_config_hash'),
         'deployed_config_hash':runtime.get('deployed_config_hash'),'status':runtime.get('state')}

def check_job(job,job_id,target,kind,dependency=None):
 if not isinstance(job,dict) or job.get('job_id')!=job_id or job.get('configuration')!=target or job.get('job_type')!=kind or (dependency is not None and job.get('depends_on')!=dependency):raise UpstreamError('firmware_job_identity_mismatch')

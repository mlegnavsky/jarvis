"""Pure target and response policy for the explicitly installed Core capability."""
import re

COMMANDS=frozenset({'devices/list','firmware/compile','firmware/install','firmware/get_job','firmware/get_jobs'})
JOB_FIELDS=('job_id','configuration','job_type','status','exit_code','progress','created_at','started_at','completed_at','depends_on')
def error_summary(value):
    lines=value.get('output')
    if not isinstance(lines,list):lines=[]
    clean=[]
    for line in lines[-200:]:
        if not isinstance(line,str):continue
        line=re.sub(r'\x1b\[[0-9;]*[A-Za-z]','',line)
        if not re.search(r'error|failed|undefined reference|killed|fatal|no space',line,re.I):continue
        # Never echo arbitrary compiler text: even an unlabelled C++ identifier
        # or quoted URL can contain a user credential from generated source.
        category='unclassified_build_error'
        for pattern,label in (
                (r'authentication failed|unauthorized|authentication required','authentication_failure'),
                (r'killed signal|out of memory|cannot allocate memory|cc1plus.*killed','compiler_out_of_memory'),
                (r'no space left','storage_full'),
                (r'no member named|missing member','cpp_missing_member'),
                (r'not declared in this scope','cpp_not_declared'),
                (r'no matching function','cpp_no_matching_function'),
                (r'undefined reference','link_undefined_reference'),
                (r'invalid conversion|cannot convert','cpp_invalid_conversion'),
                (r'no such file or directory','dependency_file_missing'),
                (r'error [0-9]+|failed','build_failed')):
            if re.search(pattern,line,re.I):category=label;break
        location=re.search(r':([0-9]{1,6})(?::([0-9]{1,6}))?:\s*(?:fatal\s+)?error',line,re.I)
        item=category+((' at line '+location[1]+(':'+location[2] if location[2] else '')) if location else '')
        if item not in clean:clean.append(item)
    return {'available':bool(clean),'lines':clean[-30:]}

def valid_target(value):
    return isinstance(value,str) and bool(re.fullmatch(r'[A-Za-z0-9_-]+\.yaml',value)) and value!='secrets.yaml'

def authorize(command,args,targets):
    if command not in COMMANDS or not isinstance(args,dict) or not targets or not all(valid_target(t) for t in targets):raise ValueError('invalid_request')
    if command=='devices/list':
        if args:raise ValueError('invalid_request')
        return {}
    if command=='firmware/get_job':
        if set(args)!={'job_id'} or not isinstance(args['job_id'],str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}',args['job_id']):raise ValueError('invalid_request')
        return dict(args)
    allowed={'configuration'}
    if command in ('firmware/compile','firmware/install'):allowed.add('force_local')
    if command=='firmware/install':allowed.update(('port','bootloader'))
    if set(args)-allowed or args.get('configuration') not in targets:raise ValueError('target_not_allowed')
    if 'force_local' in args and args['force_local'] is not True:raise ValueError('invalid_request')
    result={'configuration':args['configuration']}
    if command in ('firmware/compile','firmware/install'):result['force_local']=True
    if command=='firmware/install':
        if args.get('port','OTA')!='OTA' or args.get('bootloader',False) is not False:raise ValueError('invalid_request')
        result.update(port='OTA',bootloader=False)
    return result

def _job(value,targets):
    if not isinstance(value,dict) or value.get('configuration') not in targets:raise ValueError('target_not_allowed')
    result={k:value.get(k) for k in JOB_FIELDS}
    if value.get('status')=='failed':result['error_summary']=error_summary(value)
    return result

def redact_result(command,value,targets,args):
    if command=='devices/list':
        if not isinstance(value,dict) or not isinstance(value.get('configured'),list):raise ValueError('invalid_response')
        devices=[]
        for device in value['configured']:
            if not isinstance(device,dict) or device.get('configuration') not in targets:continue
            runtime=device.get('runtime_state') or {}
            devices.append({'configuration':device['configuration'],'name':device.get('name'),'expected_config_hash':device.get('expected_config_hash'),
                            'runtime_state':{k:runtime.get(k) for k in ('state','deployed_config_hash','deployed_version','queued_update')}})
        return {'configured':devices,'importable':[]}
    if command=='firmware/get_jobs':
        if not isinstance(value,list):raise ValueError('invalid_response')
        return [_job(j,targets) for j in value if isinstance(j,dict) and j.get('configuration')==args['configuration']][:500]
    result=_job(value,targets)
    if command=='firmware/get_job' and result['job_id']!=args['job_id']:raise ValueError('invalid_response')
    if command in ('firmware/install','firmware/compile') and result['configuration']!=args['configuration']:raise ValueError('invalid_response')
    return result

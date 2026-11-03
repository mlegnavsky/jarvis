"""Fixed Voice PE reference overlay; never accept arbitrary YAML, URLs or paths."""
import re
import yaml
from .policy import APIError

TARGET='home-assistant-voice-0a8bde.yaml'
# Both overlays require the stable public identity compiled into the silent gate.
PROFILES={'legacy':'voice-pe-legacy.yaml','stock_sendspin':'voice-pe-stock-sendspin.yaml'}
REF=r'(?:main|dev|stable|v?\d{2,4}\.\d{1,2}\.\d{1,2}|[a-f0-9]{40})'
PUBLIC=re.compile(r'github://(esphome/home-assistant-voice-pe)/(home-assistant-voice(?:\.factory)?\.yaml)(?:@('+REF+r'))?')


def mapping(node):
    if not isinstance(node,yaml.MappingNode):return {}
    result={}
    for key,value in node.value:
        if not isinstance(key,yaml.ScalarNode) or key.value in result:
            raise APIError(400,'ambiguous_firmware_configuration')
        result[key.value]=value
    return result


def document(source):
    try:
        root=yaml.compose(source)
        if not isinstance(root,yaml.MappingNode):raise ValueError()
        return root,mapping(root)
    except (ValueError,TypeError,yaml.YAMLError,RecursionError):
        raise APIError(400,'unsupported_firmware_reference_configuration') from None


def facts(source):
    result={'public_voice_package':None,'overlay_present':False,'api_encryption_declared':False}
    try:
        _,values=document(source);packages=mapping(values.get('packages'))
        result['overlay_present']='jarvis_reference' in packages
        result['api_encryption_declared']='encryption' in mapping(values.get('api'))
        for node in packages.values():
            if isinstance(node,yaml.ScalarNode) and node.tag=='tag:yaml.org,2002:str':
                match=PUBLIC.fullmatch(node.value)
                if match:
                    if result['public_voice_package'] is not None:
                        result['public_voice_package']=None;break
                    result['public_voice_package']=dict(repository=match[1],path=match[2],ref=match[3])
        result['top_level_sendspin']='sendspin' in values
        result['top_level_reference']='jarvis_reference' in values
    except APIError:
        result['unsupported_configuration']=True
    return result


def staged_source(source, args):
    if (args.get('target')!=TARGET or args.get('profile') not in PROFILES or
            not isinstance(args.get('source_sha'),str) or not re.fullmatch(r'[a-f0-9]{40}',args['source_sha']) or
            not isinstance(args.get('reference_server_id'),str) or
            not re.fullmatch(r'[A-Za-z0-9_-]{43}',args['reference_server_id'])):
        raise APIError(400,'invalid_firmware_reference_source')
    _,values=document(source);node=values.get('packages');packages=mapping(node)
    observed=facts(source)
    if (not isinstance(node,yaml.MappingNode) or node.flow_style or not packages or
            'jarvis_reference' in packages or 'jarvis_reference' in values or
            not observed['public_voice_package'] or not observed['api_encryption_declared']):
        raise APIError(400,'unsupported_firmware_reference_configuration')
    if node.start_mark.column!=2 or node.end_mark.column!=0:
        raise APIError(400,'unsupported_firmware_package_layout')
    sha=args['source_sha'];profile=PROFILES[args['profile']]
    block=('  jarvis_reference:\n'
           '    url: https://github.com/mlegnavsky/jarvis\n'
           f'    ref: {sha}\n'
           '    refresh: never\n'
           '    files:\n'
           f'      - path: firmware/reference_bridge/{profile}\n'
           '        vars:\n'
           f'          jarvis_reference_source_sha: {sha}\n'
           f'          jarvis_reference_server_id: "{args["reference_server_id"]}"\n')
    offset=node.end_mark.index
    if offset and source[offset-1]!='\n':block='\n'+block
    candidate=source[:offset]+block+source[offset:]
    _,checked=document(candidate)
    if 'jarvis_reference' not in mapping(checked.get('packages')):
        raise APIError(400,'firmware_reference_stage_invalid')
    return candidate

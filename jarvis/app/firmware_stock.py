"""Render one official Voice PE configuration; connectivity never leaves the host."""
import re
import yaml
from .firmware_reference import TARGET, document, mapping
from .policy import APIError

def stock_source(source, args):
    if args.get('target') != TARGET or not re.fullmatch(r'[a-f0-9]{40}', str(args.get('package_sha', ''))):
        raise APIError(400, 'invalid_stock_firmware_source')
    try:
        if any(isinstance(t, (yaml.tokens.AnchorToken, yaml.tokens.AliasToken)) for t in yaml.scan(source)):
            raise ValueError()
        root, values = document(source)
        def check(node):
            if isinstance(node, yaml.MappingNode):
                mapping(node)
                for _, child in node.value: check(child)
            elif isinstance(node, yaml.SequenceNode):
                for child in node.value: check(child)
        check(root)
        wifi = mapping(values.get('wifi'))
        if not (('ssid' in wifi and 'password' in wifi) or 'networks' in wifi): raise ValueError()
        api = mapping(values.get('api'))
        if 'key' not in mapping(api.get('encryption')): raise ValueError()
        def node(value): return yaml.compose(yaml.safe_dump(value, sort_keys=False))
        def selected(original, keys):
            return yaml.MappingNode('tag:yaml.org,2002:map', [(k,v) for k,v in original.value if k.value in keys])
        subs = mapping(values.get('substitutions'))
        esphome = mapping(values.get('esphome'))
        original_name=esphome.get('name')
        substitution_name=subs.get('name')
        if original_name is not None and original_name.value not in (TARGET[:-5],'${name}'): raise ValueError()
        if original_name is None or original_name.value=='${name}':
            if substitution_name is None or substitution_name.value!=TARGET[:-5]: raise ValueError()
        suffix=esphome.get('name_add_mac_suffix')
        if suffix is None or suffix.value.lower() not in ('false','no','off'): raise ValueError()
        friendly = subs.get('friendly_name')
        if friendly is not None and not isinstance(friendly, yaml.ScalarNode): raise ValueError()
        result = node({'substitutions': {'name': TARGET[:-5], 'friendly_name': friendly.value if friendly else 'Home Assistant Voice 0a8bde'},
                       'packages': {'device': 'github://esphome/home-assistant-voice-pe/home-assistant-voice.yaml@'+args['package_sha']},
                       'esphome': {'name': '${name}', 'friendly_name': '${friendly_name}', 'name_add_mac_suffix': False}})
        result.value.append((node('wifi'), selected(values['wifi'], {'ssid','password','networks','manual_ip','domain','use_address','hidden','fast_connect'})))
        result.value.append((node('api'), selected(values['api'], {'encryption','port'})))
        if 'ota' in values:
            ota = values['ota']
            if not isinstance(ota, yaml.SequenceNode): raise ValueError()
            retained=[]
            for entry in ota.value:
                fields=mapping(entry)
                if fields.get('platform') is None or fields['platform'].value!='esphome': continue
                clean=selected(entry, {'platform','password','encryption','port','version'})
                clean.value.append((node('id'),yaml.ScalarNode('!extend','ota_esphome')))
                retained.append(clean)
            if len(retained)>1: raise ValueError()
            if retained: result.value.append((node('ota'), yaml.SequenceNode('tag:yaml.org,2002:seq', retained)))
        text=yaml.serialize(result)
        # Unknown substitution references in private networking must never be lost.
        if set(re.findall(r'\$\{([^}]+)\}', text))-{'name','friendly_name'}: raise ValueError()
        return '# Official Voice PE recovery; private networking retained.\n'+text
    except (ValueError, TypeError, AttributeError, yaml.YAMLError):
        raise APIError(400, 'unsupported_stock_firmware_configuration') from None

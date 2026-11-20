"""Read only audio/lifecycle facts from one private firmware configuration.

YAML is composed, never constructed or executed. Source text, scalar strings,
lambda bodies, remote package URLs and private model paths are not returned.
Missing fields remain unknown because ESPHome packages may supply them.
"""
import hashlib
import math
from pathlib import Path
import re

import yaml

TARGET = 'home-assistant-voice-0a8bde.yaml'
LIFECYCLE = ('on_start', 'on_listening', 'on_stt_vad_end', 'on_tts_start', 'on_tts_end', 'on_end')


def mapping(node):
    return {key.value: value for key, value in node.value
            if isinstance(key, yaml.ScalarNode)} if isinstance(node, yaml.MappingNode) else {}


def number(node):
    if not isinstance(node, yaml.ScalarNode) or node.tag not in (
            'tag:yaml.org,2002:int', 'tag:yaml.org,2002:float'):
        return None
    try:
        value = float(node.value)
        return value if math.isfinite(value) and -100 <= value <= 100 else None
    except ValueError:
        return None


def microphones(node):
    if node is None:
        return None
    nodes = node.value if isinstance(node, yaml.SequenceNode) else [node]
    return [{key: number(values[key]) for key in ('channels', 'gain_factor') if key in values}
            for item in nodes[:4] if (values := mapping(item))]


def gain_dbfs(node):
    if not isinstance(node, yaml.ScalarNode) or node.tag != 'tag:yaml.org,2002:str':
        return None
    match = re.fullmatch(r'(-?\d+(?:\.\d+)?)\s*d[bB][fF][sS]', node.value)
    return float(match[1]) if match and -100 <= float(match[1]) <= 100 else None


def walk(node, seen=None):
    seen = set() if seen is None else seen
    if node is None or id(node) in seen:
        return
    seen.add(id(node))
    yield node
    if isinstance(node, yaml.MappingNode):
        for key, value in node.value:
            yield from walk(key, seen)
            yield from walk(value, seen)
    elif isinstance(node, yaml.SequenceNode):
        for value in node.value:
            yield from walk(value, seen)


def lifecycle(node):
    if node is None:
        return None
    keys = {key for item in walk(node) for key in mapping(item)}
    return {'stops_assistant': 'voice_assistant.stop' in keys,
            'starts_assistant': bool(keys & {'voice_assistant.start', 'voice_assistant.start_continuous'}),
            'contains_lambda': 'lambda' in keys,
            'waits_until': 'wait_until' in keys}


def read_snapshot(config_root):
    result = {'status': 'unavailable', 'scope': 'single_target_top_level_audio_facts',
              'target': TARGET, 'source_exposed': False}
    try:
        root = Path(config_root).resolve()
        path = root / 'esphome' / TARGET
        if (path.parent.is_symlink() or path.is_symlink() or not path.is_file()
                or not path.resolve().is_relative_to(root) or path.stat().st_size > 128*1024):
            return result
        raw = path.read_bytes()
        if len(raw) > 128*1024:
            return result
        document = yaml.compose(raw.decode('utf-8'))
        values = mapping(document)
        if not isinstance(document, yaml.MappingNode):
            return result
        for node in walk(document):
            if isinstance(node, yaml.MappingNode):
                keys = [key.value for key, _value in node.value if isinstance(key, yaml.ScalarNode)]
                if len(keys) != len(set(keys)):
                    return result
        wake, assistant = mapping(values.get('micro_wake_word')), mapping(values.get('voice_assistant'))
        # Report only identifier-shaped model names mentioned by sensitivity
        # code, never the lambda itself or a guessed effective cutoff.
        overrides = set()
        selects = values.get('select')
        if isinstance(selects, yaml.SequenceNode):
            for select in selects.value[:64]:
                item = mapping(select)
                identity = item.get('id')
                if not isinstance(identity, yaml.ScalarNode) or identity.value != 'wake_word_sensitivity':
                    continue
                for node in walk(item.get('on_value')):
                    if isinstance(node, yaml.ScalarNode):
                        overrides.update(re.findall(r'id\(([a-z][a-z0-9_]{0,63})\)\.set_probability_cutoff\(', node.value))
        result.update(status='observed', revision=hashlib.sha256(raw).hexdigest(),
                      packages_present='packages' in values,
                      wake_microphone=microphones(wake.get('microphone')),
                      wake_vad_configured=('vad' in wake) if wake else None,
                      assistant_microphones=microphones(assistant.get('microphone')),
                      assistant_audio={**{key: number(assistant[key]) for key in
                          ('noise_suppression_level', 'volume_multiplier') if key in assistant},
                          'auto_gain_dbfs': gain_dbfs(assistant.get('auto_gain'))},
                      assistant_lifecycle={key: lifecycle(assistant.get(key)) for key in LIFECYCLE},
                      sensitivity_cutoff_models=sorted(overrides)[:16])
    except (OSError, UnicodeError, ValueError, yaml.YAMLError, RecursionError):
        pass
    return result

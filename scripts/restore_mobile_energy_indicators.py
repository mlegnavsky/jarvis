"""Reuse Domov's live house composite in the Energie mobile card only."""
import copy
import sys
from pathlib import Path
import yaml

class Loader(yaml.SafeLoader):
    pass
Loader.add_constructor('!include', lambda loader, node: loader.construct_scalar(node))

def walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)

def patch(source):
    data = yaml.load(source, Loader=Loader)
    home = next(v for v in data['views'] if isinstance(v, dict) and v.get('path') == 'domov')
    energy = next(v for v in data['views'] if isinstance(v, dict) and v.get('path') == 'energie')
    composite = next(c for c in walk(home) if c.get('type') == 'picture-elements'
                     and any(e.get('image', '').endswith('/solar-house.png') for e in c.get('elements', [])))
    mobile = next(c for c in walk(energy) if c.get('type') == 'vertical-stack'
                  and c.get('cards', [{}])[0].get('type') == 'picture'
                  and c['cards'][0].get('image', '').endswith('/solar-house.png'))
    replacement = copy.deepcopy(composite)
    replacement['visibility'] = copy.deepcopy(mobile['visibility'])
    replacement['grid_options'] = copy.deepcopy(mobile['grid_options'])
    replacement.pop('title', None)
    assert sum(e.get('type') == 'state-label' for e in replacement['elements']) == 6
    tree = yaml.compose(source, Loader=Loader)
    # Find by original mapping identity through its start/end positions.
    def nodes(node):
        if isinstance(node, yaml.MappingNode):
            keys = {k.value: v for k, v in node.value}
            if keys.get('type') and keys['type'].value == 'vertical-stack' and 'cards' in keys:
                cards = keys['cards']
                if cards.value:
                    first = {k.value: v for k, v in cards.value[0].value}
                    if first.get('type') and first['type'].value == 'picture' and first.get('image') and first['image'].value.endswith('/solar-house.png'):
                        yield node
            for _, child in node.value:
                yield from nodes(child)
        elif isinstance(node, yaml.SequenceNode):
            for child in node.value:
                yield from nodes(child)
    candidates = list(nodes(tree))
    assert len(candidates) == 1
    node = candidates[0]
    indent = node.start_mark.column
    rendered = yaml.safe_dump(replacement, allow_unicode=True, sort_keys=False, width=140).rstrip()
    rendered = rendered.replace('\n', '\n' + ' ' * indent) + '\n'
    result = source[:node.start_mark.index] + rendered + ' ' * node.end_mark.column + source[node.end_mark.index:]
    after = yaml.load(result, Loader=Loader)
    for old, new in zip(data['views'], after['views']):
        if isinstance(old, dict) and old.get('path') == 'energie':
            expected = copy.deepcopy(old)
            for section in expected['sections']:
                section['cards'] = [replacement if c == mobile else c for c in section['cards']]
            assert new == expected
        else:
            assert old == new
    return result

if __name__ == '__main__':
    Path(sys.argv[2]).write_text(patch(Path(sys.argv[1]).read_text()))
    print('PASS: six live indicators restored; duplicate mobile tiles removed; all other cards and views preserved')

"""Replace the two legacy living-room sensor placeholders in a live YAML copy.

Pass input/output paths and actual temperature/humidity entity IDs as arguments.
The live dashboard and household inventory must stay out of the public repository.
"""
import re
import sys
from pathlib import Path


def connect(content, temperature, humidity):
    count = 0

    def replace(match):
        nonlocal count
        indent = match[1]
        detail = count == 1
        count += 1

        def label(entity, title, top, prefix):
            lines = [
                '- type: state-label', f'  entity: {entity}', f'  title: {title}',
                f"  prefix: '{prefix}'", '  tap_action:', '    action: more-info',
                '  style:', f'    left: {60 if detail else 54}%', f'    top: {top}%',
                '    color: white', '    background: rgba(3,19,39,.92)',
                '    border-radius: 10px', '    padding: 4px 8px',
                f'    font-size: {16 if detail else 14}px',
            ]
            return '\n'.join(indent + line for line in lines)

        return label(temperature, 'Obývák – teplota', 82 if detail else 69, '🌡 ') + '\n' + label(humidity, 'Obývák – vlhkost', 89 if detail else 75, '💧 ')

    result = re.sub(r'^( *)- type: image\n +title: HomePod · teplota není připojená do HA\n[\s\S]*?\n +width: 160px', replace, content, flags=re.M)
    if count != 2:
        raise ValueError(f'Expected two placeholders, found {count}; refusing partial change')
    return result


if __name__ == '__main__':
    source, destination, temperature, humidity = sys.argv[1:]
    for entity in (temperature, humidity):
        if not re.fullmatch(r'sensor\.[a-z0-9_]+', entity):
            raise ValueError('Expected a sensor entity ID')
    Path(destination).write_text(connect(Path(source).read_text(), temperature, humidity))

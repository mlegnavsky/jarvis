"""Replace only the existing bullhorn navigation, preserving private dashboard text."""
from pathlib import Path
import re
import sys


def patch(content):
    pattern = (r'(?m)^( +)- type: icon\n\1  icon: mdi:bullhorn\n'
               r'\1  title: Vzkaz domů – HomePod\n\1  tap_action:\n'
               r'\1    action: navigate\n\1    navigation_path: /hlavni-prehled/vzkaz\n')
    result, count = re.subn(pattern, lambda m: (
        m[1] + '- type: custom:jarvis-home-intercom\n'
        + m[1] + '  entity: media_player.homepod_obyvak_homepod_obyvak\n'
        + m[1] + '  title: Nahrát vzkaz domů\n'
        + m[1] + '  tap_action:\n' + m[1] + '    action: none\n'), content)
    if count != 2 and result.count('type: custom:jarvis-home-intercom') != 2:
        raise ValueError('Expected exactly two floorplan bullhorns')
    return result


def module():
    root = Path(__file__).parent
    return (root / 'home-message.js').read_text() + '\n\n' + (root / 'intercom.js').read_text()


if __name__ == '__main__':
    source, target, javascript = map(Path, sys.argv[1:])
    target.write_text(patch(source.read_text()))
    javascript.write_text(module())

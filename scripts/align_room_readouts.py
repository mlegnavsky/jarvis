"""Align main floorplan room labels without rewriting private YAML."""
import base64
import re

def patch(content):
    moves = 0
    def element(match):
        nonlocal moves
        block = match.group(0)
        original = block
        if 'entity: sensor.aqara_temp_humidity_sensor_teplota\n' in block:
            block = block.replace('top: 69%', 'top: 73%')
        if 'entity: sensor.aqara_temp_humidity_sensor_vlhkost_vzduchu\n' in block:
            block = block.replace('top: 75%', 'top: 78%')
        image = re.search(r'image: data:image/svg\+xml;base64,([^\n]+)', block)
        if image:
            svg = base64.b64decode(image.group(1)).decode()
            if '>Obývák<' in svg or '>Ložnice<' in svg:
                block = block.replace('top: 79%', 'top: 84%')
        moves += block != original
        return block
    result = re.sub(r'^      - type:.*\n(?:^ {8}[^\n]*\n|^\n)*', element, content, flags=re.M)
    if moves not in (0, 4):
        raise ValueError(f'Unexpected moved label count: {moves}')
    if 'Ložnice – teplota: bez údajů' not in result:
        for label, top in [('teplota', 73), ('vlhkost', 78)]:
            text = f'{label.capitalize()}: bez údajů'
            svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="240" height="40"><rect width="240" height="40" rx="9" fill="#071c32" fill-opacity=".92"/><text x="120" y="26" text-anchor="middle" font-family="sans-serif" font-size="17" fill="white">{text}</text></svg>'
            image = base64.b64encode(svg.encode()).decode()
            block = f"      - type: image\n        title: 'Ložnice – {label}: bez údajů'\n        image: data:image/svg+xml;base64,{image}\n        tap_action:\n          action: none\n        style:\n          left: 80%\n          top: {top}%\n          width: 17%\n"
            # Only the first overview elements collection, before its next existing item.
            marker = '      - type: custom:jarvis-home-intercom\n'
            if marker not in result:
                raise ValueError('Overview marker missing')
            result = result.replace(marker, block + marker, 1)
    return result

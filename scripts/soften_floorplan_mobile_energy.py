"""Patch the existing dashboard without rewriting unrelated YAML or images."""
import base64
import re
import sys
from pathlib import Path

def patch(source):
    def soften(match):
        svg = base64.b64decode(match[1]).decode()
        if not re.search(r'fill="#00152b(?:66|b3)"', svg):
            return match[0]
        gradient = ('<defs><radialGradient id="room-shade">'
                    '<stop offset="0" stop-color="#071729" stop-opacity=".28"/>'
                    '<stop offset=".65" stop-color="#071729" stop-opacity=".16"/>'
                    '<stop offset="1" stop-color="#071729" stop-opacity="0"/>'
                    '</radialGradient></defs>')
        svg = svg.replace('<polygon', gradient + '<polygon', 1)
        svg = re.sub(r'fill="#00152b(?:66|b3)"', 'fill="url(#room-shade)"', svg)
        return 'data:image/svg+xml;base64,' + base64.b64encode(svg.encode()).decode()
    source = re.sub(r'data:image/svg\+xml;base64,([A-Za-z0-9+/=]+)', soften, source)
    start = source.index('    - type: picture-elements\n', source.index('custom:jarvis-battery-overview'))
    mobile = source.index('    - type: vertical-stack\n', start)
    end = source.index('    - type: markdown\n', mobile)
    card = source[start:mobile]
    visibility = "      visibility:\n      - condition: screen\n        media_query: '(min-width: 768px)'\n"
    if visibility not in card or 'solar-house.png' not in source[mobile:end]:
        raise ValueError('Unexpected energy card layout')
    card = card.replace(visibility, '')
    # Keep the live labels above decorative images on all screen sizes.
    card = card.replace("          color: '#fff'", "          z-index: 2\n          color: '#fff'")
    card = card.replace('      dark_mode_filter: none', "      aspect_ratio: '2:1'\n      dark_mode_filter: none")
    return source[:start] + card + source[end:]

if __name__ == '__main__':
    Path(sys.argv[2]).write_text(patch(Path(sys.argv[1]).read_text()))

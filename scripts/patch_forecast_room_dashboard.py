"""Scoped text patch: preserve private YAML, includes and unrelated controls."""
import re

def patch(content):
    count=0
    def element(match):
        nonlocal count
        block=match.group(0)
        if not re.search(r'^        entity: sensor\.aqara_temp_humidity_sensor_(teplota|vlhkost_vzduchu)$',block,re.M):
            return block
        count+=1
        block=block.replace('- type: state-label','- type: custom:jarvis-device-status',1)
        block=re.sub(r'^        prefix:.*\n','',block,flags=re.M)
        block=block.replace('        tap_action:\n','        kind: label\n        battery_entity: sensor.aqara_temp_humidity_sensor_baterie\n        tap_action:\n',1)
        return block
    result=re.sub(r'^      - type: state-label\n(?:^ {8}[^\n]*\n|^\n)*',element,content,flags=re.M)
    if count not in (0,2):
        raise ValueError('Expected both living-room readings')
    if count==0 and result.count('battery_entity: sensor.aqara_temp_humidity_sensor_baterie')<2:
        raise ValueError('Living-room labels not found')
    return result

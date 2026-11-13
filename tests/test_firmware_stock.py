import hashlib
from pathlib import Path
import tempfile
import unittest
import yaml
from app.firmware import FirmwareStore
from app.policy import APIError

TARGET='home-assistant-voice-0a8bde.yaml'
SOURCE='''substitutions:
  name: home-assistant-voice-0a8bde
  friendly_name: Living voice
packages:
  device: github://esphome/home-assistant-voice-pe/home-assistant-voice.yaml
esphome:
  name: ${name}
  name_add_mac_suffix: false
  on_boot:
    - logger.log: CUSTOM_BOOT
wifi:
  ssid: !secret wifi_ssid
  password: !secret WIFI_SENTINEL
  manual_ip:
    static_ip: 192.168.1.50
    gateway: 192.168.1.1
    subnet: 255.255.255.0
api:
  encryption:
    key: !secret API_SENTINEL
  on_client_connected:
    - logger.log: CUSTOM_API
ota:
  - platform: esphome
    id: ota_esphome
    password: !secret OTA_SENTINEL
micro_wake_word:
  models:
    - id: jarvis_cz
      model: private.json
voice_assistant:
  on_end:
    - logger.log: CUSTOM_VOICE
'''

class StockRecoveryTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.root=Path(self.tmp.name);self.path=self.root/'esphome'/TARGET
  self.path.parent.mkdir();self.path.write_text(SOURCE)
  self.store=FirmwareStore(self.root,[TARGET])
 def args(self):
  return dict(target=TARGET,package_sha='a'*40,expected_revision=hashlib.sha256(self.path.read_bytes()).hexdigest())
 def stage(self,args=None):
  self.assertTrue(callable(getattr(self.store,'stage_stock',None)), 'Missing bounded stock firmware recovery')
  return self.store.stage_stock(args or self.args())
 def test_removes_custom_runtime_preserves_private_connectivity_and_identity(self):
  result=self.stage();text=self.path.read_text()
  for sentinel in ['WIFI_SENTINEL','API_SENTINEL','OTA_SENTINEL','192.168.1.50','home-assistant-voice-0a8bde']:
   self.assertIn(sentinel,text)
  for removed in ['CUSTOM_BOOT','CUSTOM_API','CUSTOM_VOICE','private.json','micro_wake_word:']:
   self.assertNotIn(removed,text)
  self.assertIn('home-assistant-voice.yaml@'+'a'*40,text)
  doc=yaml.compose(text);sections={k.value:v for k,v in doc.value}
  ota={k.value:v for k,v in sections['ota'].value[0].value}
  self.assertEqual(ota['id'].tag,'!extend')
  self.assertIn('friendly_name: ${friendly_name}',text)
  self.assertFalse(result['activation_performed'])
  self.assertNotIn('SENTINEL',str(result))
  self.assertEqual(self.store.metadata(TARGET)['models'],[])
  self.assertEqual(self.store.metadata(TARGET)['reference_profile']['public_voice_package']['ref'],'a'*40)
 def test_stale_revision_and_nonimmutable_source_do_not_write(self):
  for patch in [{'expected_revision':'0'*64},{'package_sha':'dev'},{'target':'other.yaml'},{'package_sha':'https://evil'}]:
   args=self.args();args.update(patch)
   with self.assertRaises(APIError):self.stage(args)
   self.assertEqual(self.path.read_text(),SOURCE)
 def test_hidden_network_fast_connect_and_fixed_identity_are_preserved(self):
  self.path.write_text(SOURCE.replace('wifi:\n','wifi:\n  fast_connect: true\n'))
  self.stage();self.assertIn('fast_connect: true',self.path.read_text())
  for original in [SOURCE.replace('name: home-assistant-voice-0a8bde','name: other-device'), SOURCE.replace('name_add_mac_suffix: false','name_add_mac_suffix: true'),SOURCE.replace('  name_add_mac_suffix: false\n','')]:
   self.path.write_text(original)
   with self.assertRaises(APIError):self.stage()
   self.assertEqual(self.path.read_text(),original)
 def test_existing_api_port_and_ota_credentials_survive_package_merge(self):
  self.path.write_text(SOURCE.replace('api:\n','api:\n  port: 6054\n').replace('id: ota_esphome','id: private_ota'))
  self.stage();text=self.path.read_text()
  self.assertIn('port: 6054',text)
  self.assertIn('!extend',text)
  self.assertNotIn('id: private_ota',text)
  self.assertIn('password: !secret \'OTA_SENTINEL\'',text)
 def test_ota_encryption_is_retained_and_malformed_root_is_rejected(self):
  self.path.write_text(SOURCE.replace('    password: !secret OTA_SENTINEL','    encryption:\n      key: !secret OTA_ENCRYPTION'))
  self.stage();self.assertIn('OTA_ENCRYPTION',self.path.read_text())
  for broken in ['hello','- a\n- b\n','[]']:
   self.path.write_text(broken)
   with self.assertRaises(APIError):self.store.metadata(TARGET)
 def test_ambiguous_yaml_or_missing_connectivity_never_rewritten(self):
  for source in [SOURCE+'wifi: {}\n',SOURCE.replace('wifi:\n','wifi_bad:\n'),SOURCE.replace('key: !secret API_SENTINEL','no_key: invalid'),SOURCE.replace('ssid: !secret wifi_ssid','ssid: &ssid example\n  use_address: *ssid')]:
   self.path.write_text(source)
   with self.assertRaises(APIError):self.stage()
   self.assertEqual(self.path.read_text(),source)

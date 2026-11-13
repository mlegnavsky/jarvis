import asyncio
import tempfile
import unittest
from pathlib import Path
from app.policy import validate_action, validate_current_state, APIError
from app.actions import Actions
from app.voice import VoiceBridge

class Audit:
 def write(self,*args):pass

class HA:
 def __init__(self):
  self.value={'entity_id':'select.voice_end','state':'Default','attributes':{'options':['Default','Aggressive']}}
  self.calls=[]
 async def state(self,entity):return dict(self.value,entity_id=entity)
 async def service(self,domain,name,data):
  self.calls.append((domain,name,data));self.value['state']=data.get('option',self.value['state']);return []
 async def request(self,method,path,body=None):return [self.value]

class VoicePolicyTests(unittest.TestCase):
 def opts(self,service,entity):return {'writes_enabled':True,'allowed_entities':[entity],'allowed_services':[service]}
 def test_select_checks_fresh_options_and_exact_payload(self):
  b={'service':'select.select_option','entity_id':'select.voice','data':{'option':'Aggressive'}}
  validate_action(b,self.opts(b['service'],b['entity_id']))
  validate_current_state(b['service'],b['data'],{'state':'Default','attributes':{'options':['Aggressive']}})
  with self.assertRaises(APIError):validate_current_state(b['service'],b['data'],{'state':'Default','attributes':{'options':['Default']}})
  with self.assertRaises(APIError):validate_action({**b,'data':{'option':'Aggressive','other':1}},self.opts(b['service'],b['entity_id']))
 def test_volume_bounds_and_boolean_rejected(self):
  for n in [-.1,.81,float('nan'),True]:
   with self.assertRaises(APIError):validate_action({'service':'media_player.volume_set','entity_id':'media_player.homepod','data':{'volume_level':n}},self.opts('media_player.volume_set','media_player.homepod'))
  validate_action({'service':'media_player.volume_set','entity_id':'media_player.homepod','data':{'volume_level':.65}},self.opts('media_player.volume_set','media_player.homepod'))
 def test_number_obeys_device_range_and_step(self):
  with self.assertRaises(APIError):validate_current_state('number.set_value',{'value':2.5},{'state':'1','attributes':{'min':0,'max':3,'step':1}})
 def test_unlisted_voice_target_is_denied(self):
  with self.assertRaises(APIError):validate_action({'service':'select.select_option','entity_id':'select.secret','data':{'option':'x'}},self.opts('select.select_option','select.voice'))

class VoiceBridgeTests(unittest.IsolatedAsyncioTestCase):
 async def asyncSetUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.ha=HA();self.options={'writes_enabled':True,'maintenance_enabled':True,'allowed_entities':['select.voice_end','jarvis_voice_diagnostics.system'],'allowed_services':['select.select_option','jarvis_voice_diagnostics.arm_capture']}
  self.actions=Actions(self.ha,self.options,Path(self.tmp.name),Audit())
  self.bridge=VoiceBridge(self.ha,self.options,self.actions,None)
 async def test_change_verifies_and_retries_once(self):
  args={'action':'change','entity_id':'select.voice_end','service':'select.select_option','data':{'option':'Aggressive'}}
  a=await self.bridge.invoke(args,'voice-test');b=await self.bridge.invoke(args,'voice-test')
  self.assertTrue(a['target_state_verified']);self.assertTrue(b['replayed']);self.assertEqual(len(self.ha.calls),1)
 async def test_read_returns_options_without_transcripts_or_keys(self):
  self.ha.value['attributes'].update(api_key='secret',transcript='private')
  r=await self.bridge.invoke({'action':'status'},'read');self.assertEqual(r['entities'][0]['attributes'],{'options':['Default','Aggressive']})
 async def test_recording_requires_explicit_consent_and_empty_service_body(self):
  args={'action':'change','entity_id':'jarvis_voice_diagnostics.system','service':'jarvis_voice_diagnostics.arm_capture','data':{}}
  with self.assertRaises(APIError):await self.bridge.invoke(args,'no-consent')
  args['data']={'confirm_recording':True}
  result=await self.bridge.invoke(args,'capture-consented');self.assertTrue(result['accepted'])
  await self.bridge.invoke(args,'capture-consented');self.assertEqual(len(self.ha.calls),1)
  self.assertEqual(self.ha.calls[0],('jarvis_voice_diagnostics','arm_capture',{}))
 async def test_voice_route_cannot_control_light_or_arbitrary_service(self):
  with self.assertRaises(APIError):await self.bridge.invoke({'action':'change','entity_id':'light.test','service':'light.turn_on','data':{}},'bad')

 async def test_stale_value_is_not_reported_as_verified(self):
  async def no_update(domain,name,data):self.ha.calls.append((domain,name,data));return []
  self.ha.service=no_update;self.actions.confirmation_timeout=.01
  r=await self.bridge.invoke({'action':'change','entity_id':'select.voice_end','service':'select.select_option','data':{'option':'Aggressive'}},'stale')
  self.assertFalse(r['target_state_verified'])
 async def test_recording_boolean_one_does_not_count_as_consent(self):
  with self.assertRaises(APIError):await self.bridge.invoke({'action':'change','entity_id':'jarvis_voice_diagnostics.system','service':'jarvis_voice_diagnostics.arm_capture','data':{'confirm_recording':1}},'int-consent')
 async def test_diagnostic_content_does_not_leak_transcript(self):
  import json
  class Admin:
   async def read(self,q,path):
    return {'content':json.dumps({'runs':[{'transcript':'private words','timings_s':{'intent':1}}],'capture_expires_at':None,'speech_volume':.65})}
  self.bridge.admin=Admin()
  r=await self.bridge.invoke({'action':'diagnostics'},'diag');self.assertNotIn('private words',str(r));self.assertIsNone(r['capture_expires_at'])

 async def test_optional_missing_output_does_not_hide_voice_timings(self):
  import json
  class Admin:
   async def read(self,q,path):
    return {'content':None if 'homepod' in path else json.dumps({'runs':[{'timings_s':{'intent':1}}]})}
  self.bridge.admin=Admin();r=await self.bridge.invoke({'action':'diagnostics'},'missing')
  self.assertTrue(r['partial']);self.assertEqual(r['runs'][0]['timings_s']['intent'],1)
  self.assertEqual(r['reports']['output'],'unavailable')
 async def test_malformed_reports_are_reported_without_crash_or_raw_content(self):
  class Admin:
   async def read(self,q,path):return {'content':'private broken JSON'}
  self.bridge.admin=Admin();r=await self.bridge.invoke({'action':'diagnostics'},'broken')
  self.assertTrue(r['partial']);self.assertNotIn('private broken JSON',str(r))

import unittest
from types import SimpleNamespace
from app import voice_settings
from app.policy import APIError


class EndpointTests(unittest.IsolatedAsyncioTestCase):
 def setup_admin(self):
  state={'entity_id':'select.end','state':'default','attributes':{'options':['default','relaxed','aggressive']}}
  registry=[{'entity_id':'select.end','platform':'esphome','unique_id':'mac-vad_sensitivity','device_id':'voice'},
   {'entity_id':'select.assistant','platform':'esphome','unique_id':'mac-pipeline','device_id':'voice'}]
  effects=[]
  class Sup:
   async def registry(self,kind):return registry
   async def request(self,method,path,body=None):
    if method=='POST':effects.append(body);state['state']=body['option'];return []
    return state
  return SimpleNamespace(sup=Sup(),options={'allowed_entities':['select.assistant']},remember=lambda *a:None),effects,registry

 async def test_native_endpoint_setting_is_cas_bound_and_read_back(self):
  self.assertTrue(callable(getattr(voice_settings,'endpoint',None)))
  admin,effects,_=self.setup_admin()
  before=await voice_settings.endpoint(admin,'select.end')
  result=await voice_settings.endpoint_change(admin,'key',{'entity_id':'select.end','option':'aggressive','expected_revision':before['revision']})
  self.assertTrue(result['verified']);self.assertEqual(result['state'],'aggressive')
  self.assertEqual(effects,[{'entity_id':'select.end','option':'aggressive'}])
  with self.assertRaises(APIError):await voice_settings.endpoint_change(admin,'stale',{'entity_id':'select.end','option':'default','expected_revision':before['revision']})
  self.assertEqual(len(effects),1)

 async def test_unrelated_or_unauthorized_select_is_rejected(self):
  self.assertTrue(callable(getattr(voice_settings,'endpoint',None)))
  admin,effects,registry=self.setup_admin()
  registry[0]['unique_id']='other_setting'
  with self.assertRaises(APIError):await voice_settings.endpoint(admin,'select.end')
  registry[0]['unique_id']='mac-vad_sensitivity';admin.options['allowed_entities']=[]
  with self.assertRaises(APIError):await voice_settings.endpoint(admin,'select.end')
  self.assertEqual(effects,[])

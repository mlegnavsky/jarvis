import unittest
from types import SimpleNamespace as NS
from room_commands import resolve,execute
from managed_sources.voice_common import parse_command
from managed_sources import voice_common

AREAS=[{'id':'living','name':'Obývák'},{'id':'jidelna','name':'Dětský pokoj'}]
LIGHTS=[{'entity_id':'light.living','area_id':'living'},{'entity_id':'light.child','area_id':'jidelna'}]

class NaturalTests(unittest.IsolatedAsyncioTestCase):
 def test_polite_requests_keep_child_room_and_action(self):
  for text in ('Zhasni v dětském pokoji','Ano, zhasni světlo v dětském pokoji.','Můžeš prosím zhasnout v dětském pokoji?','Zhasni prosím v dětském pokoji','Prosím tě, zhasni v dětském pokoji'):
   with self.subTest(text=text):
    request=resolve(text,'living',AREAS,LIGHTS)
    self.assertIsNotNone(request);self.assertEqual(request['entity_ids'],['light.child'])
    self.assertEqual(request['service'],'turn_off')
 async def test_accepted_light_is_silent_when_device_state_lags(self):
  calls=[]
  async def call(*args,**kwargs):calls.append((args,kwargs))
  hass=NS(data={},services=NS(async_call=call),states=NS(get=lambda entity:NS(state='on')))
  reply=await execute(hass,resolve('zhasni v dětském pokoji','living',AREAS,LIGHTS),None)
  self.assertEqual(reply,'');self.assertEqual(calls[0][0],('light','turn_off',{'entity_id':['light.child']}))
  self.assertEqual(hass.data['jarvis_light_command_observations'][-1]['status'],'accepted_pending_state')
 async def test_service_error_still_has_one_short_error(self):
  async def call(*args,**kwargs):raise RuntimeError('device offline')
  hass=NS(data={},services=NS(async_call=call))
  reply=await execute(hass,resolve('zhasni','living',AREAS,LIGHTS),None)
  self.assertTrue(reply);self.assertNotIn('Místo:',reply)
 def test_examples_negations_and_conditional_requests_do_not_execute(self):
  for text in ('Nezhasínej v dětském pokoji','Když řeknu zhasni v dětském pokoji','Můžeš vysvětlit slovo zhasni?','„Zhasni v dětském pokoji“','Můžeš zhasnout až za minutu?'):
   self.assertIsNone(parse_command(text),text)
 def test_activation_hint_preserves_full_suffix_and_explicit_verb(self):
  complete=getattr(voice_common,'complete_light_utterance',lambda *a:None)
  for prefix,text,voiced,want in [('zhasni','v dětském pokoji',1.,'zhasni v detskem pokoji'),('rozsviť','Zhasni v dětském pokoji',1.,'zhasni v detskem pokoji'),('zhasni','',0.,'zhasni'),('zhasni','context:',0.,'zhasni'),('zhasni','',1.,''),('zhasni','context:',1.,''),('zhasni','odemkni dveře',1.,''),('zhasni','„v dětském pokoji“',1.,''),('zhasni','v dětském pokoji a pak v obýváku',2.,'')]:
   with self.subTest(text=text):self.assertEqual(complete(prefix,text,allow_bare=voiced==0),want)

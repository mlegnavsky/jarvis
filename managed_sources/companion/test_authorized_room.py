import unittest
from types import SimpleNamespace as NS
from room_commands import resolve, execute

class AuthorizedRoomTests(unittest.IsolatedAsyncioTestCase):
 async def test_missing_integration_cannot_fall_back_to_unprotected_light(self):
  calls=[]
  async def service(*a,**kw):calls.append(a)
  hass=NS(data={},services=NS(async_call=service),states=NS(get=lambda e:NS(state='off')))
  req=resolve('zhasni','obyvak',[{'id':'obyvak','name':'Obývák'}],[{'entity_id':'light.room','area_id':'obyvak'}])
  result=await execute(hass,req,None,user=NS(text='zhasni',device_id='mic'))
  self.assertEqual(calls,[])
 async def test_lock_target_cannot_be_changed_with_valid_domain_service(self):
  calls=[]
  async def service(*a,**kw):calls.append(a)
  speaker=NS(enforce=True,device=lambda u:'mic',gate=NS(consume=lambda *a:True))
  hass=NS(data={'jarvis_speaker_identity':speaker},services=NS(async_call=service),states=NS(get=lambda e:NS(state='unlocked')))
  req=resolve('odemkni','obyvak',[],[{'entity_id':'lock.vstup_zamek_vchod'}]);req['entity_ids']=['lock.other_door']
  await execute(hass,req,None,user=NS(text='odemkni',device_id='mic'),token='token')
  self.assertEqual(calls,[])
 def test_entrance_lock_is_explicit_and_exposed(self):
  req=resolve('odemkni','obyvak',[],[{'entity_id':'lock.vstup_zamek_vchod'}])
  self.assertEqual(req['domain'],'lock');self.assertEqual(req['service'],'unlock')
  self.assertEqual(req['entity_ids'],['lock.vstup_zamek_vchod'])
 async def test_missing_proof_causes_zero_service_calls(self):
  calls=[]
  async def service(*a,**kw):calls.append(a)
  speaker=NS(enforce=True,device=lambda u:'mic',gate=NS(consume=lambda *a:False))
  hass=NS(data={'jarvis_speaker_identity':speaker},services=NS(async_call=service))
  req=resolve('odemkni','obyvak',[],[{'entity_id':'lock.vstup_zamek_vchod'}])
  result=await execute(hass,req,None,user=NS(text='odemkni'),token=None)
  self.assertEqual(calls,[]);self.assertIn('ověřen',result)

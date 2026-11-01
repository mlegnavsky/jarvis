import unittest
from types import SimpleNamespace as NS
import test_coordinator as fixtures

class FamilyCoordinatorTests(unittest.IsolatedAsyncioTestCase):
 asyncSetUp=fixtures.CoordinatorTests.asyncSetUp
 asyncTearDown=fixtures.CoordinatorTests.asyncTearDown
 async def say(self,text,number=0):
  await self.c.complete('device',bytes([number])*256000,7,text)
  return await self.c.turn(NS(text=text,device_id='device'),'conversation')
 def owner(self):
  self.c.profiles.begin('device','Martin')
  for _ in range(3):self.c.profiles.sample('device',[1,0],4)
  self.c.profiles.bootstrap_authorization('Martin');self.c.enforce=True
 async def test_verified_owner_starts_guide_and_training_commands_never_get_tokens(self):
  self.owner();r=await self.say('Nauč se nového člena rodiny')
  self.assertEqual(r['status'],'family_enrollment');self.assertFalse(r['authorized'])
  await self.say('Jsem Šarlota',1);await self.say('Ano souhlasím',2)
  async def child(pcm):return {'status':'ok','model':'campplus-aa3cfc16-v1','vector':[0,1],'windows':[], 'quality':{'status':'ok','rms':.1,'clipped_fraction':0}}
  self.c.infer=child;r=await self.say('Rozsviť v obýváku prosím',3)
  self.assertEqual(r['progress_percent'],12);self.assertNotIn('control_token',r)
  self.assertEqual(self.c.gate.grants,{})
  self.c.cancel_for(NS(device_id='device',text='Počkej'))
  self.assertEqual(self.c.family.summary()['status'],'paused')
  self.c.cancel_for(NS(device_id='device',text='Konec'))
  self.assertEqual(self.c.family.summary()['status'],'idle')
 async def test_unknown_voice_cannot_create_a_family_session(self):
  self.owner()
  async def other(pcm):return {'status':'ok','model':'campplus-aa3cfc16-v1','vector':[0,1],'windows':[]}
  self.c.infer=other;r=await self.say('Nauč se nového člena rodiny')
  self.assertFalse(r['authorized']);self.assertEqual(self.c.family.summary()['status'],'idle')

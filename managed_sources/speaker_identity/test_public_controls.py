import unittest
from types import SimpleNamespace as NS
import test_coordinator as fixtures

class PublicControlTests(unittest.IsolatedAsyncioTestCase):
 asyncSetUp=fixtures.CoordinatorTests.asyncSetUp
 asyncTearDown=fixtures.CoordinatorTests.asyncTearDown
 async def test_short_unknown_light_gets_single_use_light_only_grant(self):
  self.c.public_controls=True;self.c.enforce=True
  await self.c.complete('device',bytes(16000),.5,'Rozsviť')
  r=await self.c.turn(NS(text='Rozsviť',device_id='device'),'c')
  self.assertTrue(r['authorized']);self.assertEqual(r['status'],'public_command')
  self.assertEqual(r['effective_text'],'rozsvit')
  token=r['control_token'];targets=(('light.room',),'room')
  self.assertFalse(self.c.gate.bind(token,'device','rozsvit',('lock','unlock'),targets))
  self.assertTrue(self.c.gate.bind(token,'device','rozsvit',('light','turn_on'),targets))
  self.assertTrue(self.c.gate.consume(token,'device','rozsvit',('light','turn_on'),targets))
  self.assertFalse(self.c.gate.consume(token,'device','rozsvit',('light','turn_on'),targets))
 async def test_model_failure_does_not_block_light_but_lock_stays_protected(self):
  self.c.public_controls=True;self.c.enforce=True
  async def fail(pcm):raise RuntimeError('offline')
  self.c.infer=fail
  for text in ('Zhasni v obýváku','Odemkni'):
   await self.c.complete('device',bytes(128000),4,text)
   r=await self.c.turn(NS(text=text,device_id='device'),'c')
   self.assertEqual(r.get('authorized'),text.startswith('Zhasni'))
 async def test_unknown_conversation_is_not_a_voice_rejection(self):
  self.c.public_controls=True;self.c.enforce=True
  await self.c.complete('device',bytes(16000),.5,'Jak se máš?')
  r=await self.c.turn(NS(text='Jak se máš?',device_id='device'),'c')
  self.assertNotIn('local_reply',r);self.assertFalse(r.get('authorized',False))
 async def test_public_command_does_not_wait_for_model(self):
  import asyncio
  self.c.public_controls=True;self.c.enforce=True
  entered=asyncio.Event();release=asyncio.Event()
  async def infer(pcm):entered.set();await release.wait();return {'status':'unavailable'}
  self.c.infer=infer
  await asyncio.wait_for(self.c.complete('device',bytes(128000),4,'Rozsviť',playback=False),.5)
  r=await asyncio.wait_for(self.c.turn(NS(text='Rozsviť',device_id='device'),'c'),.5)
  self.assertTrue(r['authorized'])
  await asyncio.wait_for(entered.wait(),.5);release.set()
  await asyncio.gather(*self.c.learning_tasks)
 async def test_known_unprivileged_profile_is_personalization_only(self):
  self.c.profiles.begin('device','Petr')
  for _ in range(3):self.c.profiles.sample('device',[1.,0.],4)
  self.c.public_controls=True;self.c.enforce=True
  await self.c.complete('device',bytes(128000),4,'Co si o mně pamatuješ?')
  r=await self.c.turn(NS(text='Co si o mně pamatuješ?',device_id='device'),'c')
  self.assertNotEqual(r['status'],'recognized')
  self.assertFalse(r['authorized'])
  self.assertNotIn('memory_id',r);self.assertNotIn('profile',r)

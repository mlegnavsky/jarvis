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
 async def test_stt_infinitive_skips_identity_model_and_gets_light_only_grant(self):
  import asyncio
  self.c.public_controls=True;self.c.enforce=True
  async def forbidden(pcm):raise AssertionError('light command must not wait for identity inference')
  self.c.infer=forbidden
  text='Rozsvítit světlo v obýváku.'
  await asyncio.wait_for(self.c.complete('device',bytes(128000),4,text,playback=True),.5)
  result=await self.c.turn(NS(text=text,device_id='device'),'c')
  self.assertEqual(result['status'],'public_command')
  self.assertEqual(result['effective_text'],'rozsvit svetlo v obyvaku')
  self.assertTrue(result['authorized'])
  token=result['control_token'];targets=(('light.living',),'living')
  self.assertTrue(self.c.gate.bind(token,'device',result['effective_text'],('light','turn_on'),targets))
  self.assertTrue(self.c.gate.consume(token,'device',result['effective_text'],('light','turn_on'),targets))
 async def test_known_unprivileged_profile_is_personalization_only(self):
  self.c.profiles.begin('device','Petr')
  for _ in range(3):self.c.profiles.sample('device',[1.,0.],4)
  self.c.public_controls=True;self.c.enforce=True
  await self.c.complete('device',bytes(128000),4,'Co si o mně pamatuješ?')
  r=await self.c.turn(NS(text='Co si o mně pamatuješ?',device_id='device'),'c')
  self.assertNotEqual(r['status'],'recognized')
  self.assertFalse(r['authorized'])
  self.assertNotIn('memory_id',r);self.assertNotIn('profile',r)
 async def test_one_contract_runs_real_all_house_grant_and_room_execution(self):
  import importlib.util
  from pathlib import Path
  path=Path(__file__).parents[1]/'companion'/'room_commands.py'
  spec=importlib.util.spec_from_file_location('contract_room',path)
  room=importlib.util.module_from_spec(spec);spec.loader.exec_module(room)
  self.c.public_controls=True;self.c.enforce=True
  areas=[{'id':'living','name':'Obývák'}]
  exposed=[{'entity_id':'light.living','area_id':'living'},{'entity_id':'light.child','area_id':'child'},{'entity_id':'switch.heater','area_id':'living'}]
  for text in ('Zhasni všude','Jarvisi, prosím vypni všechna světla'):
   calls=[]
   async def call(*args,**kwargs):calls.append(args)
   hass=NS(data={'jarvis_speaker_identity':self.c},services=NS(async_call=call),states=NS(get=lambda entity:NS(state='off')))
   await self.c.complete('device',bytes(16000),.5,text)
   result=await self.c.turn(NS(text=text,device_id='device'),'c')
   user=NS(text=result['effective_text'],device_id='device')
   request=room.resolve(user.text,'living',areas,exposed)
   targets=(tuple(request['entity_ids']),request['area_id']);action=('light','turn_off')
   self.assertTrue(self.c.gate.bind(result['control_token'],'device',user.text,action,targets))
   reply=await room.execute(hass,request,None,user=user,token=result['control_token'])
   self.assertEqual(reply,'');self.assertEqual(calls[0][2]['entity_id'],['light.child','light.living'])
   self.assertNotIn('switch.heater',str(calls))
   self.assertFalse(self.c.gate.consume(result['control_token'],'device',user.text,action,targets))
 async def test_quoted_profile_command_cannot_mutate_even_recognized_owner(self):
  self.c.profiles.begin('device','Martin')
  for _ in range(3):self.c.profiles.sample('device',[1.,0.],4)
  self.c.profiles.bootstrap_authorization('Martin');self.c.public_controls=True;self.c.enforce=True
  text='„Smaž můj hlasový profil“'
  await self.c.complete('device',bytes(128000),4,text)
  r=await self.c.turn(NS(text=text,device_id='device'),'c')
  self.assertEqual(self.c.profiles.count(),1)
  self.assertNotIn('control_token',r)

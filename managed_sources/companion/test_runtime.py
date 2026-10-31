import asyncio
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace as NS
import unittest
from runtime import CompanionRuntime
from memory import MemoryStore, fictional_probe, finish_response
from awareness import ConversationAwareness

class RuntimeTests(unittest.IsolatedAsyncioTestCase):
 async def asyncSetUp(self):
  self.folder=tempfile.TemporaryDirectory()
  async def executor(fn,*args):return await asyncio.to_thread(fn,*args)
  async def account(uid):return NS(id=uid,name='Martin',is_active=True,is_system_generated=False)
  self.hass=NS(config=NS(path=lambda *parts:str(Path(self.folder.name).joinpath(*parts))),
               auth=NS(async_get_user=account),async_add_executor_job=executor)
  self.runtime=CompanionRuntime(self.hass,'test-agent')
 async def asyncTearDown(self):self.folder.cleanup()
 def user(self,text,device='satellite',uid=None):
  return NS(text=text,device_id=device,context=NS(user_id=uid))
 async def test_guest_household_note_is_not_persisted(self):
  turn=await self.runtime.prepare(self.user('Zapamatuj si pro domácnost: Testovací klíč je zelený.'),'guest')
  self.assertFalse(self.runtime.store.context('household')['notes'])
  self.assertIn('rozhovoru',turn.local_reply)
 async def test_anicka_confirms_saved_and_deleted_notes_in_feminine_form(self):
  saved=await self.runtime.prepare(self.user('Zapamatuj si: Zkušební poznámka.',None,'a'),'c')
  self.assertEqual(saved.local_reply,'Uložila jsem si tvoji poznámku.')
  removed=await self.runtime.prepare(self.user('Zapomeň moje poznámky',None,'a'),'c')
  self.assertEqual(removed.local_reply,'Smazala jsem tvoje poznámky a témata ze své paměti.')
  self.assertFalse(removed.store.context(removed.principal)['notes'])
 async def test_authenticated_note_survives_restart_and_is_scoped(self):
  await self.runtime.prepare(self.user('Zapamatuj si: Modrý drak Róza.',None,'a'),'c')
  other=CompanionRuntime(self.hass,'test-agent')
  own=await other.prepare(self.user('Co si pamatuješ?',None,'a'),'new')
  stranger=await other.prepare(self.user('Co si pamatuješ?',None,'b'),'else')
  self.assertIn('Modrý drak',own.prompt)
  self.assertNotIn('Modrý drak',stranger.prompt)
 async def test_voice_introduction_does_not_authorize_private_memory(self):
  self.runtime.store.note('auth:a','Tajná osobní poznámka.')
  intro=await self.runtime.prepare(self.user('Jsem Martin',uid='a'),'voice')
  self.assertEqual(intro.address,'Martine')
  self.assertFalse(intro.verified)
  self.assertNotIn('Tajná osobní',intro.prompt)
 async def test_changed_guest_introduction_forgets_previous_guest_notes(self):
  await self.runtime.prepare(self.user('Jsem Martin'),'c')
  await self.runtime.prepare(self.user('Zapamatuj si: Můj drak je modrý.'),'c')
  changed=await self.runtime.prepare(self.user('Jsem Iris'),'c')
  self.assertTrue(changed.reset_history)
  self.assertNotIn('Můj drak',changed.prompt)
 async def test_forget_resets_notes_and_history(self):
  await self.runtime.prepare(self.user('Zapamatuj si: Můj drak je modrý.'),'c')
  turn=await self.runtime.prepare(self.user('Zapomeň moje poznámky'),'c')
  self.assertTrue(turn.reset_history)
  self.assertFalse(turn.store.context(turn.principal)['notes'])
 async def test_new_account_on_same_conversation_resets_history(self):
  await self.runtime.prepare(self.user('Ahoj',None,'a'),'c')
  turn=await self.runtime.prepare(self.user('Ahoj',None,'b'),'c')
  self.assertTrue(turn.reset_history)
 async def test_recognized_voice_has_own_durable_notes_without_ha_authentication(self):
  class Speaker:
   async def turn(self,*args):return {'status':'recognized','profile':'martin','name':'Martin','score':.96}
  self.hass.data={'jarvis_speaker_identity':Speaker()}
  turn=await self.runtime.prepare(self.user('Zapamatuj si: Můj drak je zelený.'),'c')
  self.assertEqual(turn.principal,'voice:martin')
  self.assertFalse(turn.verified)
  self.assertEqual(turn.address,'Martine')
  self.assertIn('hlasov',turn.local_reply)
  self.assertTrue(self.runtime.store.context('voice:martin')['notes'])
  self.assertFalse(self.runtime.store.context('auth:martin')['notes'])
 async def test_unknown_voice_after_known_voice_does_not_inherit_personal_context(self):
  class Speaker:
   result={'status':'recognized','profile':'martin','name':'Martin','score':.96}
   async def turn(self,*args):return self.result
  speaker=Speaker();self.hass.data={'jarvis_speaker_identity':speaker}
  await self.runtime.prepare(self.user('Zapamatuj si: Můj drak je zelený.'),'c')
  speaker.result={'status':'unknown'}
  turn=await self.runtime.prepare(self.user('Jak se dnes máš?'),'c')
  self.assertTrue(turn.reset_history)
  self.assertIsNone(turn.address)
  self.assertNotIn('Můj drak',turn.prompt)
 async def test_voice_enrollment_returns_local_reply_without_pretending_authenticated_identity(self):
  class Speaker:
   async def turn(self,*args):return {'status':'enrolling','local_reply':'Potřebuji ještě dvě ukázky.'}
  self.hass.data={'jarvis_speaker_identity':Speaker()}
  turn=await self.runtime.prepare(self.user('Zkušební věta pro hlasový profil.'),'c')
  self.assertEqual(turn.local_reply,'Potřebuji ještě dvě ukázky.')
  self.assertFalse(turn.verified)
 async def test_unknown_voice_never_reuses_guest_private_context(self):
  class Speaker:
   async def turn(self,*args):return {'status':'unknown'}
  self.hass.data={'jarvis_speaker_identity':Speaker()}
  await self.runtime.prepare(self.user('Jsem Martin'),'c')
  note=await self.runtime.prepare(self.user('Zapamatuj si: Martinova soukromá poznámka.'),'c')
  self.assertFalse(note.store.context(note.principal)['notes'])
  other=await self.runtime.prepare(self.user('Jsem Iris'),'c')
  self.assertTrue(other.reset_history)
  self.assertNotIn('Martinova',other.prompt)

class PolicyTests(unittest.TestCase):
 def test_fictional_native_probe(self):self.assertTrue(fictional_probe()['passed'])
 def test_joke_filter_preserves_failure_after_misplaced_joke(self):
  self.assertEqual(finish_response('Hotovo. ⟦vtip⟧Haha.⟦/vtip⟧ Ventil selhal.',MemoryStore(),'guest',False),'Hotovo.  Ventil selhal.')
 def test_delay_once_per_episode_and_refusal(self):
  clock=[1793188800.]
  a=ConversationAwareness(clock=lambda:clock[0])
  stove={'entity_id':'switch.test','name':'Sporák','state':'on','last_changed':'2026-10-28T12:00:00+00:00'}
  self.assertFalse(a.context('c',[stove],'Jak se máš?')['optional_observation_allowed'])
  clock[0]+=299
  self.assertFalse(a.context('c',[stove],'Co nového?')['optional_observation_allowed'])
  clock[0]+=1
  self.assertTrue(a.context('c',[stove],'Co nového?')['optional_observation_allowed'])
  clock[0]+=2400
  self.assertFalse(a.context('c',[stove],'Co nového?')['optional_observation_allowed'])
  b=ConversationAwareness(clock=lambda:clock[0])
  b.context('c',[stove],'Nechci pomoci.')
  clock[0]+=301
  self.assertFalse(b.context('c',[stove],'Co nového?')['optional_observation_allowed'])
 def test_unknown_and_direct_command_never_offer(self):
  a=ConversationAwareness()
  self.assertFalse(a.context('c',[],'Co nového?')['optional_observation_allowed'])
  self.assertFalse(a.context('c',[],'Zhasni světlo')['optional_observation_allowed'])


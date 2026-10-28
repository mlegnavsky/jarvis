import asyncio
from pathlib import Path
import tempfile
from types import SimpleNamespace as NS
import unittest
from coordinator import Coordinator,admin_forget

class CoordinatorTests(unittest.IsolatedAsyncioTestCase):
 async def asyncSetUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.time=100
  async def executor(fn,*args):return await asyncio.to_thread(fn,*args)
  async def infer(pcm):return {'status':'ok','vector':[1.,0.],'windows':[],'model':'campplus-aa3cfc16-v1'}
  self.c=Coordinator(NS(async_add_executor_job=executor),Path(self.tmp.name)/'voices.sqlite',infer,clock=lambda:self.time)
 async def asyncTearDown(self):self.tmp.cleanup()
 async def say(self,text,conversation='c'):
  await self.c.complete('device',bytes(128000),4,text)
  return await self.c.turn(NS(text=text,device_id='device'),conversation)
 async def test_explicit_enrollment_and_recognition(self):
  result=await self.say('Nauč se můj hlas. Jsem Martin.')
  self.assertIn('ukáz',result['local_reply'])
  for n in range(3):result=await self.say('Tohle je moje delší věta číslo '+str(n))
  self.assertEqual(result['status'],'enrolled')
  known=await self.say('Jak se máš dnes odpoledne?')
  self.assertEqual(known['profile'],'martin')
  self.assertNotIn('vector',known)
 async def test_result_is_one_shot_and_transcript_scoped(self):
  await self.c.complete('device',bytes(128000),4,'První věta')
  result=await self.c.turn(NS(text='Jiná věta',device_id='device'),'c')
  self.assertIsNone(result)
  self.assertIsNone(await self.c.turn(NS(text='První věta',device_id='device'),'c'))
 async def test_late_audio_result_not_reused(self):
  await self.c.complete('device',bytes(128000),4,'Ahoj')
  self.time+=16
  self.assertIsNone(await self.c.turn(NS(text='Ahoj',device_id='device'),'c'))
 async def test_explicit_delete_requires_current_recognition(self):
  result=await self.say('Smaž můj hlasový profil')
  self.assertNotIn('deleted_profile',result)
 async def test_backend_failure_is_nonfatal_and_no_name_is_guessed(self):
  async def fail(pcm):raise TimeoutError()
  self.c.infer=fail
  result=await self.say('Jak se dnes máš?')
  self.assertEqual(result['status'],'unavailable')
  self.assertNotIn('profile',result)
 async def test_administrative_forget_rejects_unprivileged_user(self):
  async def user(uid):return NS(is_admin=False,is_active=True,is_system_generated=False)
  self.c.hass.auth=NS(async_get_user=user)
  with self.assertRaises(PermissionError):await admin_forget(self.c.hass,'ordinary','Martin',self.c,None)
 async def test_administrative_forget_allows_owner_and_clears_memory_id(self):
  await self.say('Nauč se můj hlas. Jsem Martin.')
  for n in range(3):await self.say('Další dlouhá věta pro učení '+str(n))
  memory_id=self.c.profiles.identify([1.,0.])['memory_id'];cleared=[]
  async def user(uid):return NS(is_admin=True,is_active=True,is_system_generated=False)
  self.c.hass.auth=NS(async_get_user=user)
  await admin_forget(self.c.hass,'owner','Martin',self.c,lambda key:cleared.append(key))
  self.assertEqual(cleared,[memory_id]);self.assertEqual(self.c.profiles.count(),0)

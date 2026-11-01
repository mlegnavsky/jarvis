import asyncio
from pathlib import Path
import tempfile
from types import SimpleNamespace as NS
import unittest
from coordinator import Coordinator,admin_forget

class CoordinatorTests(unittest.IsolatedAsyncioTestCase):
 async def test_interleaved_followup_cannot_replace_prior_turn_evidence(self):
  self.c.enforce=True
  await self.c.complete('device',bytes(128000),4,'První dlouhá věta')
  entered=asyncio.Event();release=asyncio.Event()
  async def paused_executor(fn,*args):
   entered.set();await release.wait()
   return fn(*args)
  self.c.hass.async_add_executor_job=paused_executor
  first=asyncio.create_task(self.c.turn(NS(text='První dlouhá věta',device_id='device'),'c'))
  await entered.wait()
  await self.c.complete('device',bytes(32000),.2,'context:')
  release.set();await first
  prior=self.c.recent_turns[0]
  self.assertEqual(prior['capture_number'],1)
  self.assertEqual(prior['voiced_seconds'],4)
  self.assertEqual(prior['status'],'ok')
  self.assertEqual(self.c.last['capture_number'],2)
  self.assertEqual(self.c.last['status'],'too_short')
  self.assertNotIn('matching',self.c.last)
 async def test_matching_evidence_survives_short_followup_without_private_data(self):
  self.c.enforce=True
  await self.say('Delší soukromá otázka o mém hlasu')
  original=self.c.recent_turns[0]
  self.assertIn('matching',original)
  self.assertFalse(original['authorized'])
  await self.c.complete('device',bytes(32000),.2,'context:')
  await self.c.turn(NS(text='context:',device_id='device'),'c')
  self.assertEqual(self.c.recent_turns[0],original)
  self.assertEqual(self.c.recent_turns[-1]['status'],'too_short')
  self.assertEqual(self.c.recent_turns[-1]['capture_number'],2)
  self.assertEqual(self.c.recent_turns[-1]['matching']['whole'],{'status':'too_short'})
  for i in range(20):await self.say('Soukromá věta '+str(i))
  self.assertEqual(len(self.c.recent_turns),16)
  evidence=str(self.c.recent_turns)
  for secret in ('Soukromá','device','vector','control_token','memory_id','context:'):
   self.assertNotIn(secret,evidence)
 async def test_enforced_voice_requires_authorization_even_when_name_is_recognized(self):
  await self.say('Nauč se můj hlas. Jsem Martin.')
  for n in range(3):await self.say('Ukázková věta číslo '+str(n))
  self.c.enforce=True
  result=await self.say('Zhasni')
  self.assertFalse(result['authorized'])
  self.assertIn('neprovedu',result['local_reply'])
 async def test_authorized_command_has_one_use_token_and_candidate_stays_separate(self):
  await self.say('Nauč se můj hlas. Jsem Martin.')
  for n in range(3):await self.say('Ukázková věta číslo '+str(n))
  self.c.profiles.bootstrap_authorization('Martin');self.c.enforce=True
  result=await self.say('Zhasni')
  self.assertTrue(result['authorized'])
  token=result['control_token']
  self.assertTrue(self.c.gate.consume(token,'device','Zhasni',('light','turn_off')))
  self.assertFalse(self.c.gate.consume(token,'device','Zhasni',('light','turn_off')))
 async def test_unknown_voice_cannot_start_enrollment_under_enforcement(self):
  self.c.enforce=True
  result=await self.say('Nauč se můj hlas. Jsem Martin.')
  self.assertFalse(result['authorized']);self.assertEqual(self.c.enrollment_state(),[])
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
 async def test_short_enrollment_command_starts_session_without_counting_as_sample(self):
  await self.c.complete('device',bytes(64000),1.5,'Nauč se můj hlas. Jsem Martin.')
  result=await self.c.turn(NS(text='Nauč se můj hlas. Jsem Martin.',device_id='device'),'c')
  self.assertEqual(result['status'],'enrolling')
  self.assertEqual(result['samples'],0)
  self.assertEqual(self.c.profiles.count(),0)
  for n in range(3):result=await self.say('Delší zkušební věta číslo '+str(n))
  self.assertEqual(result['status'],'enrolled')
 async def test_enrollment_without_name_returns_local_instruction_not_model_chat(self):
  result=await self.say('Nauč se můj hlas.')
  self.assertEqual(result['status'],'name_required')
  self.assertIn('Nauč se můj hlas. Jsem Martin.',result['local_reply'])
  self.assertEqual(self.c.profiles.count(),0)
  self.assertEqual(self.c.enrollment_state(),[])
 async def test_voice_status_query_reports_missing_profile_without_model(self):
  result=await self.say('Už máš otisk mého hlasu?')
  self.assertEqual(result['status'],'not_enrolled')
  self.assertEqual(result['local_reply'],'Zatím nemám uložený žádný hlasový profil. Učení ještě není dokončené.')
 async def test_result_is_one_shot_and_transcript_scoped(self):
  await self.c.complete('device',bytes(128000),4,'První věta')
  result=await self.c.turn(NS(text='Jiná věta',device_id='device'),'c')
  self.assertIsNone(result)
  self.assertIsNone(await self.c.turn(NS(text='První věta',device_id='device'),'c'))
 async def test_inconsistent_sample_retains_progress_and_reports_decision(self):
  await self.say('Nauč se můj hlas. Jsem Martin.')
  await self.say('První dost dlouhá zkušební věta.')
  async def other(pcm):return {'status':'ok','vector':[0.,1.],'model':'campplus-aa3cfc16-v1'}
  self.c.infer=other
  result=await self.say('Jiný hlas v televizi.')
  self.assertEqual(result['status'],'inconsistent')
  self.assertIn('zachovala',result['local_reply'])
  self.assertEqual(self.c.last['decision_status'],'inconsistent')
  self.assertEqual(self.c.enrollment_state()[0]['samples'],1)
  self.assertNotIn('Martin',str(self.c.enrollment_state()))
  self.assertNotIn('vector',str(self.c.enrollment_state()))
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



class MatchDiagnosticsTests(unittest.IsolatedAsyncioTestCase):
 asyncSetUp=CoordinatorTests.asyncSetUp
 asyncTearDown=CoordinatorTests.asyncTearDown
 say=CoordinatorTests.say
 async def prepare_authorized(self):
  await self.say('Nauč se můj hlas. Jsem Martin.')
  for n in range(3):await self.say('Ukázková věta číslo '+str(n))
  self.c.profiles.bootstrap_authorization('Martin');self.c.enforce=True
 async def test_window_rejection_explains_segment_problem_and_preserves_gate(self):
  await self.prepare_authorized()
  async def infer(pcm):return {'status':'ok','vector':[1.,0.],'windows':[[1.,0.],[.7,.7141428]],'model':'campplus-aa3cfc16-v1'}
  self.c.infer=infer
  result=await self.say('Toto je dostatečně dlouhá věta pro ověření hlasu.')
  self.assertFalse(result['authorized'])
  self.assertNotIn('control_token',result)
  self.assertIn('části',result['local_reply'])
  self.assertNotIn('delší',result['local_reply'])
  diag=self.c.last['matching']
  self.assertEqual(diag['whole']['status'],'recognized')
  self.assertEqual(len(diag['windows']),2)
  self.assertAlmostEqual(diag['windows'][1]['best_score'],.7,places=3)
  for private in ('vector','memory_id','martin'):
   self.assertNotIn(private,str(diag))
 async def test_repeated_unknown_voice_does_not_request_another_sentence_forever(self):
  self.c.enforce=True
  for n in range(3):result=await self.say('Neověřená věta číslo '+str(n))
  self.assertFalse(result['authorized'])
  self.assertFalse(result['retry_recommended'])
  self.assertIn('diagnostiku',result['local_reply'])
 async def test_success_resets_failure_counter(self):
  await self.prepare_authorized()
  infer=self.c.infer
  async def other(pcm):return {'status':'ok','vector':[0.,1.],'windows':[],'model':'campplus-aa3cfc16-v1'}
  self.c.infer=other
  await self.say('Cizí věta jedna');await self.say('Cizí věta dva')
  self.c.infer=infer
  self.assertTrue((await self.say('Ověřená věta'))['authorized'])
  self.c.infer=other
  self.assertTrue((await self.say('Cizí věta znovu'))['retry_recommended'])

class OwnerCalibrationCoordinatorTests(unittest.IsolatedAsyncioTestCase):
 asyncSetUp=CoordinatorTests.asyncSetUp
 asyncTearDown=CoordinatorTests.asyncTearDown
 say=CoordinatorTests.say
 async def test_admin_armed_unknown_sample_bypasses_only_collection_not_authorization(self):
  import json
  from owner_calibration import OwnerCalibration
  await self.say('Nauč se můj hlas. Jsem Martin.')
  for n in range(3):await self.say('Ukázková věta číslo '+str(n))
  self.c.profiles.bootstrap_authorization('Martin');self.c.enforce=True
  self.c.owner_calibration=OwnerCalibration(self.c.profiles,'device')
  control=Path(self.tmp.name)/'control.json'
  control.write_text(json.dumps({'request_id':'a'*32,'action':'start','profile':'Martin','issued_at':self.c.profiles.clock()}))
  self.c.owner_calibration.process_control(control)
  async def infer(pcm):return {'status':'ok','vector':[.7,.7141428],'windows':[],'model':'campplus-aa3cfc16-v1','quality':{'status':'ok','rms':.1,'clipped_fraction':0}}
  self.c.infer=infer
  result=await self.say('Zhasni světla v této místnosti.')
  self.assertEqual(result['status'],'owner_calibration');self.assertEqual(result['samples'],1)
  self.assertFalse(result['authorized']);self.assertNotIn('control_token',result)

class CalibratedStrictActionsTests(unittest.IsolatedAsyncioTestCase):
 asyncSetUp=CoordinatorTests.asyncSetUp
 asyncTearDown=CoordinatorTests.asyncTearDown
 say=CoordinatorTests.say
 async def prepare(self):
  import json
  await self.say('Nauč se můj hlas. Jsem Martin.')
  for n in range(3):await self.say('Ukázková věta číslo '+str(n))
  self.c.profiles.bootstrap_authorization('Martin');self.c.enforce=True
  identity=self.c.profiles.identify([1.,0.]);self.identity=identity
  with self.c.profiles._db() as db:
   db.execute('UPDATE voices SET samples=?',(json.dumps([[1.,0.],[.999,.04]]),))
   db.execute('INSERT INTO voice_matching_policies VALUES (?,?)',(identity['memory_id'],'top_two_mean_calibrated_v1'))
  async def low(pcm):return {'status':'ok','model':'campplus-aa3cfc16-v1','vector':[.7,.7141428],'windows':[]}
  self.c.infer=low
 async def test_calibrated_light_grant_does_not_lower_lock_floor(self):
  await self.prepare()
  self.assertIn('control_token',await self.say('Zhasni'))
  lock=await self.say('Odemkni');self.assertFalse(lock['authorized']);self.assertNotIn('control_token',lock)
 async def test_low_confidence_cannot_delete_voice_profile(self):
  await self.prepare();result=await self.say('Smaž můj hlasový profil')
  self.assertFalse(result['authorized']);self.assertEqual(self.c.profiles.count(),1)
 async def test_alias_to_unlock_cannot_bypass_strict_floor(self):
  await self.prepare();pid=self.identity['memory_id']
  self.c.pronunciation.propose(pid,'otevri','odemkni');self.c.pronunciation.confirm(pid,'otevri','odemkni')
  result=await self.say('Otevři');self.assertFalse(result['authorized']);self.assertNotIn('control_token',result)
 async def test_strong_whole_but_weaker_window_cannot_unlock(self):
  await self.prepare()
  async def mixed(pcm):return {'status':'ok','model':'campplus-aa3cfc16-v1','vector':[1.,0.],'windows':[[.7,.7141428]]}
  self.c.infer=mixed;result=await self.say('Odemkni')
  self.assertFalse(result['authorized']);self.assertNotIn('control_token',result)

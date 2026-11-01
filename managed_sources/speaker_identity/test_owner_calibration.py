import json,tempfile,unittest
from pathlib import Path
from policy import VoiceProfiles
from owner_calibration import OwnerCalibration

class OwnerCalibrationTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name);self.now=1000
  self.profiles=VoiceProfiles(self.path/'profiles.sqlite',clock=lambda:self.now)
  self.profiles.begin('mic','Martin')
  for _ in range(3):self.profiles.sample('mic',[1.,0.],4)
  self.profiles.bootstrap_authorization('Martin')
  self.voice=self.profiles.identify([1.,0.])['memory_id']
  self.c=OwnerCalibration(self.profiles,'mic');self.control=self.path/'control.json'
 def tearDown(self):self.tmp.cleanup()
 def start(self,request='a'*32):
  self.control.write_text(json.dumps({'request_id':request,'action':'start','profile':'Martin','issued_at':self.now}))
  return self.c.process_control(self.control)
 def item(self,key='u',**changes):
  return {'result':{'status':'ok','model':'campplus-aa3cfc16-v1','vector':[.7,.7141428],'quality':{'status':'ok','rms':.1,'clipped_fraction':0}},'voiced':5,'playback':False,'utterance':key,**changes}
 def test_owner_collection_accepts_unrecognized_voice_without_grant_or_profile_mutation(self):
  old=self.profiles.anchors(self.voice);self.start()
  result=self.c.collect('mic',self.item())
  self.assertEqual(result['samples'],1);self.assertFalse(result['authorized']);self.assertNotIn('control_token',result)
  self.assertEqual(old,self.profiles.anchors(self.voice));self.assertEqual(self.profiles.identify([.7,.7141428])['status'],'unknown')
  self.assertEqual(self.c.summary()['status'],'collecting')
 def test_five_samples_complete_and_stop_followup(self):
  self.start()
  for n in range(5):result=self.c.collect('mic',self.item(str(n)))
  self.assertFalse(result['retry_recommended']);self.assertEqual(result['samples'],5)
  self.assertEqual(self.c.summary()['status'],'awaiting_review')
  self.assertIsNone(self.c.collect('mic',self.item('six')))
  with self.profiles._db() as db:
   self.assertEqual(db.execute('SELECT count(*) FROM owner_calibration_samples').fetchone()[0],5)
 def test_restart_duplicate_request_and_duplicate_audio_keep_progress(self):
  self.start();self.c.collect('mic',self.item())
  self.c=OwnerCalibration(self.profiles,'mic');self.c.process_control(self.control)
  self.assertEqual(self.c.collect('mic',self.item())['samples'],1)
  self.assertEqual(self.c.summary()['samples'],1)
 def test_stale_control_and_expired_session_cannot_collect(self):
  self.start();self.now+=601
  self.assertIsNone(self.c.collect('mic',self.item()))
  self.assertEqual(self.c.summary()['status'],'expired')
  self.control.write_text(json.dumps({'request_id':'b'*32,'action':'start','profile':'Martin','issued_at':1000}))
  self.assertEqual(self.c.process_control(self.control)['status'],'rejected')
 def test_deleted_and_recreated_profile_never_inherits_session(self):
  self.start();self.profiles.forget('Martin')
  self.profiles.begin('mic','Martin')
  for _ in range(3):self.profiles.sample('mic',[1.,0.],4)
  self.assertIsNone(self.c.collect('mic',self.item()))
 def test_wrong_device_and_playback_and_quality_do_not_count(self):
  self.start();self.assertIsNone(self.c.collect('other',self.item()))
  for n,patch in enumerate(({'playback':True},{'playback':None},{'voiced':1},{'result':{'status':'unavailable'}})):
   self.start(f'{n:032x}')
   self.assertEqual(self.c.collect('mic',self.item(**patch))['samples'],0)
  self.assertEqual(self.c.summary()['samples'],0)
 def test_summary_has_no_names_vectors_or_identity_ids(self):
  self.start();self.c.collect('mic',self.item());text=str(self.c.summary())
  for private in ('Martin','martin','vector',self.voice):self.assertNotIn(private,text)
 def test_request_replay_stays_blocked_after_session_retention_eviction(self):
  self.start()
  for n in range(9):self.start(f'{n:032x}')
  self.assertEqual(self.start()['status'],'already_consumed')
 def test_invalid_future_and_symlink_requests_are_rejected(self):
  self.start();self.control.unlink()
  target=self.path/'target.json';target.write_text('{}');self.control.symlink_to(target)
  self.assertEqual(self.c.process_control(self.control)['status'],'rejected')

 def test_three_rejected_samples_pause_collection_instead_of_looping(self):
  self.start()
  for _ in range(3):result=self.c.collect('mic',self.item(playback=True))
  self.assertFalse(result['retry_recommended'])
  self.assertEqual(self.c.summary()['status'],'paused')
  self.assertIsNone(self.c.collect('mic',self.item()))
 def test_forgetting_profile_erases_its_private_calibration_samples(self):
  self.start();self.c.collect('mic',self.item());self.profiles.forget('Martin')
  with self.profiles._db() as db:
   self.assertEqual(db.execute('SELECT count(*) FROM owner_calibration_samples').fetchone()[0],0)
   self.assertEqual(db.execute('SELECT count(*) FROM owner_calibration_sessions').fetchone()[0],0)
 def test_owner_resume_preserves_four_samples_and_collects_only_missing_fifth(self):
  self.start()
  for n in range(4):self.c.collect('mic',self.item(str(n)))
  self.now+=601;self.assertEqual(self.c.summary()['status'],'expired')
  self.control.write_text(json.dumps({'request_id':'b'*32,'action':'resume','profile':'Martin','issued_at':self.now}))
  self.assertEqual(self.c.process_control(self.control)['status'],'collecting')
  self.assertEqual(self.c.summary()['samples'],4)
  self.assertEqual(self.c.collect('mic',self.item('last'))['samples'],5)
  self.assertEqual(self.c.summary()['status'],'awaiting_review')
 def test_each_new_clean_sample_refreshes_inactivity_deadline_but_duplicate_does_not(self):
  self.start();self.now+=590
  self.c.collect('mic',self.item('new'))
  self.assertEqual(self.c.summary()['expires_in_s'],600)
  self.now+=590
  self.c.collect('mic',self.item('new'))
  self.assertEqual(self.c.summary()['expires_in_s'],10)
  self.c.collect('mic',self.item('different'))
  self.assertEqual(self.c.summary()['expires_in_s'],600)
 def test_resume_without_same_existing_session_is_rejected(self):
  self.control.write_text(json.dumps({'request_id':'b'*32,'action':'resume','profile':'Martin','issued_at':self.now}))
  self.assertEqual(self.c.process_control(self.control)['status'],'rejected')
 def test_completed_session_cannot_be_resumed_or_reopened(self):
  self.start()
  for n in range(5):self.c.collect('mic',self.item(str(n)))
  self.control.write_text(json.dumps({'request_id':'b'*32,'action':'resume','profile':'Martin','issued_at':self.now}))
  self.assertEqual(self.c.process_control(self.control)['status'],'rejected')
  self.assertEqual(self.c.summary()['status'],'awaiting_review')
  self.assertEqual(self.c.summary()['samples'],5)

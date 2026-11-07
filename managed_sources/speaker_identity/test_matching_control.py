import json,unittest,math
import test_review as fixtures
from matching_control import MatchingControl

class MatchingControlTests(unittest.TestCase):
 setUp=fixtures.ReviewTests.setUp
 tearDown=fixtures.ReviewTests.tearDown
 save=fixtures.ReviewTests.save
 def request(self,action='activate',expected=None,key='a'*32,ack=True):
  self.p.clock=lambda:1000
  path=self.root/'review-control.json'
  if expected is None:expected=self.r.evaluate()['revision']
  path.write_text(json.dumps({'request_id':key,'action':action,'profile':'Martin','expected_revision':expected,'issued_at':1000,'acknowledge_replay_risk':ack}))
  return MatchingControl(self.p,self.r,path).process()
 def test_activation_and_cas_rollback_keep_stable_identity_anchors_and_permissions(self):
  anchors=self.p.anchors(self.identity['memory_id']);self.assertEqual(self.p.identify([math.cos(.82),math.sin(.82)])['status'],'unknown')
  result=self.request();self.assertEqual(result['status'],'activated')
  known=self.p.identify([math.cos(.82),math.sin(.82)]);self.assertEqual(known['memory_id'],self.identity['memory_id'])
  self.assertTrue(self.p.is_authorized(known['memory_id']));self.assertEqual(anchors,self.p.anchors(known['memory_id']))
  rollback=self.request('rollback',result['current_profile_revision'],key='b'*32)
  self.assertEqual(rollback['status'],'rolled_back');self.assertEqual(self.p.identify([math.cos(.82),math.sin(.82)])['status'],'unknown')
 def test_wrong_revision_and_missing_replay_ack_do_not_modify_profile(self):
  self.assertEqual(self.request(expected='f'*64)['status'],'rejected')
  self.assertEqual(self.request(ack=False)['status'],'rejected')
  self.assertEqual(self.p.identify([math.cos(.82),math.sin(.82)])['status'],'unknown')
 def test_same_request_is_idempotent_but_changed_body_is_rejected(self):
  result=self.request();path=self.root/'review-control.json';ctl=MatchingControl(self.p,self.r,path)
  self.assertEqual(ctl.process()['status'],'already_applied')
  body=json.loads(path.read_text());body['action']='rollback';path.write_text(json.dumps(body))
  self.assertEqual(ctl.process()['status'],'rejected')
 def test_stale_control_is_rejected_and_rejected_candidate_cannot_activate(self):
  self.request(expected='f'*64);self.p.clock=lambda:1201
  self.assertEqual(MatchingControl(self.p,self.r,self.root/'review-control.json').process()['status'],'rejected')
  with self.c.db() as db:db.execute('UPDATE owner_calibration_samples SET vector=? WHERE session=?',(json.dumps([math.cos(.8),math.sin(.8)]),f'{1:032x}'))
  self.assertEqual(self.request(key='c'*32)['status'],'rejected')
 def test_forget_erases_matching_backup_templates(self):
  self.request();self.p.forget('Martin')
  with self.p._db() as db:
   self.assertEqual(db.execute('SELECT count(*) FROM voice_matching_versions').fetchone()[0],0)
   self.assertEqual(db.execute('SELECT count(*) FROM voice_matching_policies').fetchone()[0],0)

 def test_changed_evidence_between_review_and_write_is_rejected(self):
  original=self.r.evaluate
  expected=original()['revision']
  def changed():
   result=original()
   with self.c.db() as db:db.execute('UPDATE owner_calibration_samples SET vector=? WHERE session=?',(json.dumps([0.,1.]),f'{1:032x}'))
   return result
  self.r.evaluate=changed
  self.assertEqual(self.request(expected=expected)['status'],'rejected')
  self.assertEqual(self.p.identify([math.cos(.82),math.sin(.82)])['status'],'unknown')

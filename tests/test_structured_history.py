import os,sys,tempfile,unittest
sys.path.insert(0,'managed_sources/spot_control')
from journal import Journal
from diagnostics import build_diagnostics
class StructuredHistoryTests(unittest.TestCase):
 def test_existing_history_survives_reopen_and_filtered_pagination(self):
  with tempfile.TemporaryDirectory() as d:
   path=os.path.join(d,'events.sqlite');j=Journal(path)
   a=j.append('sale_start',{'id':'one'},100);b=j.append('measurement',{'sale_id':'one'},101);c=j.append('sale_stop',{'id':'two'},102)
   j=Journal(path);page=j.page(after=0,limit=1,sale_id='one')
   self.assertEqual(page['events'][0]['id'],a);bound=page['until_id'];j.append('sale_start',{'id':'one'},103)
   nxt=j.page(after=page['next_cursor'],limit=10,until_id=bound,sale_id='one')
   self.assertEqual([e['id'] for e in nxt['events']],[b]);self.assertEqual(len(j.recent()),4)
   self.assertEqual([e['id'] for e in j.page(after=0,kind='sale_stop')['events']],[c])
 def test_validation_rejects_unbounded_bad_queries(self):
  with tempfile.TemporaryDirectory() as d:
   j=Journal(os.path.join(d,'db'))
   for args in ({'after':-1},{'limit':1001},{'kind':"x' OR 1=1"},{'sale_id':'x'*81},{'after':True}):
    with self.assertRaises(ValueError):j.page(**args)
 def test_diagnostics_distinguishes_ha_completion_from_native_proof(self):
  d=build_diagnostics({'active':False,'phase':'idle','settings':{'requested_automatic':True,'automatic':False,'inhibited':True},'diagnostic_stop':{'id':'x','reason':'health','stop_verified':True,'failure_context':{'health':{'transient_only':True,'issues':[{'code':'stale','entity_id':'soc','age_seconds':33}]}}}},100)
  self.assertEqual(d['last_stop']['id'],'x');self.assertEqual(d['last_stop']['reason'],'health');self.assertFalse(d['last_stop']['native_expiry_observed']);self.assertTrue(d['last_stop']['stop_verified']);self.assertEqual(d['last_stop']['issues'][0]['entity_id'],'soc')

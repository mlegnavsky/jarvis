import importlib.util
import json
from pathlib import Path
from types import ModuleType,SimpleNamespace
import sys
import tempfile
import unittest
from unittest.mock import patch
from journal import Journal


class HistoryViewTests(unittest.IsolatedAsyncioTestCase):
 async def asyncSetUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
  self.journal=Journal(Path(self.temp.name)/'journal.sqlite')
  self.journal.append('sale_start',{'id':'a','password':'do-not-export'},t=100)
  self.journal.append('sale_stop',{'id':'a'},t=110)
  async def executor(fn,*args):return fn(*args)
  self.hass=SimpleNamespace(async_add_executor_job=executor)
  class Base:
   def json(self,value):return value
  http=ModuleType('homeassistant.components.http');http.HomeAssistantView=Base
  with patch.dict(sys.modules,{'homeassistant':ModuleType('homeassistant'),'homeassistant.components':ModuleType('homeassistant.components'),'homeassistant.components.http':http}):
   spec=importlib.util.spec_from_file_location('history_test_view',Path('managed_sources/spot_control/history_view.py'))
   module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
  self.view=module.HistoryView(self.hass,self.journal,lambda:{'ready':True,'settings':{'password':'private'}})
 def request(self,query=None,admin=True):
  return SimpleNamespace(get=lambda key:SimpleNamespace(is_admin=admin),query=query or {})
 async def test_non_admin_is_refused_before_reading_history(self):
  result=await self.view.get(self.request(admin=False));self.assertEqual(result.status,403)
 async def test_old_no_query_contract_and_new_cursor_filters_are_preserved(self):
  result=await self.view.get(self.request())
  self.assertEqual(len(result['events']),2);self.assertEqual(result['retention'],'permanent')
  self.assertEqual(result['events'][0]['payload']['password'],'[redacted]')
  self.assertEqual(result['status']['settings']['password'],'[redacted]')
  self.assertEqual(result['diagnostics']['schema_version'],1)
  self.assertIn('stage',result['diagnostics'])
  result=await self.view.get(self.request({'after':'0','limit':'1','sale_id':'a'}))
  self.assertTrue(result['has_more']);self.assertEqual(result['next_cursor'],1)
  self.assertEqual((await self.view.get(self.request({'until_id':'1'})))['events'][0]['id'],1)
 async def test_malformed_or_unknown_query_is_a_bounded_bad_request(self):
  for query in ({'limit':'100000'},{'after':'-1'},{'limit':'1.5'},{'unknown':'field'},{'since':'NaN'}):
   with self.subTest(query=query):self.assertEqual((await self.view.get(self.request(query))).status,400)
 async def test_unreadable_history_returns_explicit_failure_without_deleting_data(self):
  with patch.object(self.journal,'recent',side_effect=OSError('private path details')):
   result=await self.view.get(self.request());self.assertEqual(result.status,503)
   self.assertNotIn('private path',result.text)
  self.assertEqual(len(self.journal.recent()),2)

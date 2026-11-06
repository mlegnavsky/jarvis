import types,unittest
import test_sale_adapter as fixtures
class HistoryPermissionsTests(unittest.IsolatedAsyncioTestCase):
 asyncSetUp=fixtures.AdapterTests.asyncSetUp
 asyncTearDown=fixtures.AdapterTests.asyncTearDown
 setup=fixtures.AdapterTests.setup
 poll=fixtures.AdapterTests.poll
 service=fixtures.AdapterTests.service
 async def test_read_only_endpoints_require_admin_and_paginate_without_writes(self):
  views=[];self.hass.http.register_view=views.append
  data=await self.setup();history=next(v for v in views if v.url.endswith('/history'));diagnostics=next(v for v in views if v.url.endswith('/diagnostics'))
  class Request(dict):query={}
  for view in (history,diagnostics):
   self.assertTrue(view.requires_auth)
   for request in (Request(),Request(hass_user=types.SimpleNamespace(is_admin=False))):self.assertEqual((await view.get(request)).status,403)
  data['journal'].append('sale_start',{'id':'one'},100)
  request=Request(hass_user=types.SimpleNamespace(is_admin=True));request.query={'after':'0','limit':'1','kind':'sale_start'}
  before=list(self.writes);result=await history.get(request)
  self.assertEqual(len(result['events']),1);self.assertEqual(self.writes,before)
  request.query={'limit':'1001'};self.assertEqual((await history.get(request)).status,400)
  request.query={};result=await diagnostics.get(request);self.assertEqual(result['schema_version'],1);self.assertIn('issues',result['health'])
  self.assertEqual(self.writes,before)

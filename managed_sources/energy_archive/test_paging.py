import importlib.util
import pathlib
import unittest

spec=importlib.util.spec_from_file_location('archive_paging',pathlib.Path(__file__).with_name('paging.py'))
try:
 module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
except FileNotFoundError:module=None

class PagingTests(unittest.IsolatedAsyncioTestCase):
 async def test_preserves_late_day_data_after_ten_thousand_events(self):
  self.assertIsNotNone(module,'archive pagination is missing')
  samples=[{'t':100+x,'values':{}} for x in range(10001)]
  async def read(start,end):return {'samples':[s for s in samples if start<=s['t']<end][:10000],'publications':{'spot':{'issued_at':'original'}}}
  data=await module.fetch_day(read,100,20000)
  self.assertEqual(len(data['samples']),10001)
  self.assertEqual(data['samples'][-1]['t'],10100)
  self.assertTrue(data['complete'])
 async def test_nonadvancing_server_fails_instead_of_silent_truncation(self):
  self.assertIsNotNone(module,'archive pagination is missing')
  async def read(start,end):return {'samples':[{'t':100}]*10000}
  with self.assertRaises(ValueError):await module.fetch_day(read,100,20000)

if __name__=='__main__':unittest.main()

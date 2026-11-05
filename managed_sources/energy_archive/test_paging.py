import importlib.util
import pathlib
import unittest

spec=importlib.util.spec_from_file_location('archive_paging',pathlib.Path(__file__).with_name('paging.py'))
try:
 module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
except FileNotFoundError:module=None

class PagingTests(unittest.IsolatedAsyncioTestCase):
 async def test_php_empty_maps_keep_events_and_measurements_readable(self):
  async def read(start,end):return {'samples':[{'t':101,'values':{'grid':{'value':3}}},{'t':102,'values':[],'event':{'kind':'sale_start'}}],'publications':[]}
  data=await module.fetch_day(read,100,200)
  self.assertEqual(data['samples'][1]['values'],{})
  self.assertEqual(data['samples'][1]['event'],{'kind':'sale_start'})
  self.assertEqual(data['publications'],{})
 async def test_nonempty_list_is_rejected_as_corrupt_measurement_map(self):
  async def read(start,end):return {'samples':[{'t':101,'values':[1]}],'publications':{}}
  with self.assertRaises(ValueError):await module.fetch_day(read,100,200)
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

class BoundedWindowTests(unittest.IsolatedAsyncioTestCase):
 async def test_full_day_uses_small_bounded_queries_without_losing_samples(self):
  from paging import fetch_window
  calls=[]
  async def read(start,end):
   self.assertLessEqual(end-start,900);calls.append((start,end))
   return {'samples':[{'t':start+1,'values':{}}],'publications':{'spot':{'issued_at':str(end)}}}
  result=await fetch_window(read,1000,4600)
  self.assertTrue(result['complete']);self.assertEqual(len(result['samples']),4)
  self.assertEqual(calls,[(1000,1900),(1900,2800),(2800,3700),(3700,4600)])
  self.assertEqual(result['publications']['spot']['issued_at'],'4600')

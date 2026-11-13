import importlib.util, pathlib, tempfile, unittest
spec=importlib.util.spec_from_file_location('archive_store',pathlib.Path(__file__).with_name('store.py'))
module=importlib.util.module_from_spec(spec)
class StoreTest(unittest.TestCase):
 def test_durable_ack(self):
  spec.loader.exec_module(module)
  with tempfile.TemporaryDirectory() as root:
   q=module.Outbox(pathlib.Path(root)/'queue.db')
   q.append({'t':1,'values':{'x':None}})
   key,body=q.batch();self.assertEqual(q.batch(),(key,body))
   self.assertRaises(ValueError,q.ack,key,'incorrect')
   self.assertEqual(q.count(),1);q.ack(key,key);self.assertEqual(q.count(),0)
   self.assertEqual(module.Outbox(pathlib.Path(root)/'queue.db').count(),0)
 def test_queue_limit_never_discards_old_records(self):
  spec.loader.exec_module(module)
  with tempfile.TemporaryDirectory() as root:
   q=module.Outbox(pathlib.Path(root)/'queue.db',limit=100)
   q.append({'t':1,'value':'original'})
   self.assertRaises(RuntimeError,q.append,{'t':2,'value':'x'*200})
   self.assertEqual(q.count(),1)
 def test_restart_reuses_inflight_batch_and_excludes_later_rows(self):
  spec.loader.exec_module(module)
  with tempfile.TemporaryDirectory() as root:
   path=pathlib.Path(root)/'queue.db';q=module.Outbox(path)
   q.append({'t':1});key,body=q.batch();q.append({'t':2})
   q=module.Outbox(path);self.assertEqual(q.batch(),(key,body));q.ack(key,key)
   self.assertEqual(q.count(),1)

import unittest
from types import SimpleNamespace as S
from retention import retention_plan
class RetentionTests(unittest.TestCase):
 def b(self,id,date,full=True,failed=False):
  return S(backup_id=id,date=date,agents={'hassio.local':S(size=100)},homeassistant_included=True,database_included=True,addons=['addon'] if full else [],failed_addons=['bad'] if failed else [],failed_folders=[],failed_agent_ids=[])
 def test_keep_last_complete_system_backup(self):
  keep,remove=retention_plan({'a':self.b('a','2026-10-27T01:00:00+00:00'),'b':self.b('b','2026-10-27T02:00:00+00:00'),'c':self.b('c','2026-10-27T03:00:00+00:00',False)})
  self.assertEqual(keep,'b');self.assertEqual(set(remove),{'a'})
 def test_no_complete_backup_means_no_deletion(self):
  self.assertEqual(retention_plan({'bad':self.b('bad','2026-10-27T01:00:00+00:00',failed=True)}),(None,[]))
if __name__=='__main__':unittest.main()

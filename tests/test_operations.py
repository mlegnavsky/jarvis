import asyncio
import unittest
from tests import test_admin as fixtures
from app.policy import APIError

class OperationsTests(unittest.IsolatedAsyncioTestCase):
 asyncSetUp=fixtures.AdminTests.asyncSetUp
 asyncTearDown=fixtures.AdminTests.asyncTearDown
 complete=fixtures.AdminTests.complete
 async def test_backup_delete_is_guarded_and_confirmed(self):
  backups=[{'slug':'old','name':'Jarvis before remote administration','date':'2026-01-01','size':10,'protected':False},{'slug':'new','name':'latest','date':'2026-02-01','size':10,'protected':False}]
  native=self.sup.request
  async def request(method,path,body=None):
   if path=='/backups':return {'backups':backups}
   if path=='/backups/old' and method=='DELETE':backups.pop(0);return {}
   return await native(method,path,body)
  self.sup.request=request
  meta=await self.worker.read('backup','old')
  result=await self.complete('backup_delete',{'backup_slug':'old','expected_revision':meta['revision']},'delete-old')
  self.assertEqual(result['state'],'verified',result)
  latest=await self.worker.read('backup','new')
  result=await self.complete('backup_delete',{'backup_slug':'new','expected_revision':latest['revision']},'delete-new')
  self.assertEqual(result['state'],'failed')
 async def test_backup_preparation_failure_is_not_unknown_restart(self):
  self.sup.backup_fails=True
  job=await self.complete('core_restart',{},'restart-no-space')
  self.assertEqual(job['state'],'failed')
  self.assertFalse(any(path=='/core/restart' for path,_ in self.sup.effects))
 async def test_active_deployment_lease_blocks_other_writer(self):
  lease=await self.complete('deployment_acquire',{'owner':'work-one','ttl_seconds':600,'deployment_token':'1'*32},'lease-one')
  self.assertEqual(lease['state'],'verified',lease)
  job=await self.complete('file_write',{'path':'automations.yaml','content':'[]\n','expected_revision':'missing'},'other-writer')
  self.assertEqual(job['state'],'failed',job)
  token='1'*32
  job=await self.complete('file_write',{'path':'automations.yaml','content':'[]\n','expected_revision':'missing','deployment_token':token},'owner-writer')
  self.assertEqual(job['state'],'verified',job)
 async def test_bundle_preview_apply_and_cas_rollback(self):
  from app.ha import UpstreamError
  native=self.sup.request
  async def request(method,path,body=None):
   if path=='/core/api/config':return {'state':'RUNNING'}
   if path=='/core/api/states/sensor.proof':return {'state':'ready','attributes':{'version':'1.0'}}
   return await native(method,path,body)
  self.sup.request=request
  bundle={'source_commit':'a'*40,'core_version':'2026.6.4','activation':'none','files':[{'path':'automations.yaml','content':'[]\n','expected_revision':'missing'}],'checks':[{'entity_id':'sensor.proof','state':'ready','version':'1.0'}]}
  prepared=await self.complete('deployment_prepare',{'bundle':bundle},'bundle-plan')
  self.assertEqual(prepared['state'],'verified',prepared)
  self.assertFalse((self.ha_root/'automations.yaml').exists())
  await self.complete('deployment_acquire',{'owner':'deploy','ttl_seconds':600,'deployment_token':'1'*32},'bundle-lock')
  token='1'*32
  args={'plan_id':'bundle-plan','expected_revision':prepared['result']['revision'],'deployment_token':token}
  applied=await self.complete('deployment_apply',args,'bundle-apply')
  self.assertEqual(applied['state'],'verified',applied)
  self.assertEqual(applied['result']['phase'],'file_written')
  # No activation cannot claim a running version even if old sensors match.
  plan=await self.worker.read('deployment','bundle-plan')
  self.assertNotEqual(plan['phase'],'active_verified')
  restored=await self.complete('deployment_rollback',args,'bundle-undo')
  self.assertEqual(restored['state'],'verified',restored)
  self.assertFalse((self.ha_root/'automations.yaml').exists())
 async def test_storage_shortfall_blocks_before_backup_or_restart(self):
  native=self.sup.request
  async def request(method,path,body=None):
   if path=='/host/info':return {'disk_free':1.5,'disk_used':30.5,'disk_total':32}
   return await native(method,path,body)
  self.sup.request=request
  job=await self.complete('core_restart',{},'no-space-preflight')
  self.assertEqual(job['state'],'failed',job)
  self.assertEqual(job['result']['error'],'insufficient_backup_space_requested_change_not_started')
  self.assertFalse(self.sup.effects)
 async def test_other_work_cannot_release_deployment_lease(self):
  lease=await self.complete('deployment_acquire',{'owner':'one','ttl_seconds':600,'deployment_token':'1'*32},'guarded-lease')
  blocked=await self.complete('deployment_release',{'deployment_token':'0'*32},'wrong-release')
  self.assertEqual(blocked['state'],'failed')
  self.assertTrue((await self.worker.read('deployment_status'))['locked'])
 async def test_protected_backup_is_never_deleted(self):
  native=self.sup.request
  async def request(method,path,body=None):
   if path=='/backups':return {'backups':[{'slug':'old','date':'2026-01-01','protected':True},{'slug':'new','date':'2026-02-01','protected':False}]}
   return await native(method,path,body)
  self.sup.request=request
  item=await self.worker.read('backup','old')
  job=await self.complete('backup_delete',{'backup_slug':'old','expected_revision':item['revision']},'protected-delete')
  self.assertEqual(job['state'],'failed');self.assertFalse(self.sup.effects)
 async def test_missing_backup_date_fails_closed(self):
  async def request(method,path,body=None):
   if path=='/backups':return {'backups':[{'slug':'old','protected':False},{'slug':'new','date':'2026-02-01','protected':False}]}
   if method=='DELETE':self.fail('Must not delete with incomplete dates')
  self.sup.request=request
  meta=await self.worker.read('backup','old')
  result=await self.complete('backup_delete',{'backup_slug':'old','expected_revision':meta['revision']},'missing-date')
  self.assertEqual(result['state'],'failed',result)
 async def test_runtime_check_must_have_an_expectation(self):
  from app.deployments import validate
  bundle={'source_commit':'a'*40,'core_version':'2026.6.4','activation':'core_restart','files':[{'path':'automations.yaml','content':'[]\n','expected_revision':'missing'}],'checks':[{'entity_id':'sensor.proof','state':None,'version':None}]}
  with self.assertRaises(APIError):validate(self.worker,'deployment_prepare',{'bundle':bundle})
 async def test_manual_backup_uses_space_preflight(self):
  native=self.sup.request
  async def request(method,path,body=None):
   if path=='/host/info':return {'disk_free':1.5,'disk_used':30.5,'disk_total':32}
   return await native(method,path,body)
  self.sup.request=request
  job=await self.complete('backup_create',{},'manual-backup-no-space')
  self.assertEqual(job['state'],'failed',job)
  self.assertFalse(self.sup.effects)

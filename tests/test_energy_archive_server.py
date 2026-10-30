"""Real HTTP regression tests for private immutable telemetry archive."""
import hashlib,json,shutil
from tests import test_backup_dav as fixtures
class EnergyArchiveServerTests(fixtures.BackupDAVTests):
 def setUp(self):
  super().setUp()
  shutil.copytree('testing/energy-archive',self.web/'energy-archive')
 def req(self,method='GET',name='',data=None,auth=True,headers=None):
  import base64,http.client
  h={}
  if auth:h['Authorization']='Basic '+base64.b64encode(('jarvis-backup:'+self.password).encode()).decode()
  h.update(headers or {});c=http.client.HTTPConnection('127.0.0.1',self.port,timeout=5)
  c.request(method,'/energy-archive/index.php'+name,body=data,headers=h);r=c.getresponse();result=r.status,dict(r.getheaders()),r.read();c.close();return result
 def test_forecast_keeps_original_issuance(self):
  import time,datetime
  now=time.time();start=now-3*86400;end=start+86400
  original=datetime.datetime.fromtimestamp(start-3600,datetime.timezone.utc).isoformat()
  revised=datetime.datetime.fromtimestamp(start+7200,datetime.timezone.utc).isoformat()
  raw=json.dumps([{'kind':'weather','t':now,'issued_at':original,'attributes':{'rows':[{'cloud_cover':20}]}},{'kind':'weather','t':now,'issued_at':revised,'attributes':{'rows':[{'cloud_cover':90}]}}]).encode()
  status,_,body=self.req('POST',data=raw,headers={'X-Batch-SHA256':hashlib.sha256(raw).hexdigest()});self.assertEqual(status,200,body)
  status,_,body=self.req(name='?op=day&start='+str(start)+'&end='+str(end));self.assertEqual(status,200,body);self.assertEqual(json.loads(body)['publications']['weather']['issued_at'],original)
 # Parent WebDAV tests are inapplicable to this separate API.
 def test_batch_retry_and_day(self):
  import time
  raw=json.dumps([{'kind':'sample','t':time.time(),'values':{'sensor.inverter_battery':{'value':None,'source_updated':None}}}]).encode();key=hashlib.sha256(raw).hexdigest()
  for _ in range(2):
   status,_,body=self.req('POST',data=raw,headers={'X-Batch-SHA256':key});self.assertEqual(status,200,body);self.assertEqual(json.loads(body)['ack'],key)
  status,_,body=self.req();self.assertEqual(status,200,body);self.assertEqual(json.loads(body)['samples'],1)
  status,_,body=self.req(name='?op=day&start='+str(time.time()-60)+'&end='+str(time.time()+60));self.assertEqual(status,200,body);self.assertEqual(len(json.loads(body)['samples']),1)
  self.assertEqual(self.req('POST',data=raw,headers={'X-Batch-SHA256':'0'*64})[0],400)
  self.assertEqual(self.req(auth=False)[0],401);self.assertEqual(self.req('DELETE')[0],405)
# Avoid inheriting WebDAV-method assertions; retain fixture and our targeted test.
for name in list(vars(fixtures.BackupDAVTests)):
 if name.startswith('test_'):setattr(EnergyArchiveServerTests,name,None)

"""Real HTTP regression tests for private immutable telemetry archive."""
import hashlib,json,shutil
from tests import test_backup_dav as fixtures
class EnergyArchiveServerTests(fixtures.BackupDAVTests):
 def test_samples_without_export_measurements_do_not_imply_zero_revenue(self):
  import subprocess
  code="require 'testing/energy-archive/finance.php'; [$s,$e]=cash_day('2026-11-14'); echo json_encode(cash_calculate([['t'=>$s+36000,'values'=>[]]],[],'2026-11-14'));"
  r=json.loads(subprocess.check_output(['php','-r',code]));self.assertIsNone(r['known_sale_czk']);self.assertIsNone(r['export_kwh'])
 def test_receipt_delay_does_not_move_export_to_another_price_quarter(self):
  import subprocess
  code="require 'testing/energy-archive/finance.php'; [$s,$e]=cash_day('2026-11-14'); $q=$s+36000; $rows=[]; foreach([[880,880,0],[910,890,1]] as [$receipt,$stamp,$v]){$rows[]=['t'=>$q+$receipt,'values'=>['sensor.inverter_today_energy_export'=>['value'=>$v,'source_updated'=>gmdate('c',(int)($q+$stamp)),'source_changed'=>gmdate('c',(int)($q+$stamp))]]];} echo json_encode(cash_calculate($rows,[(int)$q=>1.0,(int)$q+900=>10.0],'2026-11-14'));"
  r=json.loads(subprocess.check_output(['php','-r',code]));self.assertAlmostEqual(r['known_sale_czk'],.7);self.assertEqual(r['quarters'][0]['start'],1794646800)
 def test_import_counter_reset_keeps_purchase_incomplete(self):
  import subprocess
  code="require 'testing/energy-archive/finance.php'; [$s,$e]=cash_day('2026-11-14'); $rows=[]; foreach([[$s+36000,2.0],[$e-30,.2]] as [$t,$v]){$rows[]=['t'=>$t,'values'=>['sensor.inverter_today_energy_import'=>['value'=>$v,'source_updated'=>gmdate('c',(int)$t),'source_changed'=>gmdate('c',(int)$t)]]];} echo json_encode(cash_calculate($rows,[],'2026-11-14'));"
  r=json.loads(subprocess.check_output(['php','-r',code]));self.assertTrue(r['counter_reset']);self.assertIsNone(r['purchase_czk'])
 def test_midday_archive_is_not_a_complete_day(self):
  import subprocess
  code="require 'testing/energy-archive/finance.php'; [$s,$e]=cash_day('2026-11-14'); $rows=[]; foreach([[36000,0],[36010,6.2]] as [$dt,$v]){$t=$s+$dt; $rows[]=['t'=>$t,'values'=>['sensor.inverter_today_energy_export'=>['value'=>$v,'source_updated'=>gmdate('c',(int)$t),'source_changed'=>gmdate('c',(int)$t)]]];} $r=cash_calculate($rows,[(int)floor(($s+36000)/900)*900=>4.0],'2026-11-14'); echo json_encode($r);"
  r=json.loads(subprocess.check_output(['php','-r',code]));self.assertIsNone(r['sale_czk'],'A day ending at noon is not final revenue');self.assertEqual(r['quality'],'partial')
 def test_closed_day_finance_is_materialized_from_meter_increments(self):
  import datetime as dt
  from zoneinfo import ZoneInfo
  day=dt.datetime.now(ZoneInfo('Europe/Prague')).date()-dt.timedelta(days=1)
  start=dt.datetime.combine(day,dt.time(),ZoneInfo('Europe/Prague')).timestamp()
  stamp=lambda t:dt.datetime.fromtimestamp(t,dt.timezone.utc).isoformat()
  prices=[{'time':stamp(start+i*900),'eur_mwh':152 if i<49 else 192} for i in range(96)]
  records=[{'kind':'spot','t':start,'issued_at':stamp(start),'attributes':{'rate':25,'rows':prices}}]
  for t,energy in [(start+12*3600,0),(start+12*3600+10,2.4),(start+12*3600+901,2.4),(start+12*3600+911,6.2),(start+86400-30,6.2)]:
   values={}
   for kind,value in [('export',energy),('import',.23)]:
    values['sensor.inverter_today_energy_'+kind]={'value':str(value),'source_updated':stamp(t),'source_changed':stamp(t)}
   records.append({'kind':'sample','t':t,'values':values})
  raw=json.dumps(records).encode();status,_,body=self.req('POST',data=raw,headers={'X-Batch-SHA256':hashlib.sha256(raw).hexdigest()});self.assertEqual(status,200,body)
  status,_,body=self.req();self.assertEqual(status,200,body);report=json.loads(body)['finance'];self.assertEqual(report['schema'],2)
  row=next(d for d in report['days'] if d['date']==day.isoformat());self.assertAlmostEqual(row['export_kwh'],6.2);self.assertAlmostEqual(row['sale_czk'],25.5);self.assertEqual(row['quality'],'estimate')
  status,_,body=self.req();self.assertEqual(json.loads(body)['finance']['built_days'],0,'Unchanged days reuse durable materialized results')
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
  status,_,body=self.req();self.assertEqual(status,200,body);self.assertEqual(json.loads(body)['samples'],1);self.assertGreater(json.loads(body)['compressed_bytes'],30)
  status,_,body=self.req(name='?op=day&start='+str(time.time()-60)+'&end='+str(time.time()+60));self.assertEqual(status,200,body);self.assertEqual(len(json.loads(body)['samples']),1)
  self.assertEqual(self.req('POST',data=raw,headers={'X-Batch-SHA256':'0'*64})[0],400)
  self.assertEqual(self.req(auth=False)[0],401);self.assertEqual(self.req('DELETE')[0],405)
# Avoid inheriting WebDAV-method assertions; retain fixture and our targeted test.
for name in list(vars(fixtures.BackupDAVTests)):
 if name.startswith('test_'):setattr(EnergyArchiveServerTests,name,None)

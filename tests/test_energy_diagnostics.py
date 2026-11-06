import copy
import sqlite3
import tempfile
import unittest
from pathlib import Path
from journal import Journal
from diagnostics import diagnostic_snapshot, redact


class JournalQueryTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
  self.path=Path(self.temp.name)/'existing.sqlite'
  # Actual old schema and IDs: opening the refactor must not rewrite history.
  with sqlite3.connect(self.path) as db:
   db.execute('CREATE TABLE events(id INTEGER PRIMARY KEY,t REAL NOT NULL,kind TEXT NOT NULL,payload TEXT NOT NULL)')
   db.execute('INSERT INTO events VALUES(41,100,"sale_start",\'{"id":"a","unknown_old_field":7}\')')
   db.execute('CREATE TABLE commands(id TEXT PRIMARY KEY,body TEXT NOT NULL)')
   db.execute('INSERT INTO commands VALUES("old",\'{"id":"old"}\')')
  self.q=Journal(self.path)
  self.q.append('write_failed',{'sale_id':'a','expected':500,'actual':None},t=110)
  self.q.append('sale_stop',{'id':'b'},t=120)
 def test_cursor_paging_reopens_legacy_history_without_loss_or_repeated_ids(self):
  first=self.q.page(after=0,limit=2)
  self.assertEqual([r['id'] for r in first['events']],[41,42]);self.assertTrue(first['has_more'])
  second=Journal(self.path).page(after=first['next_cursor'],limit=2)
  self.assertEqual([r['id'] for r in second['events']],[43]);self.assertFalse(second['has_more'])
  self.assertEqual(first['events'][0]['payload']['unknown_old_field'],7)
  self.assertFalse(self.q.claim_command({'id':'old'}))
 def test_filters_time_kind_and_correlation_match_both_event_id_conventions(self):
  rows=self.q.page(after=0,limit=10,sale_id='a')['events']
  self.assertEqual([r['id'] for r in rows],[41,42])
  rows=self.q.page(after=0,limit=10,since=105,until=115,kind='write_failed')['events']
  self.assertEqual([r['id'] for r in rows],[42])
 def test_bad_limits_and_filter_injection_are_rejected_or_treated_as_literals(self):
  for kwargs in ({'limit':1001},{'limit':True},{'after':-1},{'since':float('nan')},{'since':10,'until':1}):
   with self.subTest(kwargs=kwargs),self.assertRaises(ValueError):self.q.page(**kwargs)
  self.assertEqual(self.q.page(kind="x' OR1=1 --")['events'],[])
  self.assertEqual(len(self.q.recent()),3)


class DiagnosticTests(unittest.TestCase):
 def body(self):
  return {'version':'0.10.0','ready':True,'active':True,'observed':True,'phase':'measuring',
          'healthy':True,'settings':{'requested_automatic':True},'mode':'battery',
          'telemetry':{'sensor.inverter_battery':{'state':'78','source_reported':'2026-11-06T17:00:00+00:00'}},
          'health':{'healthy':True,'issues':[]},'diagnostic_stop':{'id':'x','failure_context':{'health':{'issues':[{'code':'stale','entity_id':'sensor.inverter_battery','age_seconds':31}]}}}}
 def test_snapshot_explains_stage_and_retains_exact_last_failure_without_mutating_input(self):
  body=self.body();original=copy.deepcopy(body)
  result=diagnostic_snapshot(body,1793984405)
  self.assertEqual(result['stage'],'export_confirmed')
  self.assertEqual(result['measurements']['sensor.inverter_battery']['age_seconds'],5)
  self.assertEqual(result['last_stop']['failure_context']['health']['issues'][0]['age_seconds'],31)
  self.assertEqual(body,original)
 def test_stale_health_configuration_and_stopping_are_distinct_stages(self):
  body=self.body();body.update(active=False,observed=False,healthy=False,health={'healthy':False,'transient_only':True,'issues':[{'code':'stale'}]})
  self.assertEqual(diagnostic_snapshot(body,1)['stage'],'measurement_unavailable')
  body.update(healthy=True,health={'healthy':True,'issues':[]},profile_issues=[{'expected':30,'actual':100}])
  self.assertEqual(diagnostic_snapshot(body,1)['stage'],'configuration_mismatch')
  body.update(active=True,phase='stopping')
  self.assertEqual(diagnostic_snapshot(body,1)['stage'],'stopping')
 def test_redaction_is_recursive_and_preserves_diagnostic_fields(self):
  raw={'expected':30,'actual':60,'nested':[{'password':'dont-export','api_key':'private','token':'secret','authorization':'Bearer secret'}]}
  result=redact(raw)
  self.assertEqual(result['actual'],60)
  self.assertEqual(set(result['nested'][0].values()),{'[redacted]'})
  self.assertEqual(raw['nested'][0]['password'],'dont-export')

 def test_previous_day_completion_does_not_describe_today_as_finished(self):
  body=self.body();body.update(active=False,completed_battery_plan={'day':'2026-11-05'})
  self.assertEqual(diagnostic_snapshot(body,1793984405)['stage'],'waiting')
  body['completed_battery_plan']['day']='2026-11-06'
  self.assertEqual(diagnostic_snapshot(body,1793984405)['stage'],'plan_complete')

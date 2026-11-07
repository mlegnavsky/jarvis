import unittest
from supervision import Monitor

class MonitorTests(unittest.TestCase):
 def body(self,now=1000,**kw):
  values={'sensor.inverter_grid_power':-12,'sensor.inverter_battery_power':160,
          'sensor.inverter_pv_power':0,'sensor.inverter_battery':53,
          'sensor.inverter_battery_temperature':13.5}
  return dict(ready=True,healthy=True,active=True,mode='bias',phase='running',power_w=20,
              deadline=5000,reason='Malý přetok',charging_active=False,
              telemetry={k:{'state':str(v),'source_reported':now} for k,v in values.items()},**kw)
 def test_stable_zero_is_fresh_from_report_timestamp_and_bias_is_distinct(self):
  r=Monitor().update(self.body(),1000)
  self.assertEqual(r['operation']['mode'],'bias')
  self.assertEqual(r['measurements']['sensor.inverter_pv_power']['status'],'fresh')
  self.assertEqual(r['operation']['result'],'measured_export')
  self.assertIn('měnič',r['operation']['evidence_notice'])
 def test_missing_export_requires_continuous_90_seconds_and_resets_on_flow(self):
  m=Monitor();b=self.body();b['telemetry']['sensor.inverter_grid_power']['state']='300'
  self.assertEqual(m.update(b,1000)['alerts'],[])
  for t in range(1005,1091,5):
   for v in b['telemetry'].values():v['source_reported']=t
   r=m.update(b,t)
  self.assertIn('flow_mismatch',{a['code'] for a in r['alerts']})
  b['telemetry']['sensor.inverter_grid_power']['state']='-10'
  self.assertEqual(m.update(b,1090)['alerts'],[])
  b['telemetry']['sensor.inverter_grid_power']['state']='300'
  self.assertEqual(m.update(b,1090)['alerts'],[])
 def test_stale_future_and_nonfinite_values_never_confirm_export(self):
  for stamp,value in ((900,'-20'),(1005,'-20'),(1000,'nan')):
   b=self.body();b['telemetry']['sensor.inverter_grid_power']={'state':value,'source_reported':stamp}
   r=Monitor().update(b,1000)
   self.assertEqual(r['operation']['result'],'unknown')
   self.assertNotEqual(r['measurements']['sensor.inverter_grid_power']['status'],'fresh')
 def test_charging_is_checked_and_missing_flow_warns_after_90_seconds(self):
  m=Monitor();b=self.body();b.update(charging_active=True,active=False,healthy=False)
  m.update(b,1000)
  for t in range(1005,1091,5):
   for v in b['telemetry'].values():v['source_reported']=t
   r=m.update(b,t)
  self.assertEqual(r['operation']['mode'],'charging')
  self.assertIn('charge_mismatch',{a['code'] for a in r['alerts']})
  b['telemetry']['sensor.inverter_battery_power']['state']='-4000'
  r=m.update(b,1090)
  self.assertEqual(r['operation']['result'],'measured_charging')
  self.assertEqual(r['alerts'],[])
 def test_owner_off_and_stopping_are_not_failed_exports(self):
  for phase,active in (('idle',False),('stopping',True)):
   b=self.body();b.update(phase=phase,active=active)
   m=Monitor();m.update(b,1000)
   for v in b['telemetry'].values():v['source_reported']=1200
   self.assertEqual(m.update(b,1200)['alerts'],[])
 def test_stale_telemetry_has_precise_alert_even_while_charging(self):
  b=self.body();b.update(charging_active=True,healthy=False)
  r=Monitor().update(b,1100)
  self.assertIn('monitor_measurements',{a['code'] for a in r['alerts']})
 def test_startup_grace_does_not_confirm_stale_measurements(self):
  r=Monitor(started_at=1000).update(self.body(now=900),1001)
  self.assertEqual(r['alerts'],[])
  self.assertEqual(r['operation']['result'],'unknown')
 def test_gap_in_monitoring_does_not_count_as_continuous_failure(self):
  m=Monitor();b=self.body();b['telemetry']['sensor.inverter_grid_power']['state']='200'
  m.update(b,1000)
  for v in b['telemetry'].values():v['source_reported']=1200
  self.assertEqual(m.update(b,1200)['alerts'],[])

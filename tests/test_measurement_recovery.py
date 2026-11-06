import unittest
from sales import after_stop

class MeasurementRecoveryTests(unittest.TestCase):
 def test_ambiguous_legacy_health_reason_cannot_queue_recovery(self):
  proof=self.proof();proof['context'].pop('health')
  r=after_stop({'requested_automatic':True},proof)
  self.assertFalse((r.get('measurement_recovery') or {}).get('pending',False))
 def test_documented_pv_data_loss_queues_thirty_second_recovery(self):
  proof=self.proof();proof['context']['health']={'healthy':False,'transient_only':True,'issues':[{'code':'stale','entity_id':'sensor.inverter_battery','age_seconds':31}]}
  r=after_stop({'requested_automatic':True},proof)
  self.assertEqual(r['measurement_recovery']['source'],'pv')
  self.assertEqual(r['measurement_recovery']['stable_seconds'],30)
 def test_temperature_or_fault_mixed_with_data_loss_is_not_transient(self):
  proof=self.proof();proof['context']['health']={'healthy':False,'transient_only':False,'issues':[{'code':'stale'},{'code':'temperature'}]}
  self.assertFalse((after_stop({'requested_automatic':True},proof).get('measurement_recovery') or {}).get('pending',False))
 def proof(self):
  return {'id':'lost-data','mode':'bias','purpose':'automatic','reason':'guard','stop_verified':True,'conflicts':{},'failures':[],'context':{'triggers':['measurement_or_health'],'health':{'healthy':False,'transient_only':True,'issues':[{'code':'stale','entity_id':'sensor.inverter_battery','age_seconds':31}]}}}
 def test_only_confirmed_measurement_guard_queues_recovery_without_revoking_prior_bias_proof(self):
  r=after_stop({'requested_automatic':True,'automatic':True,'bias_verified':True},self.proof())
  self.assertTrue(r['measurement_recovery']['pending']);self.assertTrue(r['bias_verified'])
  self.assertFalse(r['automatic']);self.assertTrue(r['inhibited'])
 def test_owner_off_conflict_failed_stop_and_other_guards_cannot_queue_recovery(self):
  for change in ({'stop_verified':False},{'conflicts':{'cap':{}}},{'failures':['bad']},{'context':{'triggers':['export_limit']}},{'purpose':'bias_probe'}):
   r=after_stop({'requested_automatic':True,'automatic':True,'bias_verified':True},{**self.proof(),**change})
   self.assertFalse((r.get('measurement_recovery') or {}).get('pending',False))
  r=after_stop({'requested_automatic':False},self.proof());self.assertFalse((r.get('measurement_recovery') or {}).get('pending',False))

 def test_confirmed_production_stop_retry_recovers_but_unfinished_retry_does_not(self):
  proof={**self.proof(),'purpose':'manual','reason':'stop_recovery','failures':['number.inverter_export_surplus_power: ']}
  r=after_stop({'requested_automatic':True},proof);self.assertTrue(r['measurement_recovery']['pending'])
  r=after_stop({'requested_automatic':True},{**proof,'stop_verified':False});self.assertFalse((r.get('measurement_recovery') or {}).get('pending',False))

 def test_fully_restored_pv_restart_does_not_latch_automatic_off(self):
  proof={'id':'retry','mode':'pv','purpose':'automatic','reason':'stop_recovery','original_reason':'recovery','stop_verified':True,'conflicts':{},'failures':['number.inverter_export_surplus_power: timeout']}
  self.assertTrue(after_stop({'automatic':True,'requested_automatic':True},proof)['automatic'])
  for change in ({'stop_verified':False},{'conflicts':{'cap':{}}},{'original_reason':'guard'}):
   self.assertFalse(after_stop({'automatic':True,'requested_automatic':True},{**proof,**change})['automatic'])

 def test_confirmed_measurement_stop_with_prior_native_ack_timeout_still_recovers(self):
  proof={**self.proof(),'reason':'stop_recovery','failures':['number.inverter_export_surplus_power: Měnič nepotvrdil number.inverter_export_surplus_power']}
  self.assertTrue(after_stop({'requested_automatic':True},proof).get('measurement_recovery',{}).get('pending',False))

 def test_native_transport_failure_preserves_real_faults_and_never_labels_them_transient(self):
  from telemetry_health import control_transport_failure
  original={'healthy':False,'transient_only':False,'issues':[{'code':'device_fault','entity_id':'sensor.inverter_device_fault','value':'Alarm'}]}
  report=control_transport_failure(original,100,TimeoutError('native read'))
  self.assertFalse(report['transient_only']);self.assertEqual(report['issues'][0]['code'],'device_fault')
  self.assertEqual(len(original['issues']),1)

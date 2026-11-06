import unittest
from sales import after_stop

class MeasurementRecoveryTests(unittest.TestCase):
 def proof(self):
  return {'id':'lost-data','mode':'bias','purpose':'automatic','reason':'guard','stop_verified':True,'conflicts':{},'failures':[],'context':{'triggers':['measurement_or_health']}}
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

import copy
import unittest

from telemetry_health import evaluate_health, recoverable_battery_stop


class HealthTests(unittest.TestCase):
    def setUp(self):
        self.now = 1000
        values = {'sensor.inverter_battery':78, 'sensor.inverter_pv_power':0,
                  'sensor.inverter_battery_power':9000, 'sensor.inverter_grid_power':-8500,
                  'sensor.inverter_battery_temperature':19,
                  'sensor.inverter_device_state':'Normal','sensor.inverter_device_alarm':'OK',
                  'sensor.inverter_device_fault':'OK','binary_sensor.inverter_battery_alarm':'off',
                  'binary_sensor.inverter_battery_fault':'off'}
        self.states = {k:{'state':v,'reported_at':self.now} for k,v in values.items()}

    def test_zero_pv_is_valid_and_no_failure_is_invented(self):
        self.assertEqual(evaluate_health(self.states,self.now)['issues'],[])
        self.assertTrue(evaluate_health(self.states,self.now)['healthy'])

    def test_stale_measurement_identifies_entity_value_and_age(self):
        self.states['sensor.inverter_battery']['reported_at']=self.now-31
        r=evaluate_health(self.states,self.now)
        self.assertFalse(r['healthy']);self.assertTrue(r['transient_only'])
        issue=r['issues'][0]
        self.assertEqual(issue['entity_id'],'sensor.inverter_battery')
        self.assertEqual(issue['code'],'stale');self.assertEqual(issue['age_seconds'],31)

    def test_unavailable_temperature_is_measurement_loss_but_hot_temperature_is_not(self):
        self.states['sensor.inverter_battery_temperature']['state']='unavailable'
        self.assertTrue(evaluate_health(self.states,self.now)['transient_only'])
        self.states['sensor.inverter_battery_temperature']['state']=46
        r=evaluate_health(self.states,self.now)
        self.assertFalse(r['transient_only']);self.assertIn('temperature',[i['code'] for i in r['issues']])

    def test_fault_and_stale_together_never_allow_automatic_recovery(self):
        self.states['sensor.inverter_device_fault']['state']='Fault'
        self.states['sensor.inverter_battery']['reported_at']=0
        self.assertFalse(evaluate_health(self.states,self.now)['transient_only'])

    def test_missing_alarm_and_future_timestamp_are_explicit(self):
        del self.states['binary_sensor.inverter_battery_alarm']
        self.states['sensor.inverter_grid_power']['reported_at']=1002
        codes={i['code'] for i in evaluate_health(self.states,self.now)['issues']}
        self.assertIn('missing',codes);self.assertIn('timestamp',codes)

    def test_charging_blocks_export_without_being_a_communication_failure(self):
        r=evaluate_health(self.states,self.now,charging=True)
        self.assertFalse(r['healthy']);self.assertFalse(r['transient_only'])

    def test_only_documented_measurement_stop_with_confirmed_cleanup_can_recover(self):
        self.states['sensor.inverter_battery']['reported_at']=0
        proof={'id':'x','purpose':'automatic','reason':'health','stop_verified':True,
               'conflicts':{},'failure_context':{'health':evaluate_health(self.states,self.now)}}
        self.assertTrue(recoverable_battery_stop(proof))
        for change in ({'stop_verified':False},{'conflicts':{'143':{}}},
                       {'purpose':'manual'},{'reason':'voltage'},{'failure_context':{}},
                       {'failure_context':{'health':{'healthy':False,'transient_only':True,'issues':[]}}}):
            with self.subTest(change=change):
                self.assertFalse(recoverable_battery_stop({**copy.deepcopy(proof),**change}))

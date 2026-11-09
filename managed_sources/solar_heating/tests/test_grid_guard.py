import unittest
from types import SimpleNamespace as NS
from datetime import datetime,timezone
from grid_guard import check,ENTITIES

class GridGuardTests(unittest.TestCase):
 def states(self):
  v={'binary_sensor.inverter_grid':'on','select.inverter_work_mode':'Zero Export To CT','select.inverter_time_of_use':'Week','switch.inverter_export_surplus':'off','sensor.inverter_battery':'30','sensor.inverter_battery_power':'-40','sensor.inverter_grid_power':'340','binary_sensor.inverter_battery_alarm':'off','binary_sensor.inverter_battery_fault':'off'}
  v.update({f'number.inverter_program_{i}_soc':'30' for i in range(1,7)})
  return {e:NS(state=v[e],last_updated=datetime.fromtimestamp(1000,timezone.utc),last_reported=datetime.fromtimestamp(1000,timezone.utc)) for e in ENTITIES}
 def test_30percent_at_native_reserve_admitted_without_writes(self):
  self.assertTrue(check(self.states().get,1001)[0])
 def test_fail_closed_for_unprotected_discharge_and_missing_or_stale(self):
  for e,value in [('binary_sensor.inverter_grid','off'),('sensor.inverter_battery','31'),('sensor.inverter_battery_power','101'),('number.inverter_program_6_soc','29'),('select.inverter_work_mode','Selling First'),('switch.inverter_export_surplus','on'),('select.inverter_time_of_use','Disabled'),('binary_sensor.inverter_battery_fault','on')]:
   s=self.states();s[e].state=value;self.assertFalse(check(s.get,1001)[0],(e,value))
  self.assertFalse(check(self.states().get,1061)[0])
  s=self.states();del s['sensor.inverter_battery'];self.assertFalse(check(s.get,1001)[0])
 def test_unknown_soc_and_future_report_are_rejected(self):
  s=self.states();s['sensor.inverter_battery'].state='unavailable';self.assertFalse(check(s.get,1001)[0])
  self.assertFalse(check(self.states().get,990)[0])

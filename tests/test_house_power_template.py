"""A zero grid target must never masquerade as zero appliance consumption."""
from datetime import datetime, timezone, timedelta
from pathlib import Path
import math
import unittest
import yaml
from jinja2 import Environment

class State:
 def __init__(self,state,when):
  self.state=str(state);self.last_reported=self.last_updated=when
class States:
 def __init__(self,data):self.data=data
 def __call__(self,key):return self.data.get(key,State('unknown',NOW)).state
 def __getitem__(self,key):return self.data.get(key,State('unknown',NOW))
NOW=datetime(2026,11,5,20,10,tzinfo=timezone.utc)
class HousePowerTests(unittest.TestCase):
 def setUp(self):
  self.assertTrue(Path('managed_sources/energy_weather/house-power.yaml').exists(),'corrected house measurement is missing')
  self.sensor=yaml.safe_load(Path('managed_sources/energy_weather/house-power.yaml').read_text())['sensor'][0]
  self.data={k:State(v,NOW) for k,v in {'select.inverter_work_mode':'Export First','sensor.inverter_load_power':0,'sensor.inverter_power':8349,'sensor.inverter_external_power':-8261,'number.inverter_zero_export_power':0,'sensor.inverter_battery_power':9042}.items()}
 def render(self,key):
  env=Environment();states=States(self.data)
  def numeric(value):
   try:return math.isfinite(float(value)) and str(value) not in ('True','False')
   except (ValueError,TypeError):return False
  env.globals.update(states=states,is_state=lambda k,v:states(k)==v,is_number=numeric,now=lambda:NOW,as_timestamp=lambda v,default=0:v.timestamp() if isinstance(v,datetime) else default)
  return env.from_string(self.sensor[key]).render().strip()
 def available(self):return self.render('availability')=='True'
 def test_selling_preserves_appliance_load_separate_from_zero_grid_target(self):
  self.assertTrue(self.available());self.assertEqual(float(self.render('state')),88)
  self.data['number.inverter_zero_export_power']=State(20,NOW)
  self.assertEqual(float(self.render('state')),88)
 def test_battery_dc_losses_are_not_called_appliance_consumption(self):
  self.data['sensor.inverter_battery_power']=State(10000,NOW)
  self.assertTrue(self.available());self.assertEqual(float(self.render('state')),88)
 def test_normal_mode_uses_native_house_measurement(self):
  self.data['select.inverter_work_mode']=State('Zero Export To CT',NOW)
  self.data['sensor.inverter_load_power']=State(347,NOW)
  self.data['sensor.inverter_external_power']=State('unavailable',NOW)
  self.assertTrue(self.available());self.assertEqual(float(self.render('state')),347)
 def test_missing_stale_incoherent_and_negative_balance_are_not_fake_zero(self):
  for key,value,stamp in [('sensor.inverter_external_power','unavailable',NOW),('sensor.inverter_power',8349,NOW-timedelta(seconds=31)),('sensor.inverter_power',8349,NOW-timedelta(seconds=15)),('sensor.inverter_external_power',-8500,NOW),('select.inverter_work_mode','unknown',NOW)]:
   old=self.data[key];self.data[key]=State(value,stamp)
   self.assertFalse(self.available(),(key,value,stamp));self.data[key]=old
 def test_real_balanced_zero_is_still_a_valid_measurement(self):
  self.data['sensor.inverter_external_power']=State(-8349,NOW)
  self.assertTrue(self.available());self.assertEqual(float(self.render('state')),0)

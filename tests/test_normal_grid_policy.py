"""The normal grid policy applies the owner's5W bias only after verified idle control."""
from pathlib import Path
import unittest
import yaml
from jinja2 import Environment

class NormalGridPolicyTests(unittest.TestCase):
 def setUp(self):
  self.policy=yaml.safe_load(Path('managed_sources/spot_control/normal_grid_bias.yaml').read_text())
  self.states={'sensor.jarvis_energy_sales':'idle','select.inverter_work_mode':'Zero Export To CT','switch.inverter_export_surplus':'off','number.inverter_zero_export_power':'20'}
  self.attrs={'sensor.jarvis_energy_sales':{'ready':True,'healthy':True,'active':False},'sensor.jarvis_spot_control':{'active':False}}
 def guard(self):
  env=Environment();env.globals.update(states=lambda key:self.states.get(key,'unknown'),is_state=lambda key,value:self.states.get(key)==value,state_attr=lambda key,name:self.attrs.get(key,{}).get(name))
  return env.from_string(self.policy['triggers'][1]['value_template']).render().strip()=='True'
 def test_healthy_idle_house_allows_five_watts_only_and_preserves_enabled_state(self):
  self.assertTrue(self.guard());self.assertNotIn('initial_state',self.policy)
  actions=[a for a in self.policy['actions'] if 'action' in a]
  self.assertEqual(actions,[{'action':'solarman.write_multiple_registers','data':{'device':"{{ device_id('number.inverter_zero_export_power') }}",'address':104,'values':[5]}}])
 def test_running_sale_charge_fault_unknown_mode_and_preparation_all_block(self):
  for field in ('active','ready','healthy'):
   saved=self.attrs['sensor.jarvis_energy_sales'][field]
   self.attrs['sensor.jarvis_energy_sales'][field]=not saved
   self.assertFalse(self.guard());self.attrs['sensor.jarvis_energy_sales'][field]=saved
  self.attrs['sensor.jarvis_spot_control']['active']=True;self.assertFalse(self.guard());self.attrs['sensor.jarvis_spot_control']['active']=False
  for key,value in [('sensor.jarvis_energy_sales','preparing'),('select.inverter_work_mode','Export First'),('switch.inverter_export_surplus','on'),('number.inverter_zero_export_power','unavailable')]:
   old=self.states[key];self.states[key]=value;self.assertFalse(self.guard());self.states[key]=old
 def test_guard_is_rechecked_after_settling_and_never_polls_bias_on_timer(self):
  self.assertEqual(self.policy['actions'][2]['value_template'],self.policy['triggers'][1]['value_template'])
  self.assertEqual(self.policy['actions'][1]['delay'],'00:00:15')
  self.assertNotIn('time_pattern',[t['trigger'] for t in self.policy['triggers']])
  self.assertEqual(len([a for a in self.policy['actions'] if 'condition' in a]),1)
  self.states['number.inverter_zero_export_power']='0';self.assertTrue(self.guard())

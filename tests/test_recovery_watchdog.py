import copy,unittest
from datetime import datetime,timezone,timedelta
from types import SimpleNamespace
from jinja2 import Environment
from recovery_watchdog import TEMPLATE,automation

class RecoveryTests(unittest.TestCase):
 def setUp(self):
  self.now=datetime.now(timezone.utc);self.a={'settings':{'requested_automatic':True,'automatic':False,'inhibited':True,'handled_stop_id':'done'},'last_stop':{'id':'done','mode':'pv','purpose':'automatic','reason':'stop_recovery','original_reason':'error','stop_verified':True,'conflicts':{}},'native_program':{'captured_at':self.now.isoformat(),'registers_146_177':[255,1]+[100,500,900,1300,1700,2100]+[12000]*6+[4900]*6+[30]*6+[0]*6},'ready':True,'active':False,'healthy':True}
  self.phase='idle';self.grid=10;self.updated=self.now
 def valid(self):
  class States:
   sensor=SimpleNamespace(jarvis_energy_sales=SimpleNamespace(last_updated=self.updated))
   def __call__(_,key):return self.phase if key=='sensor.jarvis_energy_sales' else str(self.grid)
  def ts(v,default=0):
   try:return v.timestamp() if isinstance(v,datetime) else datetime.fromisoformat(v).timestamp()
   except (TypeError,ValueError):return default
  result=Environment().from_string(TEMPLATE).render(state_attr=lambda key,attr:self.a.get(attr),states=States(),now=lambda:self.now,as_timestamp=ts)
  return result.strip()=='True'
 def test_only_confirmed_idle_owner_requested_transport_stop_can_resume(self):self.assertTrue(self.valid())
 def test_owner_off_stopping_bad_health_unverified_conflict_and_stale_data_are_refused(self):
  for section,key,value in [('settings','requested_automatic',False),('settings','automatic',True),('settings','handled_stop_id','old'),('last_stop','stop_verified',False),('last_stop','conflicts',{'cap':{}}),('last_stop','purpose','commission'),('last_stop','original_reason','export_limit')]:
   saved=copy.deepcopy(self.a);self.a[section][key]=value;self.assertFalse(self.valid(),str((section,key,value)));self.a=saved
  for key,value in [('active',True),('healthy',False),('ready',False)]:
   self.a[key]=value;self.assertFalse(self.valid());self.a[key]=not value
  self.phase='stopping';self.assertFalse(self.valid());self.phase='idle'
  self.grid=-200;self.assertFalse(self.valid());self.grid=10
  self.updated=self.now-timedelta(seconds=21);self.assertFalse(self.valid())
 def test_wrong_native_reserve_charging_and_real_guards_are_not_overridden(self):
  self.a['native_program']['registers_146_177'][23]=60;self.assertFalse(self.valid())
  self.a['native_program']['registers_146_177'][23]=30;self.a['native_program']['registers_146_177'][27]=1;self.assertFalse(self.valid())
  self.a['native_program']['registers_146_177'][27]=0;self.a['last_stop'].update(original_reason='guard',context={'triggers':['export_limit']});self.assertFalse(self.valid())
  self.a['last_stop']['context']['triggers']=['measurement_or_health'];self.assertTrue(self.valid())
 def test_action_rechecks_after_delay_and_only_calls_existing_serialized_controller(self):
  a=automation();self.assertEqual(a['actions'][1]['value_template'],TEMPLATE);self.assertEqual(a['actions'][2]['action'],'jarvis_spot_control.resume_confirmed_sale');self.assertEqual(a['mode'],'single')

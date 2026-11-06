import unittest
import asyncio
import types
from supervision import evaluate, Changes


class SupervisionTests(unittest.TestCase):
 def body(self,**kw):
  return {'ready':True,'healthy':True,'active':False,'phase':'idle','settings':{'automatic':True},
          'capacity':{'capacity_kwh':23.552},'house_power_w':450,'native_program':{'register_104':1},'grid_target_w':1,**kw}
 def test_waiting_without_sun_or_energy_is_not_a_failed_sale(self):
  self.assertEqual(evaluate(self.body(reason='Čekám na blok.'),1000),[])
 def test_authorized_charging_is_not_reported_as_a_measurement_failure(self):
  self.assertEqual(evaluate(self.body(healthy=False,charging_active=True),1000),[])
 def test_missing_house_measurement_is_reported_even_when_inverter_is_healthy(self):
  self.assertIn('house_measurement',{a['code'] for a in evaluate(self.body(house_power_w=None),1000)})
 def test_unknown_measurement_startup_grace_and_native_target_difference(self):
  x=self.body(healthy=False,native_program={'register_104':20})
  self.assertNotIn('measurements',{a['code'] for a in evaluate(x,1000,started_at=990)})
  codes={a['code'] for a in evaluate(x,1100,started_at=990)}
  self.assertEqual(codes,{'measurements','grid_target'})
 def test_stuck_stop_and_missing_export_are_reported_with_native_deadlines(self):
  x=self.body(active=True,phase='measuring',battery_sale={'start':100,'end':400,'observed':False})
  self.assertIn('no_export',{a['code'] for a in evaluate(x,200)})
  self.assertIn('overdue',{a['code'] for a in evaluate(x,500)})
  x['battery_sale']['observed']=True
  self.assertNotIn('no_export',{a['code'] for a in evaluate(x,200)})
 def test_error_capacity_and_inhibited_are_not_success(self):
  x=self.body(error='Nepotvrzené ukončení',capacity={'capacity_kwh':None},settings={'inhibited':True})
  self.assertTrue({'control_error','capacity','inhibited'}<={a['code'] for a in evaluate(x,200)})
 def test_notification_changes_are_deduplicated_and_clear_when_resolved(self):
  c=Changes();alert={'code':'control_error','level':'error','message':'Chyba'}
  self.assertEqual(c.update([alert]),([alert],[]))
  self.assertEqual(c.update([alert]),([],[]))
  self.assertEqual(c.update([]),([],['control_error']))
  self.assertEqual(c.update([]),([],[]))

class NotificationTests(unittest.IsolatedAsyncioTestCase):
 async def test_delivery_is_separate_deduplicated_and_resolved(self):
  from supervision import Supervisor
  calls=[];tasks=[]
  async def call(domain,service,data,blocking):calls.append((domain,service,dict(data)))
  hass=types.SimpleNamespace(services=types.SimpleNamespace(async_call=call),
   states=types.SimpleNamespace(async_set=lambda *a:None),async_create_task=lambda c:tasks.append(asyncio.create_task(c)))
  s=Supervisor(hass,clock=lambda:1000)
  body=SupervisionTests().body(native_program={'register_104':20})
  s.publish(body);self.assertEqual(calls,[])
  await asyncio.gather(*tasks);tasks.clear()
  self.assertEqual(len([x for x in calls if x[1]=='create']),1)
  before=len(calls);s.publish(body);await asyncio.gather(*tasks)
  self.assertEqual(len(calls),before)
  body['native_program']['register_104']=1;s.publish(body);await asyncio.gather(*tasks)
  self.assertEqual(calls[-1][1],'dismiss')
  self.assertEqual(calls[-1][2]['notification_id'],'jarvis_solar_grid_target')

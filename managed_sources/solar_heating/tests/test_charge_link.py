import time,unittest
from datetime import datetime,timezone
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock,patch
from charge_link import ChargeLink

class LinkTests(unittest.IsolatedAsyncioTestCase):
 def make(self,old=False,power='-1000'):
  now=time.time();c=NS(active=True,record={'purpose':'heating','phase':'running','started_at':now-2,'target':90},observed=False,error='',heating_ready=lambda **kw:True,healthy=lambda:True,start_heating=AsyncMock(),stop=AsyncMock())
  stamp=datetime.fromtimestamp(now-100 if old else now-1,timezone.utc)
  values={f'sensor.inverter_{k}':NS(state=v,last_updated=stamp) for k,v in dict(battery_power=power,grid_power='1400',battery='30').items()}
  h=NS(data={'jarvis_spot_control':c},states=NS(get=values.get));link=ChargeLink(h)
  return link,c,values
 async def test_wait_for_actual_charge_before_heater_can_be_admitted(self):
  link,c,v=self.make();c.heating_ready=lambda **kw:False
  async def started(_,**kw):c.heating_ready=lambda **kw:True
  c.start_heating=started
  await link.start();self.assertTrue(c.observed);self.assertFalse(c.stop.called)
 async def test_stale_power_cannot_confirm_new_charge(self):
  link,c,v=self.make(old=True);first=[True]
  def ready(**kw):
   if first[0]:first[0]=False;return False
   return True
  c.heating_ready=ready
  with patch('charge_link.asyncio.sleep',new=AsyncMock()):
   with self.assertRaises(ValueError):await link.start()
  c.stop.assert_awaited_once()
 async def test_stop_does_not_touch_unrelated_manual_charging(self):
  link,c,v=self.make();c.record['purpose']='test';await link.stop();c.stop.assert_not_awaited()
 async def test_lost_charge_flow_has_short_transfer_tolerance_then_stops_readiness(self):
  link,c,v=self.make();await link.start();self.assertTrue(link.ready())
  v['sensor.inverter_battery_power'].state='1000';v['sensor.inverter_battery'].state='40'
  self.assertTrue(link.ready())
  link.flow_lost_since=time.time()-31;self.assertFalse(link.ready())
 async def test_existing_session_still_requires_actual_charge_for_second_start(self):
  link,c,v=self.make();await link.start();v['sensor.inverter_battery_power'].state='1000'
  with patch('charge_link.asyncio.sleep',new=AsyncMock()):
   with self.assertRaises(ValueError):await link.start()
  c.stop.assert_awaited_once()
 async def test_two_heaters_require_fresh_higher_charging_power(self):
  link,c,v=self.make();await link.start()
  async def resize(_,heaters):
   c.record.update(heaters=heaters,target_w=1000*heaters,power_changed_at=time.time())
  c.start_heating=resize
  async def measured(_):
   for state in v.values():state.last_updated=datetime.now(timezone.utc)
   v['sensor.inverter_battery_power'].state='-1900'
  with patch('charge_link.asyncio.sleep',new=measured):await link.start(heaters=2)
  self.assertTrue(link.flow_ok());self.assertEqual(c.record['target_w'],2000)

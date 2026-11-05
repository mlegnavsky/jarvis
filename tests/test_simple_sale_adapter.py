"""Simple policy routes battery I/O exclusively through the native controller."""
import copy
from datetime import datetime, timezone
import math
import time
import types
import unittest
from unittest.mock import patch
from zoneinfo import ZoneInfo
import test_sale_adapter as fixtures


class FakeBattery:
 def __init__(self,native_read,native_write,telemetry,save,event,clock=time.time,saved=None):
  self.native_read,self.native_write,self.telemetry,self.save,self.event=native_read,native_write,telemetry,save,event
  self.record=copy.deepcopy(saved or {});self.error='';self.last_stop=None;self.starts=[];self.adjustments=[];self.stops=[]
 @property
 def active(self):return bool(self.record.get('before'))
 @property
 def observed(self):return bool(self.record.get('observed'))
 async def start(self,power_w,duration_minutes,minimum_soc,quotes,**kwargs):
  self.starts.append((power_w,duration_minutes,minimum_soc,quotes,kwargs))
  start=math.ceil((time.time()+60)/300)*300
  self.record={'before':{'143':9300},'id':'battery-test','phase':'armed','power_w':power_w,'minimum_soc':minimum_soc,
   'start':start,'end':min(start+duration_minutes*60,kwargs.get('window_end',float('inf'))),'purpose':kwargs.get('purpose'),'observed':False,'maximum_power_w':kwargs.get('maximum_power_w',power_w)}
  await self.save(self.record)
 async def tick(self):pass
 async def adjust_power(self,power):self.adjustments.append(power);self.record['power_w']=power;await self.save(self.record)
 async def stop(self,reason='manual'):
  self.stops.append(reason)
  if self.active:
   self.last_stop={'id':self.record['id'],'purpose':self.record.get('purpose'),'reason':reason,'stop_verified':True,'native_expiry_observed':False,'production_verified':False}
   self.record={};await self.save({})


class SimpleAdapterTests(unittest.IsolatedAsyncioTestCase):
 asyncSetUp=fixtures.AdapterTests.asyncSetUp
 asyncTearDown=fixtures.AdapterTests.asyncTearDown
 service=fixtures.AdapterTests.service
 def poll(self):
  fixtures.AdapterTests.poll(self)
  if hasattr(self,'clock'):self.refresh()

 async def setup(self):
  self.clock=[round(time.time(),6)]
  self.clock_patch=patch.object(self.module.time,'time',lambda:self.clock[0]);self.clock_patch.start()
  self.addCleanup(self.clock_patch.stop)
  self.storage=fixtures.Store()
  self.module.Store=lambda *args:self.storage
  self.assertTrue(hasattr(self.module,'BatterySaleController'),'native battery controller must be integrated')
  self.module.BatterySaleController=FakeBattery
  values={'sensor.inverter_load_power':1000,'sensor.inverter_battery_voltage':52,'sensor.inverter_battery_current':0,
   'select.inverter_time_of_use':'Week','number.inverter_battery_max_discharging_current':175,'number.inverter_battery_max_charging_current':175}
  for i in range(1,7):
   values.update({f'number.inverter_program_{i}_soc':30,f'number.inverter_program_{i}_power':10000,
    f'select.inverter_program_{i}_charging':'Disabled',f'time.inverter_program_{i}_time':f'{(i-1)*4:02d}:00:00'})
  for key,value in values.items():self.hass.states.async_set(key,value)
  registers={0:5,98:1,109:175,111:1,130:0,142:2,143:9300,145:0,146:255,219:200,340:12000}
  for address in range(98,112):registers.setdefault(address,0)
  for address in range(142,178):registers.setdefault(address,0)
  for i in range(6):registers.update({148+i:i*400,154+i:10000,166+i:30,172+i:0})
  self.native_registers=registers
  async def execute(code,address,count=1,**kwargs):
   if code==16:
    for i,value in enumerate(kwargs['data']):registers[address+i]=value
    return kwargs['data']
   if address==62:
    dt=datetime.fromtimestamp(self.clock[0],ZoneInfo('Europe/Prague'))
    return [((dt.year-2000)<<8)|dt.month,(dt.day<<8)|dt.hour,(dt.minute<<8)|dt.second]
   if address in (142,143,145,104) and count==1:return [self.device_registers[address]]
   return [registers.get(address+i,0) for i in range(count)]
  self.hass.config_entries.async_entries('solarman')[0].runtime_data.device.execute=execute
  await self.module.async_setup_sales(self.hass,{},types.SimpleNamespace(active=False))
  data=self.hass.data[self.module.KEY]
  self.refresh();await self.ticks[0]()
  return data

 def refresh(self):
  for state in self.hass.states.async_all():
   state.last_updated=state.last_reported=datetime.fromtimestamp(self.clock[0],timezone.utc)

 def prices(self,start,net_eur=100):
  rows=[{'time':datetime.fromtimestamp(start+i*900,timezone.utc).isoformat(),'eur_mwh':net_eur} for i in range(-1,12)]
  self.hass.states.async_set('sensor.jarvis_spot_ote',1,{'fetched_at':datetime.fromtimestamp(self.clock[0],timezone.utc).isoformat(),'rate':25,'rows':rows})

 async def test_manual_battery_never_uses_legacy_sale_route(self):
  data=await self.setup();data['settings'].update(battery_verified=True,pv_verified=True)
  start=math.floor(self.clock[0]/900)*900;self.prices(start)
  self.refresh()
  await self.service('start_sale',{'mode':'battery','power_w':9300,'duration_minutes':30})
  self.assertTrue(data['battery_controller'].active)
  self.assertFalse(data['controller'].active)
  self.assertLessEqual(data['battery_controller'].starts[0][0],3000)
  self.assertEqual(data['battery_controller'].starts[0][2],60)
  self.assertIn('battery_sale',self.storage.data)

 async def test_unverified_battery_does_not_start_from_native_pilot_proof(self):
  data=await self.setup();data['window'].last_stop={'id':'pilot','native_expiry_observed':True,'stop_verified':True,'production_verified':False}
  await self.ticks[0]()
  self.assertFalse(data['settings']['battery_verified'])
  self.assertEqual(data['settings']['native_window_proof']['id'],'pilot')
  with self.assertRaises(ValueError):await self.service('start_sale',{'mode':'battery','power_w':500,'duration_minutes':5})

 async def test_actual_soc_budget_starts_native_segment_without_forecast_gate(self):
  data=await self.setup();data['settings'].update(automatic=True,pv_verified=True,battery_verified=True)
  start=math.ceil(self.clock[0]/900)*900
  self.clock[0]=start-60;self.prices(start)
  self.hass.states.async_set('sensor.inverter_battery',90)
  data['planning']['snapshot']=lambda:(_ for _ in ()).throw(ValueError('optional forecast broken'))
  self.refresh();await self.ticks[0]()
  controller=data['battery_controller'];self.assertTrue(controller.active)
  power,minutes,floor,quotes,options=controller.starts[0]
  self.assertLessEqual(power,3000);self.assertGreater(power,0)
  self.assertLessEqual(minutes,60);self.assertEqual(floor,60)
  self.assertEqual(options['window_end'],data['settings']['selected_block']['end'])
  self.assertEqual(options['maximum_power_w'],3000)
  attrs=self.hass.states.get('sensor.jarvis_energy_sales').attributes
  self.assertEqual(attrs['mode'],'battery');self.assertTrue(attrs['active'])
  self.assertFalse(attrs['observed']);self.assertEqual(attrs['sale_floor_soc'],60)

 async def test_native_preparation_starts_three_minutes_early_and_resizes_at_t_minus_one(self):
  data=await self.setup();data['settings'].update(automatic=True,pv_verified=True,battery_verified=True)
  start=math.ceil(self.clock[0]/900)*900
  self.clock[0]=start-180;self.prices(start);self.refresh()
  self.hass.states.async_set('sensor.inverter_battery',90);self.refresh()
  await self.ticks[0]()
  battery=data['battery_controller'];self.assertTrue(battery.active)
  first_power=battery.record['power_w'];chosen=copy.deepcopy(data['settings']['selected_block'])
  self.clock[0]=start-60;self.refresh()
  self.hass.states.async_set('sensor.inverter_battery',70);self.refresh()
  await self.ticks[0]()
  self.assertTrue(battery.active);self.assertLess(battery.record['power_w'],first_power)
  self.assertEqual(data['settings']['selected_block'],chosen)
  self.assertEqual(battery.record['minimum_soc'],60)

 async def test_stale_house_measurement_prevents_native_battery_start(self):
  data=await self.setup();data['settings'].update(automatic=True,pv_verified=True,battery_verified=True)
  start=math.ceil(self.clock[0]/900)*900;self.clock[0]=start-60;self.prices(start);self.refresh()
  self.hass.states.get('sensor.inverter_load_power').last_reported=datetime.fromtimestamp(self.clock[0]-60,timezone.utc)
  await self.ticks[0]()
  self.assertFalse(data['battery_controller'].active)

 async def test_manual_stop_includes_battery_and_aggregate_interlock(self):
  data=await self.setup();battery=data['battery_controller']
  battery.record={'id':'x','before':{'143':9300},'phase':'armed','power_w':500,'end':self.clock[0]+300}
  await data['report']();attrs=self.hass.states.get('sensor.jarvis_energy_sales').attributes
  self.assertTrue(attrs['active']);self.assertIn(battery,data['controllers'])
  await data['stop']();self.assertFalse(battery.active);self.assertFalse(data['settings']['automatic'])

 async def test_dark_or_cooldown_pv_cannot_start(self):
  data=await self.setup();data['settings'].update(automatic=True,pv_verified=True)
  self.hass.states.async_set('sensor.inverter_pv_power',0);self.refresh();await self.ticks[0]()
  self.assertFalse(data['controller'].active)
  self.hass.states.async_set('sensor.inverter_pv_power',400)
  data['settings']['cooldown_until']=self.clock[0]+300
  self.refresh();await self.ticks[0]()
  self.assertFalse(data['controller'].active)

 async def test_full_daylight_battery_may_probe_curtailed_zero_pv(self):
  data=await self.setup();data['settings'].update(automatic=True,pv_verified=True)
  self.prices(math.floor(self.clock[0]/900)*900)
  self.hass.states.async_set('sensor.inverter_pv_power',0)
  self.hass.states.async_set('sun.sun','above_horizon')
  self.refresh();await self.ticks[0]()
  self.assertTrue(data['controller'].active,self.hass.states.get('sensor.jarvis_energy_sales').attributes['error'])

 async def test_fixed_battery_commission_and_strict_acceptance_keep_auto_off(self):
  data=await self.setup();self.prices(math.floor(self.clock[0]/900)*900);self.refresh()
  await data['commission_battery']()
  power,minutes,floor,quotes,options=data['battery_controller'].starts[0]
  self.assertEqual((power,minutes,floor),(500,5,90));self.assertEqual(options['maximum_power_w'],500)
  await data['battery_controller'].stop('manual')
  proof={'id':'accepted','phase':'complete','observed':True,'native_expiry_observed':True,'stop_verified':True,'reason':'deadline','purpose':'commission','power_w':500,'minimum_soc':90}
  data['battery_controller'].last_stop=proof;await self.ticks[0]()
  self.assertTrue(data['settings']['battery_verified']);self.assertFalse(data['settings']['automatic'])
  self.assertEqual(data['settings']['battery_sale_proof'],proof)
  for key in ('observed','native_expiry_observed','stop_verified'):
   data['settings']['battery_verified']=False
   data['battery_controller'].last_stop={**proof,'id':'bad-'+key,key:1}
   await self.ticks[0]()
   self.assertFalse(data['settings']['battery_verified'])

 async def test_native_stop_with_owner_conflict_inhibits_even_after_normal_deadline(self):
  data=await self.setup()
  for purpose in ('commission','automatic'):
   data['settings'].update(automatic=True,battery_verified=False,inhibited=False)
   data['battery_controller'].last_stop={'id':'conflict-'+purpose,'phase':'complete','purpose':purpose,'reason':'deadline','power_w':500,'minimum_soc':90,'observed':True,'native_expiry_observed':True,'stop_verified':True,'conflicts':{'166':{'value':45}}}
   await self.ticks[0]()
   self.assertFalse(data['settings']['automatic']);self.assertTrue(data['settings']['inhibited'])
   self.assertFalse(data['settings']['battery_verified'])

 async def test_manual_native_cap_cannot_be_increased_by_budget_resize(self):
  data=await self.setup();data['settings'].update(battery_verified=True,pv_verified=True)
  self.prices(math.floor(self.clock[0]/900)*900);self.refresh()
  await self.service('start_sale',{'mode':'battery','power_w':500,'duration_minutes':5})
  battery=data['battery_controller'];self.clock[0]+=5;self.refresh();await self.ticks[0]()
  self.assertTrue(battery.active);self.assertEqual(battery.record['maximum_power_w'],500)
  self.assertTrue(all(power<=500 for power in battery.adjustments))

 async def test_clock_admission_rechecks_mode_after_awaited_audit(self):
  data=await self.setup();self.prices(math.floor(self.clock[0]/900)*900);self.refresh()
  device=self.hass.config_entries.async_entries('solarman')[0].runtime_data.device
  original=device.execute
  async def skewed(code,address,count=1,**kwargs):
   if address==62:
    dt=datetime.fromtimestamp(self.clock[0]-60,ZoneInfo('Europe/Prague'))
    return [((dt.year-2000)<<8)|dt.month,(dt.day<<8)|dt.hour,(dt.minute<<8)|dt.second]
   return await original(code,address,count=count,**kwargs)
  device.execute=skewed
  append=data['journal'].append
  def changed(kind,*args):
   if kind=='native_clock_sync_intent':self.native_registers[142]=self.device_registers[142]=0
   return append(kind,*args)
  data['journal'].append=changed
  called=[]
  async def sync(*args,**kwargs):called.append(True);return {'verified':True}
  self.module.sync_native_clock=sync
  with self.assertRaises(ValueError):await data['commission_battery']()
  self.assertEqual(called,[])


if __name__=='__main__':unittest.main()

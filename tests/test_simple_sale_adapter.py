"""Simple policy routes battery I/O exclusively through the native controller."""
import copy
from datetime import datetime, timezone, timedelta
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
  if hasattr(self,'clock'):self.clock[0]+=1
  fixtures.AdapterTests.poll(self)
  if hasattr(self,'clock'):self.refresh()

 async def test_report_publishes_configured_capacity_and_canonical_house_power(self):
  data=await self.setup()
  self.hass.states.async_set('sensor.jarvis_spotreba_domu',720)
  self.hass.states.async_set('sensor.inverter_load_power',0)
  self.hass.states.async_set('select.inverter_work_mode','Export First')
  self.refresh();await data['report']()
  a=self.hass.states.get('sensor.jarvis_energy_sales').attributes
  self.assertEqual(a['capacity']['capacity_kwh'],23.552)
  self.assertFalse(a['capacity']['physical_verified'])
  self.assertEqual(a['house_power_w'],720)

 async def test_verified_bias_runs_only_outside_higher_priority_sales_and_above_resume_floor(self):
  data=await self.setup();data['settings'].update(automatic=True,pv_verified=True,bias_verified=True,bias_enabled=True,battery_verified=False)
  quarter=math.floor(self.clock[0]/900)*900;self.prices(quarter,net_eur=-100)
  self.hass.states.async_set('sensor.inverter_battery',63);self.refresh();await self.ticks[0]()
  self.assertTrue(data['controller'].active)
  self.assertEqual(data['controller'].record['mode'],'bias')
  self.assertEqual(data['controller'].record['power_w'],2)
  self.assertEqual(data['controller'].record['minimum_soc'],30)

 async def test_night_high_soc_does_not_interrupt_bias_without_actual_pv_opportunity(self):
  data=await self.setup();data['settings'].update(automatic=True,pv_verified=True,bias_verified=True,bias_enabled=True,battery_verified=False)
  quarter=math.floor(self.clock[0]/900)*900;self.prices(quarter)
  self.hass.states.async_set('sensor.inverter_battery',98);self.hass.states.async_set('sensor.inverter_pv_power',0);self.hass.states.async_set('sun.sun','below_horizon');self.refresh()
  await data['controller'].start('bias',2,60,minimum_soc=30,purpose='automatic')
  before=data['controller'].record['id'];self.refresh();await self.ticks[0]()
  self.assertTrue(data['controller'].active);self.assertEqual(data['controller'].record['id'],before);self.assertNotEqual(data['controller'].record['phase'],'stopping')

 async def test_repeat_bias_probe_revokes_old_proof_even_if_preparation_fails(self):
  data=await self.setup();data['settings'].update(automatic=True,bias_verified=True,inhibited=False)
  self.hass.states.async_set('sensor.inverter_battery',31);self.refresh()
  with self.assertRaises(ValueError):await data['bias_probe']()
  self.assertFalse(data['settings']['automatic']);self.assertFalse(data['settings']['bias_verified']);self.assertTrue(data['settings']['inhibited'])
  self.assertFalse(data['controller'].active)

 async def test_bias_cannot_start_before_physical_verification(self):
  data=await self.setup();data['settings'].update(automatic=True,pv_verified=True,bias_verified=False,bias_enabled=True)
  quarter=math.floor(self.clock[0]/900)*900;self.prices(quarter)
  self.hass.states.async_set('sensor.inverter_battery',63);self.refresh();await self.ticks[0]()
  self.assertFalse(data['controller'].active)

 async def test_missing_capacity_blocks_manual_battery_start(self):
  data=await self.setup();data['settings']['battery_verified']=True
  self.hass.states.async_set('number.inverter_battery_capacity','unavailable')
  with self.assertRaises(ValueError):await data['start']({'mode':'battery','power_w':500,'duration_minutes':5})
  self.assertEqual(data['battery_controller'].starts,[])

 async def test_stale_capacity_setting_is_not_an_available_sale_budget(self):
  data=await self.setup();data['settings']['battery_verified']=True
  state=self.hass.states.get('number.inverter_battery_capacity')
  state.last_updated=state.last_reported=datetime.fromtimestamp(self.clock[0]-601,timezone.utc)
  await data['report']()
  self.assertIsNone(self.hass.states.get('sensor.jarvis_energy_sales').attributes['capacity']['capacity_kwh'])
  with self.assertRaises(ValueError):await data['start']({'mode':'battery','power_w':500,'duration_minutes':5})

 async def test_failed_native_expiry_revokes_battery_verification_and_automatic(self):
  data=await self.setup();data['settings'].update(battery_verified=True,automatic=True)
  data['battery_controller'].last_stop={'id':'failedend','purpose':'manual','reason':'deadline',
    'phase':'complete','observed':True,'native_expiry_observed':False,'stop_verified':True,'conflicts':{}}
  await self.ticks[0]()
  self.assertFalse(data['settings']['automatic']);self.assertFalse(data['settings']['battery_verified'])
  self.assertTrue(data['settings']['inhibited'])

 async def test_near_full_pv_surplus_runs_outside_future_battery_block(self):
  data=await self.setup();data['settings'].update(automatic=True,pv_verified=True,battery_verified=True)
  quarter=math.floor(self.clock[0]/900)*900;self.prices(quarter)
  data['settings']['selected_block']={'start':quarter+3600,'end':quarter+10800}
  self.hass.states.async_set('sensor.inverter_battery',98)
  self.hass.states.async_set('sensor.inverter_pv_power',1500)
  self.refresh();await self.ticks[0]()
  self.assertTrue(data['controller'].active)
  self.assertFalse(data['battery_controller'].active)
  self.assertEqual(data['controller'].record['mode'],'pv')
  self.assertEqual(data['controller'].record['power_w'],9300)

 async def test_near_full_pv_stays_blocked_at_negative_net_price(self):
  data=await self.setup();data['settings'].update(automatic=True,pv_verified=True)
  quarter=math.floor(self.clock[0]/900)*900;self.prices(quarter,net_eur=-100)
  self.hass.states.async_set('sensor.inverter_battery',99)
  self.hass.states.async_set('sensor.inverter_pv_power',1500)
  self.refresh();await self.ticks[0]()
  self.assertFalse(data['controller'].active)

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
  registers={0:5,98:1,109:175,111:1,130:0,142:2,143:9300,145:0,146:255,213:200,219:200,340:12000}
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

 async def test_zero_target_holds_exclusive_lock_and_rechecks_command_expiry(self):
  data=await self.setup();deadline=self.clock[0]+10
  async def helper(device,ready,event):
   self.assertTrue(data['busy']());self.assertTrue(ready())
   self.clock[0]=deadline+1;self.refresh();self.assertFalse(ready())
   return {'verified':False,'actual_w':20}
  with patch.object(self.module,'set_zero_target',side_effect=helper):
   with self.assertRaises(ValueError):await data['zero_import_target'](deadline)
  self.assertIsNone(data['settings']['native_grid_target_w'])
  self.assertEqual(data['settings']['zero_target_proof']['actual_w'],20)
  self.assertFalse(data['settings']['zero_target_proof']['verified'])
 async def test_zero_target_cannot_run_during_native_battery_sale(self):
  data=await self.setup();data['battery_controller'].record={'before':{'143':9300},'phase':'armed'}
  with patch.object(self.module,'set_zero_target') as helper:
   with self.assertRaises(ValueError):await data['zero_import_target']()
   helper.assert_not_called()

 async def test_manual_battery_never_uses_legacy_sale_route(self):
  data=await self.setup();data['settings'].update(battery_verified=True,pv_verified=True)
  start=math.floor(self.clock[0]/900)*900;self.prices(start)
  self.refresh()
  await self.service('start_sale',{'mode':'battery','power_w':9300,'duration_minutes':30})
  self.assertTrue(data['battery_controller'].active)
  self.assertFalse(data['controller'].active)
  self.assertLessEqual(data['battery_controller'].starts[0][0],9300)
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
  self.assertLessEqual(power,9300);self.assertGreater(power,0)
  self.assertLessEqual(minutes,60);self.assertEqual(floor,60)
  self.assertEqual(options['window_end'],data['settings']['selected_block']['end'])
  self.assertEqual(options['maximum_power_w'],9300)
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
  proof={'id':'accepted','phase':'complete','observed':True,'native_expiry_observed':True,'stop_verified':True,'reason':'deadline','purpose':'commission','power_w':500,'minimum_soc':90,'native_power_fence':True}
  data['battery_controller'].last_stop=proof;await self.ticks[0]()
  self.assertTrue(data['settings']['battery_verified']);self.assertFalse(data['settings']['automatic'])
  self.assertEqual(data['settings']['battery_sale_proof'],proof)
  for key in ('observed','native_expiry_observed','stop_verified'):
   data['settings']['battery_verified']=False
   data['battery_controller'].last_stop={**proof,'id':'bad-'+key,key:1}
   await self.ticks[0]()
   self.assertFalse(data['settings']['battery_verified'])

 async def test_explicit_60_percent_commission_uses_fixed_bounded_power_and_needs_fenced_proof(self):
  data=await self.setup();self.prices(math.floor(self.clock[0]/900)*900)
  self.hass.states.async_set('sensor.inverter_battery',63);self.refresh()
  await data['commission_battery'](minimum_soc=60)
  self.assertEqual(data['battery_controller'].starts[0][:3],(500,5,60))
  await data['battery_controller'].stop('manual')
  proof={'id':'fenced','phase':'complete','observed':True,'native_expiry_observed':True,'stop_verified':True,'reason':'deadline','purpose':'commission','power_w':500,'minimum_soc':60,'native_power_fence':True}
  data['battery_controller'].last_stop=proof;await self.ticks[0]()
  self.assertTrue(data['settings']['battery_verified']);self.assertFalse(data['settings']['automatic'])
  data['settings']['battery_verified']=False
  data['battery_controller'].last_stop={**proof,'id':'unfenced','native_power_fence':False};await self.ticks[0]()
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

 async def test_late_automatic_segment_clips_at_2340_without_rebudgeting(self):
  data=await self.setup();data['settings'].update(automatic=True,pv_verified=True,battery_verified=True)
  local=datetime.fromtimestamp(self.clock[0],ZoneInfo('Europe/Prague'))
  start=local.replace(hour=22,minute=0,second=0,microsecond=0).timestamp()
  self.clock[0]=local.replace(hour=23,minute=0,second=0,microsecond=0).timestamp()
  self.prices(start);data['settings']['selected_block']={'start':start,'end':start+7200}
  self.hass.states.async_set('sensor.inverter_battery',70);self.refresh()
  await self.ticks[0]()
  battery=data['battery_controller'];self.assertTrue(battery.active)
  cutoff=local.replace(hour=23,minute=40,second=0,microsecond=0).timestamp()
  self.assertEqual(battery.starts[0][4]['window_end'],cutoff)
  self.assertLessEqual(battery.record['end'],cutoff)
  expected=self.module.size_sale(70,23.552,start,start+7200,self.clock[0],1000,max_export_w=3000)['power_w']
  self.assertEqual(battery.starts[0][0],expected)

 async def test_after_2340_is_normal_hold_and_next_day_automatic_still_starts(self):
  data=await self.setup();data['settings'].update(automatic=True,pv_verified=True,battery_verified=True)
  local=datetime.fromtimestamp(self.clock[0],ZoneInfo('Europe/Prague'))
  start=local.replace(hour=22,minute=0,second=0,microsecond=0).timestamp()
  self.clock[0]=local.replace(hour=23,minute=41,second=0,microsecond=0).timestamp()
  self.prices(start);data['settings']['selected_block']={'start':start,'end':start+7200}
  self.hass.states.async_set('sensor.inverter_battery',80);self.refresh()
  await self.ticks[0]()
  self.assertFalse(data['battery_controller'].active)
  self.assertTrue(data['settings']['automatic']);self.assertFalse(data['settings'].get('inhibited',False))
  tomorrow=local.replace(hour=11,minute=0,second=0,microsecond=0)+timedelta(days=1)
  self.clock[0]=tomorrow.timestamp()-180;self.prices(tomorrow.timestamp());self.refresh()
  await self.ticks[0]()
  self.assertTrue(data['battery_controller'].active)
  self.assertTrue(data['settings']['automatic'])


if __name__=='__main__':unittest.main()

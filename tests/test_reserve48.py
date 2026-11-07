import unittest,sys
from datetime import datetime,timedelta,timezone
sys.path.insert(0,'managed_sources/spot_control')
from weather_reserve import calculate_reserve,TZ
from test_weather_reserve import fixture

class Reserve48(unittest.TestCase):
 def plan(self,first=30,second=30,charge=6,day='2026-11-07'):
  w,b,n=fixture(30,day)
  base=datetime.fromtimestamp(b['start'],TZ).replace(hour=0,minute=0,second=0,microsecond=0)
  rows=[]
  for i in range(97):
   dt=datetime.fromtimestamp(base.timestamp()+i*3600,TZ)
   kwh=first if dt.date()==(base+timedelta(days=1)).date() else second
   g=kwh/(10.12*.8054584854081006)/8*1000 if 9<=dt.hour<=16 else 0
   rows.append({'time':dt.isoformat(),'global_tilted_irradiance':g})
  w['rows']=rows
  return calculate_reserve(w,b,n,23.552,6,60,charge_limit_kw=charge)
 def test_existing_api_must_cover_two_days(self):
  w,b,n=fixture();p=calculate_reserve(w,b,n,23.552,6)
  self.assertEqual(p['horizon_end']-p['horizon_start'],172800)
 def test_two_good_days_keep_60_and_model_48_real_hours(self):
  p=self.plan();self.assertEqual(p['required_soc'],60);self.assertEqual(p['horizon_end']-p['horizon_start'],172800)
  self.assertEqual(len(p['forecast_days']),2);self.assertGreater(p['battery_charge_credit_kwh'],0)
  self.assertGreaterEqual(p['lowest_soc'],30);self.assertEqual(p['night_usage_soc'],20)
 def test_far_day_weak_requires_at_least_75(self):
  p=self.plan(30,5);self.assertGreaterEqual(p['required_soc'],75);self.assertEqual(p['weather_tier_soc'],75)
 def test_two_weak_days_raise_90_or_100(self):
  self.assertGreaterEqual(self.plan(5,5)['required_soc'],90)
  self.assertEqual(self.plan(1,1)['required_soc'],100)
 def test_no_charge_proof_cannot_credit_future_surplus(self):
  p=self.plan(charge=0);self.assertEqual(p['battery_charge_credit_kwh'],0)
  self.assertGreater(p['required_soc'],self.plan()['required_soc'])
 def test_limited_charge_and_capacity_clipping_are_respected(self):
  p=self.plan(charge=.1)
  for row in p['intervals']:
   self.assertLessEqual(row['charge_kwh'],.1*(row['end']-row['start'])/3600+1e-4)
   self.assertLessEqual(row['battery_soc'],100.0001)
 def test_dst_uses_elapsed_48_hours(self):
  for day in ['2026-03-28','2026-10-24']:
   p=self.plan(day=day);self.assertEqual(p['quality'],'estimated');self.assertEqual(p['horizon_end']-p['horizon_start'],172800)
 def test_missing_second_day_is_unavailable(self):
  w,b,n=fixture();w['rows']=w['rows'][:48]
  self.assertEqual(calculate_reserve(w,b,n,23.552,6,charge_limit_kw=6)['quality'],'unavailable')
 def test_no_solar_can_be_borrowed_before_it_arrives(self):
  p=self.plan(0,30)
  # The first night/day plus second night must be funded before day2 sunlight.
  self.assertGreaterEqual(p['required_soc'],90)
  self.assertGreaterEqual(p['energy_floor_soc'],80)
 def test_fractional_sunset_full_night_budget_is_exact(self):
  w,b,n=fixture(0)
  # A15h20m night must receive its full25SOC budget, not15 midpoint hours.
  w['daily']=[{'time':'2026-11-07','sunset':'2026-11-07T18:20:00+01:00'}, {'time':'2026-11-08','sunrise':'2026-11-08T07:40:00+01:00'}]
  p=calculate_reserve(w,b,n,23.552,0,charge_limit_kw=0)
  night=[r for r in p['intervals'] if r['start']<datetime.fromisoformat('2026-11-08T09:40:00+01:00').timestamp()]
  self.assertAlmostEqual(sum(r['discharge_dc_kwh'] for r in night),23.552*.25,places=3)

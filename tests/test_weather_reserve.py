import unittest,sys,math
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
sys.path.insert(0,'managed_sources/spot_control')
from weather_reserve import calculate_reserve
TZ=ZoneInfo('Europe/Prague')
def fixture(kwh=15,day='2026-11-07'):
 start=datetime.fromisoformat(day+'T15:45:00').replace(tzinfo=TZ).timestamp();now=start-3600
 rows=[];base=datetime.fromtimestamp(start,TZ).replace(hour=0,minute=0,second=0,microsecond=0)
 for i in range(73):
  dt=base+timedelta(hours=i);gti=kwh/(10.12*.8054584854)/8*1000 if 9<=dt.hour<=16 else 0
  rows.append({'time':dt.isoformat(),'global_tilted_irradiance':gti})
 return {'fetched_at':datetime.fromtimestamp(now,TZ).isoformat(),'rows':rows},{'start':start,'end':start+7200,'day':day},now
class WeatherReserve(unittest.TestCase):
 def runplan(self,kwh=15,load=8,owner=60,day='2026-11-07'):
  w,b,n=fixture(kwh,day);return calculate_reserve(w,b,n,23.552,load,owner)
 def test_saturday_uses_sunday_and_keeps_75(self):
  p=self.runplan();self.assertEqual(p['forecast_day'],'2026-11-08');self.assertEqual(p['required_soc'],75);self.assertAlmostEqual(p['forecast_pv_kwh'],15,places=3);self.assertEqual(p['house_with_margin_kwh'],10)
 def test_sunny_and_weak(self):
  self.assertEqual(self.runplan(30)['required_soc'],60);self.assertEqual(self.runplan(5)['required_soc'],90);self.assertEqual(self.runplan(1)['required_soc'],100)
 def test_high_load_and_owner_raise_floor(self):
  self.assertGreaterEqual(self.runplan(15,20)['required_soc'],90);self.assertGreaterEqual(self.runplan(30,8,85)['required_soc'],85)
 def test_missing_stale_future_nan_or_incomplete_weather_stops_battery(self):
  w,b,n=fixture()
  for bad in ({},{**w,'fetched_at':datetime.fromtimestamp(n-7200,TZ).isoformat()},{**w,'fetched_at':datetime.fromtimestamp(n+900,TZ).isoformat()},{**w,'rows':w['rows'][:30]},{**w,'rows':[{**r,'global_tilted_irradiance':float('nan')} for r in w['rows']]}):
   self.assertEqual(calculate_reserve(bad,b,n,23.552,8,60)['required_soc'],100)
 def test_dst_and_future_block(self):
  for day in ['2026-03-28','2026-10-24']:
   p=self.runplan(15,day=day);self.assertEqual(p['horizon_end']-p['horizon_start'],86400);self.assertGreaterEqual(p['required_soc'],75)
 def test_capacity_and_missing_load_rejected(self):
  w,b,n=fixture()
  for cap,load in [(None,8),(23.552,None),(0,8),(23.552,float('nan'))]:self.assertEqual(calculate_reserve(w,b,n,cap,load,60)['required_soc'],100)

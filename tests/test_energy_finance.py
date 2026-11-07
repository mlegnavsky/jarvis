import datetime as dt
import pathlib
import sys
import tempfile
import unittest
sys.path.insert(0,'managed_sources/spot_control')
try:from finance import Ledger,totals
except ImportError:Ledger=totals=None

class FinanceTests(unittest.TestCase):
 def setUp(self):
  self.assertIsNotNone(totals,'live daily accounting is missing')
  self.start=dt.datetime(2026,11,5,tzinfo=dt.timezone(dt.timedelta(hours=1))).timestamp()
 def price(self,start,eur):return {'time':dt.datetime.fromtimestamp(start,dt.timezone.utc).isoformat(),'eur_mwh':eur}
 def point(self,t,p,imported=None,exported=0):return {'t':self.start+t,'grid_w':p,'import_kwh':imported,'export_kwh':exported}
 def calc(self,points,quotes=None,now=40000):return totals(points,quotes or [self.price(self.start+36000,100)],25,self.start+now)
 def test_revenue_uses_each_quarter_and_deducts_fee(self):
  p=[self.point(36885,-2000),self.point(36915,-2000)]
  out=self.calc(p,[self.price(self.start+36000,100),self.price(self.start+36900,200)])
  self.assertAlmostEqual(out['sale_czk'],(2.2+4.7)*2*15/3600)
 def test_purchase_anchors_today_counter_and_updates_from_five_second_power(self):
  out=self.calc([self.point(36000,1000,4.9),self.point(36005,1000,4.9)])
  self.assertAlmostEqual(out['purchase_czk'],(4.9+5/3600)*5)
 def test_direction_crossing_counts_two_triangles(self):
  out=self.calc([self.point(36000,1000,0),self.point(36020,-1000,0)])
  self.assertAlmostEqual(out['import_kwh'],1000*5/3600000)
  self.assertAlmostEqual(out['export_kwh'],1000*5/3600000)
 def test_gap_is_not_fabricated_as_export(self):
  out=self.calc([self.point(36000,-1000),self.point(36100,-1000,exported=1)])
  self.assertEqual(out['export_kwh'],0)
  self.assertIsNone(out['sale_czk'])
  self.assertGreater(out['unaccounted_export_kwh'],0)
 def test_unknown_export_price_is_not_zero_revenue(self):
  out=self.calc([self.point(35100,-1000),self.point(35110,-1000)])
  self.assertIsNone(out['sale_czk'])
  self.assertGreater(out['unpriced_export_kwh'],0)
 def test_negative_market_price_produces_negative_revenue(self):
  out=self.calc([self.point(36000,-1000),self.point(36010,-1000)],[self.price(self.start+36000,-10)])
  self.assertLess(out['sale_czk'],0)
 def test_midnight_does_not_copy_yesterdays_counter_into_today(self):
  out=self.calc([self.point(-10,1000,4.9),self.point(10,1000,4.9),self.point(20,1000,0)],now=30)
  self.assertLess(out['purchase_czk'],.1)
 def test_replayed_archive_and_restart_do_not_double_count(self):
  with tempfile.TemporaryDirectory() as d:
   path=pathlib.Path(d)/'finance.sqlite';book=Ledger(path)
   points=[self.point(36000,-1000),self.point(36010,-1000)]
   book.add(points);book.add(points)
   reloaded=Ledger(path)
   out=reloaded.today([self.price(self.start+36000,100)],25,self.start+40000)
   self.assertEqual(out['samples'],2)
   self.assertAlmostEqual(out['sale_czk'],2.2*10/3600)

 def test_missing_noon_history_is_not_presented_as_complete_zero_cash(self):
  out=self.calc([self.point(36000,0,exported=None)])
  self.assertIsNone(out['purchase_czk']);self.assertIsNone(out['sale_czk'])
  self.assertEqual(out['quality'],'partial')
 def test_small_previous_day_counter_reset_does_not_carry_a_false_charge(self):
  out=self.calc([self.point(-10,0,.1),self.point(10,0,.1),self.point(20,0,0)],now=30)
  self.assertEqual(out['purchase_czk'],0)

if __name__=='__main__':unittest.main()

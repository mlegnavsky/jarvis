import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'managed_sources/spot_control'))
from finance import totals,day_bounds
class OwnerRateTests(unittest.TestCase):
 def test_rate_changes_do_not_reprice_past_delivery(self):
  now=1793977200.;_,start,_=day_bounds(now);at=start+30
  pts=[{'t':start,'grid_w':-1000},{'t':start+30,'grid_w':-1000},{'t':start+60,'grid_w':-1000}]
  from datetime import datetime,timezone
  quotes=[{'time':datetime.fromtimestamp(start,timezone.utc).isoformat(),'eur_mwh':100}]
  result=totals(pts,quotes,25,start+60,rate_history=[{'at':at,'purchase_rate':6,'sale_fee':.5}])
  self.assertAlmostEqual(result['known_sale_czk'],(2.2+2.)/120)
 def test_missing_quote_does_not_create_negative_known_revenue(self):
  now=1793977200.;_,start,_=day_bounds(now)
  pts=[{'t':start,'grid_w':-1000},{'t':start+30,'grid_w':-1000}]
  result=totals(pts,[],25,start+30,rate_history=[{'at':start,'purchase_rate':5,'sale_fee':.5}])
  self.assertEqual(result['known_sale_czk'],0)

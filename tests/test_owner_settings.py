import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'managed_sources/spot_control'))
from owner_settings import DEFAULTS,validate,revision,rate_at
class OwnerSettingsTests(unittest.TestCase):
 def test_defaults_match_current_policy(self):
  self.assertEqual((DEFAULTS['pv_soc'],DEFAULTS['home_soc'],DEFAULTS['sale_soc'],DEFAULTS['bias_w'],DEFAULTS['block_minutes'],DEFAULTS['max_w']),(97,30,60,20,120,9300))
 def test_validate_cross_fields_and_no_automatic_keys(self):
  for changes in ({'automatic':True},{'sale_soc':29},{'home_soc':60},{'pv_soc':59},{'bias_w':float('nan')},{'max_w':9500},{'block_minutes':16},{'bias_w':True}):
   with self.assertRaises(ValueError):validate(DEFAULTS,changes)
  self.assertEqual(validate(DEFAULTS,{'sale_soc':65,'pv_soc':98})['sale_soc'],65)
 def test_canonical_revision(self):self.assertEqual(revision({'a':1,'b':2}),revision({'b':2,'a':1}))
 def test_dated_rates_preserve_past(self):
  rows=[{'at':100,'purchase_rate':6,'sale_fee':.4}]
  self.assertEqual(rate_at(rows,99),{'purchase_rate':5,'sale_fee':.3})
  self.assertEqual(rate_at(rows,100),{'purchase_rate':6,'sale_fee':.4})

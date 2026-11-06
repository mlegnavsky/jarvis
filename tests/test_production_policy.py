import sys,unittest
sys.path.insert(0,'managed_sources/spot_control')
from production_policy import decide_production,home_profile,block_key,completed_selection
class ProductionPolicyTests(unittest.TestCase):
 def setUp(self):self.p={'sale_soc':60,'pv_soc':97,'home_soc':30,'resume_soc':31,'bias_w':20,'max_w':9300};self.block={'start':100,'end':500,'day':'2026-11-06'}
 def decide(self,**kw):
  args=dict(policy=self.p,settings={'pv_verified':True,'bias_verified':True,'bias_enabled':True},block=self.block,price={'start':0,'end':900,'net':5},now=200,soc=80,pv_available=True,profile_ready=True)
  args.update(kw);return decide_production(**args)
 def test_priority_schedule_then_pv_then_bias(self):
  self.assertEqual(self.decide()['mode'],'battery')
  self.assertEqual(self.decide(soc=99,now=600)['mode'],'pv')
  self.assertEqual(self.decide(soc=61,now=600)['mode'],'bias')
 def test_completed_floor_cannot_restart_after_rebound(self):
  self.assertEqual(self.decide(settings={'completed_blocks':{block_key(self.block):{'reason':'reserve'}},'bias_verified':True,'bias_enabled':True})['mode'],'bias')
 def test_invalid_or_stale_price_does_not_sell_large(self):
  for price in (None,{'start':0,'end':100,'net':5},{'start':0,'end':900,'net':0}):self.assertNotEqual(self.decide(price=price)['mode'],'battery')
 def test_completed_selection_stays_done_until_tomorrow(self):
  self.assertTrue(completed_selection(self.block,'2026-11-06',600))
  self.assertFalse(completed_selection(self.block,'2026-11-07',600))
 def test_house_profile_read_only_exact_floor(self):
  r={0:5,98:1,111:1,130:0,142:2,145:0,146:255,**{166+i:30 for i in range(6)},**{154+i:12000 for i in range(6)},**{172+i:0 for i in range(6)}}
  self.assertTrue(home_profile(r,30)['ok']);r[168]=100
  d=home_profile(r,30);self.assertFalse(d['ok']);self.assertEqual(d['mismatches'][0]['expected'],30);self.assertEqual(d['mismatches'][0]['actual'],100)

 def test_block_identity_keeps_exact_deadline(self):
  block={'day':'2026-11-06','start':1793960000,'end':1793960600}
  self.assertNotEqual(block_key(block),block_key({**block,'end':1793960900}))
 def test_normal_bias_starts_without_historical_probe_but_keeps_proof_false(self):
  settings={'bias_enabled':True,'bias_verified':False}
  self.assertEqual(self.decide(now=600,soc=60,settings=settings)['mode'],'bias')
  self.assertFalse(settings['bias_verified'])

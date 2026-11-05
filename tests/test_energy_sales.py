"""Breaks caught: stale prices, selling protected energy, fabricated PV, lost audit."""
import importlib.util
import pathlib
import tempfile
import unittest
import sys

ROOT=pathlib.Path('managed_sources/spot_control')
sys.path.insert(0,str(ROOT))
try:
 import sales
 from journal import Journal
except ImportError:
 sales=None
 Journal=None

class PriceTests(unittest.TestCase):
 def setUp(self):
  self.assertIsNotNone(sales,'sales policy is not implemented')
  self.rows=[{'time':'2026-11-05T12:00:00+01:00','eur_mwh':240,'price':6}]
  self.t=1793876700 # 2026-11-05 11:05 UTC
 def test_contract_conversion_and_fee(self):
  r=sales.price_at(self.rows,self.t,25)
  self.assertAlmostEqual(r['net'],5.7)
  self.assertEqual(r['end']-r['start'],900)
 def test_old_interval_never_carried_forward(self):
  self.assertIsNone(sales.price_at(self.rows,self.t+900,25))
 def test_invalid_duplicate_or_missing_price_rejected(self):
  for rows in ([],self.rows*2,[dict(self.rows[0],eur_mwh='nan')]):
   self.assertIsNone(sales.price_at(rows,self.t,25))
 def test_negative_net_blocks(self):
  p=sales.price_at([dict(self.rows[0],eur_mwh=5)],self.t,25)
  self.assertAlmostEqual(p['net'],-.175)
  self.assertEqual(sales.decide(99,p,[],self.t)['mode'],'hold')
 def test_spring_and_autumn_offsets_are_distinct(self):
  rows=[{'time':'2026-10-25T02:00:00+02:00','eur_mwh':200},
        {'time':'2026-10-25T02:00:00+01:00','eur_mwh':300}]
  from datetime import datetime
  t=datetime.fromisoformat('2026-10-25T02:05:00+01:00').timestamp()
  self.assertEqual(sales.price_at(rows,t,25)['net'],7.2)

class PolicyTests(unittest.TestCase):
 def setUp(self):self.assertIsNotNone(sales,'sales policy is not implemented')
 def test_full_battery_probes_curtailed_solar_without_claiming_six_kw(self):
  result=sales.decide(99,{'net':2,'start':0,'end':900},[],5)
  self.assertEqual(result['mode'],'pv')
  self.assertEqual(result['power_w'],9300)
  self.assertIsNone(result.get('available_pv_w'))
 def test_battery_not_sold_at_low_price_even_with_full_soc(self):
  self.assertEqual(sales.decide(90,{'net':4.7,'start':0,'end':900},[],5)['mode'],'hold')
 def test_battery_waits_for_more_expensive_slot(self):
  future=[{'start':900,'end':1800,'net':9}]
  self.assertEqual(sales.decide(90,{'net':7,'start':0,'end':900},future,5)['mode'],'hold')
 def test_expensive_slot_sells_only_above_reserve(self):
  p={'net':8,'start':0,'end':900}
  self.assertEqual(sales.decide(60,p,[],5)['mode'],'hold')
  r=sales.decide(80,p,[],5)
  self.assertEqual(r['mode'],'battery')
  self.assertLessEqual(r['power_w'],9300)
  self.assertGreater(r['minimum_soc'],60)
 def test_house_forecast_increases_reserve(self):
  r=sales.decide(80,{'net':8,'start':0,'end':900},[],5,required_soc=85)
  self.assertEqual(r['mode'],'hold')
 def test_manual_stop_cannot_promote_or_restart_automatic(self):
  result=sales.after_stop({'automatic':False,'commission_cancelled':True},{'id':'a','reason':'manual','purpose':'commission','observed':True,'stop_verified':True,'sustained':True,'promote_auto':True})
  self.assertFalse(result['automatic']);self.assertFalse(result.get('pv_verified',False))
 def test_guard_abort_latches_automatic_off_even_after_export(self):
  result=sales.after_stop({'automatic':True},{'id':'b','reason':'guard','observed':True,'stop_verified':True})
  self.assertFalse(result['automatic']);self.assertTrue(result['inhibited'])
 def test_commission_pass_requires_normal_end_sustained_export_and_stop(self):
  proof={'id':'c','reason':'deadline','purpose':'commission','observed':True,'stop_verified':True,'sustained':True,'promote_auto':True,'mode':'pv'}
  self.assertTrue(sales.after_stop({},proof)['pv_verified'])
  for key in ('observed','stop_verified','sustained'):
   self.assertFalse(sales.after_stop({},dict(proof,**{key:False})).get('pv_verified',False))

class JournalTests(unittest.TestCase):
 def setUp(self):self.assertIsNotNone(Journal,'durable journal is not implemented')
 def test_history_survives_reopen_and_keeps_unavailable_values(self):
  with tempfile.TemporaryDirectory() as root:
   path=pathlib.Path(root)/'history.sqlite'
   q=Journal(path); q.append('intent',{'entity':'switch.inverter_export_surplus','before':'off','value':'on'},t=100)
   q.append('sample',{'battery_current':None},t=101)
   result=Journal(path).recent(10)
   self.assertEqual([x['kind'] for x in result],['intent','sample'])
   self.assertIsNone(result[1]['payload']['battery_current'])
 def test_nonfinite_payload_rejected_without_damaging_history(self):
  with tempfile.TemporaryDirectory() as root:
   q=Journal(pathlib.Path(root)/'history.sqlite');q.append('ok',{},t=100)
   with self.assertRaises(ValueError):q.append('bad',{'power':float('nan')},t=101)
   self.assertEqual(len(q.recent(10)),1)
 def test_archive_replay_reads_only_unqueued_events_in_order(self):
  with tempfile.TemporaryDirectory() as root:
   q=Journal(pathlib.Path(root)/'history.sqlite')
   a=q.append('a',{},t=100);q.append('b',{},t=101);q.append('c',{},t=102)
   self.assertEqual([x['kind'] for x in q.after(a,1)],['b'])
   self.assertEqual([x['kind'] for x in q.after(a,100)],['b','c'])

class AutomaticPauseTests(unittest.TestCase):
 def test_owner_conflict_never_promotes_or_restarts_after_normal_deadline(self):
  proof={'id':'owner','reason':'deadline','purpose':'commission','mode':'pv','observed':True,'stop_verified':True,'sustained':True,'promote_auto':True,'conflicts':{'soc':{'actual':45}}}
  result=sales.after_stop({'automatic':True},proof)
  self.assertFalse(result['automatic']);self.assertTrue(result['inhibited'])
  self.assertFalse(result.get('pv_verified',False))

 def test_no_surplus_pauses_for_five_minutes_without_disabling_automatic(self):
  from unittest.mock import patch
  with patch.object(sales.time,'time',return_value=1000):
   result=sales.after_stop({'automatic':True},{'id':'cloud','reason':'no_surplus','mode':'pv','stop_verified':True})
  self.assertTrue(result['automatic']);self.assertFalse(result.get('inhibited',False))
  self.assertEqual(result['cooldown_until'],1300)
 def test_unverified_no_surplus_and_owner_override_cannot_keep_automatic_enabled(self):
  for reason in ('no_surplus','external_override'):
   result=sales.after_stop({'automatic':True},{'id':'blocked','reason':reason,'mode':'pv','stop_verified':False})
   self.assertFalse(result['automatic']);self.assertTrue(result['inhibited'])

 def test_market_and_reserve_pause_do_not_disable_the_owners_automatic_mode(self):
  for reason in ('price','reserve','recovery'):
   result=sales.after_stop({'automatic':True},{'id':'pause','reason':reason,'purpose':'automatic','stop_verified':True})
   self.assertTrue(result['automatic'])
 def test_manual_transaction_recovery_still_stays_inhibited(self):
  result=sales.after_stop({'automatic':True},{'id':'manual','reason':'recovery','purpose':'manual','stop_verified':True})
  self.assertFalse(result['automatic']);self.assertTrue(result['inhibited'])

if __name__=='__main__':unittest.main()

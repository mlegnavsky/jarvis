from datetime import datetime
from zoneinfo import ZoneInfo
import unittest
from daily_override import today_override

class OverrideTests(unittest.TestCase):
 def setUp(self):
  self.tz=ZoneInfo('Europe/Prague')
  self.now=datetime(2026,11,6,17,46,tzinfo=self.tz).timestamp()
  first=datetime(2026,11,6,15,45,tzinfo=self.tz).timestamp()
  self.rows=[{'start':first+i*900,'end':first+(i+1)*900,'net':7} for i in range(16)]
  self.config={'date':'2026-11-06','start':'15:45','end':'18:30'}
 def test_today_only_override_preserves_start_and_exact_end(self):
  block=today_override(self.config,self.rows,self.now)
  self.assertEqual(datetime.fromtimestamp(block['end'],self.tz).strftime('%H:%M'),'18:30')
  self.assertEqual(datetime.fromtimestamp(block['start'],self.tz).strftime('%H:%M'),'15:45')
  self.assertTrue(block['one_day_override'])
 def test_override_keeps_completed_day_closed_and_is_inert_next_day(self):
  self.assertIsNone(today_override(self.config,self.rows,self.now+86400))
  block=today_override(self.config,self.rows,datetime(2026,11,6,18,30,tzinfo=self.tz).timestamp())
  self.assertTrue(block['expired']);self.assertTrue(block['one_day_override'])
 def test_price_after_the_requested_end_does_not_block_today(self):
  end=datetime(2026,11,6,18,30,tzinfo=self.tz).timestamp()
  rows=[r for r in self.rows if r['start']<end]
  self.assertEqual(today_override(self.config,rows,self.now)['end'],end)
 def test_missing_or_negative_future_prices_reject_extension(self):
  for rows in (self.rows[:8],[{**r,'net':-1} for r in self.rows]):
   with self.assertRaises(ValueError):today_override(self.config,rows,self.now)
 def test_unknown_fields_bad_time_and_reversed_window_are_rejected(self):
  for config in ({**self.config,'end':'25:00'},{**self.config,'start':'19:00'},{**self.config,'unsafe':True}):
   with self.assertRaises(ValueError):today_override(config,self.rows,self.now)

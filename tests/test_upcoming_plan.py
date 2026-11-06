import unittest
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
try:
 from upcoming_plan import build_next_plan,valid_prepared_block
except ImportError:
 build_next_plan=valid_prepared_block=None
TZ=ZoneInfo('Europe/Prague')
def stamp(day):return datetime.fromisoformat(day).replace(tzinfo=TZ).timestamp()
def rows(day):
 start=stamp(day);end=(datetime.fromisoformat(day)+timedelta(days=1)).replace(tzinfo=TZ).timestamp()
 return [dict(start=t,end=t+900,net=1) for t in range(int(start),int(end),900)]
class UpcomingTests(unittest.TestCase):
 def test_best_complete_tomorrow_net_window_is_ready(self):
  self.assertIsNotNone(build_next_plan)
  data=rows('2026-11-07')
  for r in data[64:72]:r['net']=9
  p=build_next_plan(data,stamp('2026-11-06')+18*3600,120)
  self.assertEqual(p['status'],'ready');self.assertEqual(p['block']['start'],stamp('2026-11-07')+16*3600)
  self.assertEqual(p['block']['average_net'],9)
 def test_partial_duplicate_invalid_and_empty_day_cannot_claim_best(self):
  self.assertIsNotNone(build_next_plan)
  day=rows('2026-11-07')
  for data in ([],day[:-1],day+[day[0]],day[:-1]+[dict(day[-1],net=None)]):
   self.assertEqual(build_next_plan(data,stamp('2026-11-06'),120)['status'],'waiting_prices')
 def test_complete_negative_day_has_no_sellable_window(self):
  data=[dict(r,net=-1) for r in rows('2026-11-07')]
  self.assertIsNotNone(build_next_plan)
  self.assertEqual(build_next_plan(data,stamp('2026-11-06'),120)['status'],'no_window')
 def test_dst_day_requires_its_real_quarter_count(self):
  self.assertIsNotNone(build_next_plan)
  for previous,day,count in [('2026-03-28','2026-03-29',92),('2026-10-24','2026-10-25',100)]:
   data=rows(day);self.assertEqual(len(data),count)
   self.assertEqual(build_next_plan(data,stamp(previous),120)['status'],'ready')
 def test_midnight_promotion_revalidates_price_and_never_revives_expired_plan(self):
  self.assertIsNotNone(build_next_plan)
  data=rows('2026-11-07');p=build_next_plan(data,stamp('2026-11-06'),120)['block']
  self.assertTrue(valid_prepared_block(p,data,stamp('2026-11-07')+5,120))
  self.assertFalse(valid_prepared_block(p,data,stamp('2026-11-06'),120))
  self.assertFalse(valid_prepared_block(p,data,p['end'],120))
  changed=[dict(r,net=2) for r in data]
  self.assertFalse(valid_prepared_block(p,changed,stamp('2026-11-07'),120))

 def test_prepared_window_rejected_when_other_prices_make_a_better_window(self):
  data=rows('2026-11-07');p=build_next_plan(data,stamp('2026-11-06'),120)['block']
  for r in data[64:72]:r['net']=9
  self.assertFalse(valid_prepared_block(p,data,stamp('2026-11-07')+5,120))

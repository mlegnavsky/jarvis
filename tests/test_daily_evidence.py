import tempfile
import unittest
from datetime import datetime,timezone
from pathlib import Path
from types import SimpleNamespace
from journal import Journal

class EvidenceTests(unittest.TestCase):
 def test_periodic_evidence_is_not_duplicated_after_restart(self):
  with tempfile.TemporaryDirectory() as d:
   path=Path(d)/'journal.sqlite';j=Journal(path)
   first=j.append_periodic('energy_daily_snapshot',{'date':'2026-11-07'},1000)
   self.assertIsNotNone(first)
   self.assertIsNone(Journal(path).append_periodic('energy_daily_snapshot',{},1001))
   self.assertIsNotNone(j.append_periodic('energy_daily_snapshot',{},1300))
   self.assertEqual(len(j.recent_kind('energy_daily_snapshot',20)),2)
 def test_daily_snapshot_preserves_unknowns_and_counter_source_ages(self):
  from daily_evidence import daily_snapshot
  now=datetime(2026,11,7,8,tzinfo=timezone.utc).timestamp()
  states={'sensor.inverter_today_production':SimpleNamespace(state='2.5',last_reported=datetime.fromtimestamp(now,timezone.utc),last_changed=datetime.fromtimestamp(now,timezone.utc)),
          'sensor.inverter_today_load_consumption':SimpleNamespace(state='99',last_reported=datetime.fromtimestamp(now-601,timezone.utc))}
  out=daily_snapshot(states.get,{},None,now)
  self.assertEqual(out['date'],'2026-11-07')
  self.assertEqual(out['energy_kwh']['production'],2.5)
  self.assertIsNone(out['energy_kwh']['house'])
  self.assertIsNone(out['finance'])
  self.assertEqual(out['quality'],'partial')
 def test_finance_from_another_day_is_not_copied_into_today(self):
  from daily_evidence import daily_snapshot
  out=daily_snapshot(lambda _:None,{}, {'date':'2026-11-06','as_of':1,'known_sale_czk':50},1794038400)
  self.assertIsNone(out['finance'])
 def test_history_date_bounds_are_dst_aware_and_invalid_dates_fail(self):
  from daily_evidence import date_bounds
  a,b=date_bounds('2026-10-25');self.assertEqual(b-a,25*3600)
  for value in ('2026-11-31','2026-1-1','2026-11-07T00:00','../'):
   with self.assertRaises(ValueError):date_bounds(value)

 def test_delayed_midnight_reset_does_not_record_yesterdays_counter(self):
  from daily_evidence import daily_snapshot,date_bounds
  start,_=date_bounds('2026-11-07');now=start+300
  state=SimpleNamespace(state='25',last_reported=datetime.fromtimestamp(now,timezone.utc),last_changed=datetime.fromtimestamp(start-100,timezone.utc))
  out=daily_snapshot(lambda _:state,{},None,now)
  self.assertIsNone(out['energy_kwh']['production'])

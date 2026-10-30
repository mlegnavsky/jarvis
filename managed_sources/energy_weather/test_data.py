import unittest
from data import parse_ote, ote_url
class DataTests(unittest.TestCase):
 def test_delivery_date_query(self):
  from urllib.parse import urlparse,parse_qs
  q=parse_qs(urlparse(ote_url('2026-10-31')).query)
  self.assertEqual(q['report_date'],['2026-10-31']);self.assertNotIn('date',q)
 def test_negative_and_dst(self):
  for day,n in [('2026-10-25',100),('2026-03-29',92),('2026-10-27',96)]:
   raw={'graph':{'title':'Výsledky denního trhu - '+'.'.join(reversed(day.split('-')))},'data':{'dataLine':[{'title':'15min cena (EUR/MWh)','point':[{'x':str(i+1),'y':-10+i} for i in range(n)]}]}}
   rows=parse_ote(raw,day,25)
   self.assertEqual(len(rows),n)
   self.assertEqual(rows[0]['price'],-.25)
   self.assertEqual(len(set(x['time'] for x in rows)),n)
 def test_reject_wrong_delivery_date(self):
  with self.assertRaises(ValueError): parse_ote({'graph':{'title':'Výsledky denního trhu - 27.10.2026'}},'2026-10-28',25)
if __name__=='__main__': unittest.main()

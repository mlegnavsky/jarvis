import unittest
from app.policy import APIError

class EnergyFinanceReadTests(unittest.IsolatedAsyncioTestCase):
 async def test_reads_exact_closed_day_without_returning_credentials_or_other_days(self):
  from app.energy_finance import read
  class Supervisor:
   calls=[]
   async def request(self,method,path):
    self.calls.append((method,path))
    return {'state':'ready','last_updated':'2026-11-15T12:00:00Z','attributes':{'password':'DO-NOT-EXPOSE-ME','server':{'finance':{'schema':2,'captured_at':1794744000,'days':[{'date':'2026-11-14','export_kwh':6.2,'known_sale_czk':21.7,'sale_czk':21.7,'quality':'estimate','token':'DO-NOT-EXPOSE-ME'},{'date':'2026-11-13','sale_czk':3}]}}}}
  sup=Supervisor();out=await read(sup,'2026-11-14');self.assertEqual(out['day']['export_kwh'],6.2);self.assertEqual(out['day']['sale_czk'],21.7);self.assertNotIn('DO-NOT-EXPOSE-ME',str(out));self.assertEqual(sup.calls,[('GET','/core/api/states/sensor.jarvis_energy_archive')])
 async def test_invalid_date_never_reaches_upstream(self):
  from app.energy_finance import read
  for target in ['../secrets','2026-02-30','2026-11-14?token=x','2026-1-1','']:
   with self.assertRaises(APIError):await read(None,target)
 async def test_missing_ledger_never_reports_zero_revenue(self):
  from app.energy_finance import read
  class Supervisor:
   async def request(self,*_):return {'state':'ready','attributes':{'server':{}}}
  out=await read(Supervisor(),'2026-11-14');self.assertIsNone(out['day']);self.assertEqual(out['status'],'not_available')

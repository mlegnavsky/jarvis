import copy
import sys
import unittest
from jinja2 import Environment
sys.path.insert(0,'managed_sources/spot_control')
from finance_view import money_card,upgrade_dashboard

class FinanceViewTests(unittest.TestCase):
 def test_daily_money_replaces_both_home_layouts_and_both_energy_layouts(self):
  picture={'type':'picture-elements','image':'house.png','elements':[{'icon':'home'}]}
  flow=lambda text:{'type':'markdown','content':text}
  money=lambda:{'type':'horizontal-stack','cards':[flow('### Náklady na odběr'),flow('### Výnos z prodeje'),flow('Prodej: spot čeká na nastavení')]}
  base={'views':[{'path':'domov','cards':[picture,flow('Síť → dům'),flow('<details>Podrobnosti · Síť → dům')]},{'path':'energie','cards':[money(),money()]}]}
  before=copy.deepcopy(base);out,count=upgrade_dashboard(base)
  self.assertEqual(base,before);self.assertEqual(out['views'][0]['cards'][0],picture)
  self.assertEqual(count,{'home':2,'purchase':2,'sale':2,'price_note':2})
  self.assertIn('sensor.jarvis_dnes_prodano_za',str(out))
  self.assertNotIn('spot čeká na nastavení',str(out))
 def test_currency_is_rendered_in_czech_with_cents(self):
  env=Environment();template=env.from_string(money_card('purchase')['content'])
  rendered=template.render(states=lambda _:24.5123,is_number=lambda v:True)
  self.assertIn('24,51 Kč',rendered)

if __name__=='__main__':unittest.main()

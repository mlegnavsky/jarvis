import unittest,importlib.util
from pathlib import Path
spec=importlib.util.spec_from_file_location('catalogue',Path(__file__).with_name('catalogue.py'))
class CatalogueTest(unittest.TestCase):
 def test_complete_unique_read_only_catalogue(self):
  self.assertTrue(Path(__file__).with_name('catalogue.py').exists(),'catalogue builder missing')
  m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
  import json
  states=json.loads(Path(__file__).with_name('entities.json').read_text())
  entries=m.catalogue(states)
  self.assertEqual({x['id'] for x in entries},{x['entity_id'] for x in states})
  self.assertEqual(len(entries),len(states))
  self.assertEqual(sum(x['writable'] for x in entries),103)
  self.assertTrue(all(x['label'] and '_' not in x['label'] for x in entries))
  for x in entries:
   if x['id'].startswith(('sensor.','binary_sensor.')):self.assertFalse(x['writable'])
 def test_unknown_geometry_cannot_claim_curtailment(self):
  p=Path(__file__).with_name('potential.jinja')
  self.assertTrue(p.exists(),'potential estimator missing')
  import jinja2
  env=jinja2.Environment();t=env.from_string(p.read_text())
  out=t.render(states=lambda e:'500',state_attr=lambda e,a:None,as_timestamp=lambda v,d=0:d,now=lambda:None)
  self.assertIn('Chybí sklon a orientace',out)
  self.assertNotIn('Nevyužitý výkon: 0',out)
 def test_all_templates_render_and_settings_are_text_only(self):
  import json,jinja2
  m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
  entries=m.catalogue(json.loads(Path(__file__).with_name('entities.json').read_text()))
  c=m.card(entries,'Katalog')
  env=jinja2.Environment();t=env.from_string(c['content'])
  rendered=t.render(states=lambda e:'unavailable' if e=='switch.inverter_access_point' else '100',state_attr=lambda e,a:None)
  self.assertEqual(rendered.count('můžeme změnit'),102)
  self.assertIn('nyní nelze měnit',rendered)
  self.assertNotIn('call-service',str(c))
  self.assertNotIn('perform-action',str(c))
if __name__=='__main__':unittest.main()

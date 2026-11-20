from pathlib import Path
import unittest,yaml

class SpotClientVersionTests(unittest.TestCase):
 def test_replaces_iframe_and_every_changed_script_with_new_paths(self):
  from scripts.version_spot_client import prepare
  root="title: Domov\nviews:\n- !include 'spot-control-view.yaml'\n"
  view='title: Spoty\npath: spoty\ntype: panel\ncards:\n- type: iframe\n  url: /local/jarvis-spot-hub.html?v=1.3.4\n  aspect_ratio: 85%\n'
  files=prepare(root,view);page=files['www/jarvis-spot-hub-finance-20261115b.html']
  self.assertIn('/local/jarvis-accounting-finance-20261115b.js',page)
  self.assertIn('/local/jarvis-spot-hub-finance-20261115b.js',page)
  self.assertNotIn('jarvis-spot-hub.js?',page)
  config=yaml.safe_load(files['jarvis_workspace/spot-control-view.yaml'])
  self.assertEqual(config['cards'][0]['url'],'/local/jarvis-spot-hub-finance-20261115b.html')
  self.assertEqual(config['cards'][0]['aspect_ratio'],'85%')
  self.assertTrue(files['jarvis_workspace/hlavni-prehled.yaml'].startswith(root))
  self.assertEqual(files['www/jarvis-accounting-finance-20261115b.js'],Path('managed_sources/spot_hub/accounting.js').read_text())

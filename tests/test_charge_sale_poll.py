"""Reproduce the sales poll overlapping standalone charging, using its real gate."""
import ast
from pathlib import Path
from types import SimpleNamespace
from test_spot_control import Tests

class ChargeSalePollTests(Tests):
 def gate(self,c,busy):
  tree=ast.parse(Path('managed_sources/spot_control/__init__.py').read_text())
  setup=next(n for n in tree.body if isinstance(n,ast.AsyncFunctionDef) and n.name=='async_setup')
  permitted=next(n for n in setup.body if isinstance(n,ast.FunctionDef) and n.name=='permitted')
  self.sales={'busy':lambda:busy[0]}
  scope={'hass':SimpleNamespace(data={'jarvis_spot_control_sales':self.sales}),'DOMAIN':'jarvis_spot_control','c':c}
  exec(compile(ast.Module(body=[permitted],type_ignores=[]),'<real permitted>','exec'),scope)
  return scope['permitted']
 async def test_poll_lock_does_not_abort_own_standalone_start(self):
  c=self.controller();busy=[False];gate=self.gate(c,busy);c.healthy=gate
  original=c.write
  async def write(e,v):
   await original(e,v);busy[0]=True
  c.write=write
  await c.start(960)
  self.assertEqual(c.record['phase'],'running')
  await c.tick(gate());self.assertTrue(c.active)
  await c.stop();self.assertEqual(self.s,self.before)
 def test_unowned_start_and_actual_sale_still_blocked(self):
  c=self.controller();busy=[True];gate=self.gate(c,busy)
  self.assertFalse(gate())
  c.record={'before':{'x':'old'},'phase':'running'}
  self.sales['controller']=SimpleNamespace(active=True)
  self.assertFalse(gate())
  self.sales['controller'].active=False;self.sales['clock_sync_active']=True
  self.assertFalse(gate())

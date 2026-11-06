import importlib,sys,types,unittest
import test_battery_native as fixtures
from pathlib import Path
class ProductionBoundaryTests(unittest.IsolatedAsyncioTestCase):
 asyncSetUp=fixtures.BatteryNativeTests.asyncSetUp
 make_controller=fixtures.BatteryNativeTests.make_controller
 async def test_manual_and_automatic_export_never_program_house_or_current(self):
  name='production_boundary_fixture';pkg=types.ModuleType(name);pkg.__path__=[str(Path('managed_sources/spot_control').resolve())];sys.modules[name]=pkg
  C=importlib.import_module(name+'.production_controller').ProductionBatteryController
  for purpose in ('manual','automatic'):
   self.reg=dict(self.original);self.writes=[];self.states.update(grid_w=20,battery_w=0,reported_at=self.now)
   c=C(self.read,self.write,lambda:dict(self.states),self.save,self.event,clock=lambda:self.now)
   await c.start(500,5,60,self.quotes,purpose=purpose)
   self.assertEqual([a for a,v in self.writes],[143]);self.assertTrue(c.record['ha_controlled'])
   for address in (109,146,*range(148,160),*range(166,178)):self.assertEqual(self.reg[address],self.original[address])
   self.now+=1;self.states['reported_at']=self.now;await c.tick()
   self.assertTrue(all(a in (142,143,145) for a,v in self.writes))
 async def test_production_rejects_new_native_commission(self):
  name='production_boundary_fixture2';pkg=types.ModuleType(name);pkg.__path__=[str(Path('managed_sources/spot_control').resolve())];sys.modules[name]=pkg
  C=importlib.import_module(name+'.production_controller').ProductionBatteryController
  c=C(self.read,self.write,lambda:dict(self.states),self.save,self.event,clock=lambda:self.now)
  with self.assertRaises(ValueError):await c.start(500,5,90,self.quotes,purpose='commission')
  self.assertFalse(self.writes)

"""HA dispatches unmarked sync event listeners in the executor.

Exercise real platform listeners through that dispatcher; writes must occur
on the event loop, as required by Home Assistant's state API.
"""
import asyncio
import importlib.util
import pathlib
import sys
import types
import unittest
from unittest.mock import patch

class Entity:
 def async_on_remove(self,remove):pass
 def async_write_ha_state(self):
  asyncio.get_running_loop()
  self.updated=True

def callback(fn):
 fn._hass_callback=True
 return fn

class EntityEvents(unittest.IsolatedAsyncioTestCase):
 async def test_settings_event_updates_every_native_control_on_the_event_loop(self):
  handlers=[];key='jarvis_spot_control_sales'
  modules={}
  for name in ['homeassistant','homeassistant.core','homeassistant.components','homeassistant.components.number','homeassistant.components.select','homeassistant.components.switch']:
   modules[name]=types.ModuleType(name)
  modules['homeassistant.core'].callback=callback
  for platform,cls in [('number','NumberEntity'),('select','SelectEntity'),('switch','SwitchEntity')]:setattr(modules['homeassistant.components.'+platform],cls,Entity)
  modules['homeassistant.components.number'].NumberMode=types.SimpleNamespace(BOX='box')
  pkg=types.ModuleType('sale_entity_test');pkg.__path__=[str(pathlib.Path('managed_sources/spot_control').resolve())];modules[pkg.__name__]=pkg
  setup=types.ModuleType(pkg.__name__+'.sale_setup');setup.KEY=key;modules[setup.__name__]=setup
  hass=types.SimpleNamespace(data={key:{'settings':{'automatic':False}}},bus=types.SimpleNamespace(async_listen=lambda name,handler:handlers.append(handler)))
  controls=[]
  with patch.dict(sys.modules,modules):
   for platform in ('number','select','switch'):
    spec=importlib.util.spec_from_file_location(pkg.__name__+'.'+platform,pathlib.Path('managed_sources/spot_control')/(platform+'.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    await module.async_setup_platform(hass,{},controls.extend)
   for control in controls:
    control.hass=hass;await control.async_added_to_hass()
   for handler in handlers:
    if getattr(handler,'_hass_callback',False):handler(None)
    else:await asyncio.to_thread(handler,None)
  self.assertEqual(len(controls),4)
  self.assertTrue(all(control.updated for control in controls))

if __name__=='__main__':unittest.main()

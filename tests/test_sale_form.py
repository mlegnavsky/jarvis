"""Battery source selection must not leave the PV-only three-minute default."""
import asyncio
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

class Entity:
 @property
 def options(self):return self._attr_options
 @property
 def native_max_value(self):return self._attr_native_max_value
 def async_write_ha_state(self):pass

class SaleFormTests(unittest.IsolatedAsyncioTestCase):
 async def test_battery_selection_raises_default_and_enforces_its_native_minimum(self):
  package=types.ModuleType('sale_form_test');package.__path__=[str(Path('managed_sources/spot_control').resolve())]
  modules={'sale_form_test':package,'sale_form_test.sale_setup':types.SimpleNamespace(KEY='sales'),
   'homeassistant.core':types.SimpleNamespace(callback=lambda fn:fn),
   'homeassistant.components.select':types.SimpleNamespace(SelectEntity=Entity),
   'homeassistant.components.number':types.SimpleNamespace(NumberEntity=Entity,NumberMode=types.SimpleNamespace(BOX='box'))}
  settings={'source':'pv','minutes':3,'power_w':500}
  async def configure(changes):settings.update(changes)
  async def report():pass
  hass=types.SimpleNamespace(data={'sales':{'settings':settings,'configure':configure,'report':report}})
  with patch.dict(sys.modules,modules):
   loaded={}
   for name in ('select','number'):
    spec=importlib.util.spec_from_file_location('sale_form_test.'+name,Path('managed_sources/spot_control')/(name+'.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);loaded[name]=module
   source=loaded['select'].SaleSource(hass)
   minutes=loaded['number'].SaleNumber(hass,'minutes','Délka',1,60,1,'min')
   self.assertEqual(minutes.native_min_value,1)
   await source.async_select_option('Baterie nad rezervou')
   self.assertEqual(settings['minutes'],5);self.assertEqual(minutes.native_min_value,5)
   with self.assertRaises(ValueError):await minutes.async_set_native_value(3)
   await minutes.async_set_native_value(8);self.assertEqual(settings['minutes'],8)
   await source.async_select_option('Přebytky panelů')
   self.assertEqual(minutes.native_min_value,1)
   await minutes.async_set_native_value(3);self.assertEqual(settings['minutes'],3)

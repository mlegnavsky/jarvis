import asyncio
import importlib.util
from pathlib import Path
from types import SimpleNamespace as NS
import unittest

PATH=Path(__file__).with_name('room_commands.py')
if PATH.exists():
 spec=importlib.util.spec_from_file_location('room_commands',PATH)
 commands=importlib.util.module_from_spec(spec);spec.loader.exec_module(commands)
else:
 commands=NS(resolve=lambda *a,**kw:None)

AREAS=[{'id':'living','name':'Obývák','aliases':[]},
       {'id':'bath','name':'Koupelna + WC','aliases':['koupelna','záchod','toaleta']},
       {'id':'hall','name':'Vstupní chodba','aliases':['chodbička']}]
LIGHTS=[{'entity_id':'light.living','area_id':'living','state':'off'},
        {'entity_id':'light.bath','area_id':'bath','state':'off'},
        {'entity_id':'light.hall','area_id':'hall','state':'off'},
        {'entity_id':'switch.heater','area_id':'living','state':'off'}]
class CommandTests(unittest.TestCase):
 def resolve(self,text,source='living',lights=None,areas=None):
  return commands.resolve(text,source,AREAS if areas is None else areas,LIGHTS if lights is None else lights)
 def test_bare_commands_use_source_room(self):
  for text,service in [('Rozsviť','turn_on'),('rozsviť to','turn_on'),('Zhasni světla.','turn_off'),('zhasni to','turn_off')]:
   with self.subTest(text=text):
    value=self.resolve(text);self.assertIsNotNone(value)
    self.assertEqual(value['service'],service);self.assertEqual(value['entity_ids'],['light.living'])
 def test_explicit_inflected_room_overrides_source(self):
  for text,entity in [('rozsviť v koupelně','light.bath'),('zhasni v chodbičce','light.hall'),('rozsvit svetla v obyvaku','light.living')]:
   value=self.resolve(text);self.assertIsNotNone(value);self.assertEqual(value['entity_ids'],[entity])
 def test_missing_source_never_selects_whole_house(self):
  value=self.resolve('Rozsviť',None);self.assertIsNotNone(value);self.assertEqual(value['error'],'source_room_missing');self.assertEqual(value['entity_ids'],[])
 def test_unknown_explicit_room_never_falls_back(self):
  value=self.resolve('Zhasni v garáži');self.assertIsNotNone(value);self.assertEqual(value['error'],'room_not_found');self.assertFalse(value['entity_ids'])
 def test_duplicate_room_names_require_clarification(self):
  value=self.resolve('Rozsviť v koupelně',areas=AREAS+[{'id':'bath2','name':'Koupelna','aliases':[]}]);self.assertIsNotNone(value);self.assertEqual(value['error'],'room_ambiguous')
 def test_only_supplied_exposed_lights_are_targets(self):
  value=self.resolve('Rozsviť',lights=[LIGHTS[-1]]);self.assertIsNotNone(value);self.assertEqual(value['error'],'no_exposed_lights')
 def test_ordinary_conversation_and_complex_requests_are_not_shortcut(self):
  for text in ['Řekl jsem rozsviť.','Nezhasni','Když řeknu zhasni, co uděláš?','Rozsviť na 20 procent','Rozsviť a otevři dveře']:
   self.assertIsNone(self.resolve(text),text)

class AdapterTests(unittest.IsolatedAsyncioTestCase):
 async def test_execution_retains_context_and_reports_unverified_submission(self):
  handler=getattr(commands,'execute',None);self.assertIsNotNone(handler)
  called=[];context=object()
  async def call(domain,service,data,**kw):called.append((domain,service,data,kw))
  hass=NS(services=NS(async_call=call),states=NS(get=lambda entity:NS(state='off')))
  request=self.resolve_request()
  reply=await handler(hass,request,context)
  self.assertEqual(called,[('light','turn_on',{'entity_id':['light.living']},{'blocking':True,'context':context})])
  self.assertIn('odeslala',reply);self.assertNotIn('Rozsvítil',reply)
 def resolve_request(self):return commands.resolve('rozsviť','living',AREAS,LIGHTS)
 async def test_error_never_calls_any_service(self):
  handler=getattr(commands,'execute',None);self.assertIsNotNone(handler)
  async def forbidden(*a,**kw):raise AssertionError('must not call')
  reply=await handler(NS(services=NS(async_call=forbidden)),commands.resolve('rozsviť',None,AREAS,LIGHTS),None)
  self.assertIn('místnost',reply)

class RegistryTests(unittest.IsolatedAsyncioTestCase):
 async def test_registry_area_override_and_source_device(self):
  handler=getattr(commands,'async_handle_room_command',None);self.assertIsNotNone(handler)
  from unittest.mock import patch
  called=[]
  async def call(*args,**kw):called.append(args)
  areas=NS(async_list_areas=lambda:[NS(id=a['id'],name=a['name'],aliases=a['aliases']) for a in AREAS])
  devices={'mic':NS(area_id='living'),'lamp':NS(area_id='bath')}
  entities={'light.moved':NS(area_id='living',device_id='lamp'),'light.other':NS(area_id=None,device_id='lamp')}
  helpers=NS(area_registry=NS(async_get=lambda hass:areas),device_registry=NS(async_get=lambda hass:NS(async_get=devices.get)),entity_registry=NS(async_get=lambda hass:NS(async_get=entities.get)))
  hass=NS(services=NS(async_call=call),states=NS(get=lambda entity:NS(state='on')))
  user=NS(text='rozsviť',device_id='mic',context=object())
  with patch.dict('sys.modules',{'homeassistant':NS(),'homeassistant.helpers':helpers}):
   await handler(hass,user,[{'entity_id':'light.moved'},{'entity_id':'light.other'}])
  self.assertEqual(called[0][2]['entity_id'],['light.moved'])

class ActualRoomNamesTests(unittest.TestCase):
 def test_chodbicka_resolves_registered_vstupni_chodba(self):
  value=commands.resolve('Zhasni v chodbičce','living',[
   {'id':'hall','name':'Vstupní chodba','aliases':[]}],LIGHTS)
  self.assertEqual(value['entity_ids'],['light.hall'])


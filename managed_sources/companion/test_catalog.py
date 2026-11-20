"""Live device visibility is independent of device action permission."""
import importlib
import json
import unittest


class CatalogTests(unittest.TestCase):
 def module(self):return importlib.import_module('catalog')
 def build(self,states,entities=(),devices=(),areas=(),exposed=()):
  return self.module().build_catalog(states,list(entities),list(devices),list(areas),set(exposed))

 def test_all_states_units_and_unavailable_entities_are_visible(self):
  states=[{'entity_id':'sensor.power_'+str(i),'state':str(i),'attributes':{'friendly_name':'Výkon '+str(i),'unit_of_measurement':'W'}} for i in range(80)]
  states.append({'entity_id':'light.offline','state':'unavailable','attributes':{}})
  data=self.build(states,exposed={'light.offline'})
  self.assertEqual(len(data['entities']),81)
  self.assertEqual(data['summary']['state_count'],81)
  self.assertEqual(data['entities'][0]['exposed'],True)
  power=next(e for e in data['entities'] if e['id']=='sensor.power_79')
  self.assertEqual((power['state'],power['unit'],power['exposed']),('79','W',False))
  self.assertEqual(data['entities'][0]['state'],'unavailable')

 def test_entity_room_overrides_device_and_disabled_has_no_invented_state(self):
  data=self.build([{'entity_id':'light.a','state':'off','attributes':{}}],
   entities=[{'entity_id':'light.a','device_id':'d','area_id':'child','aliases':['Lampička']},
             {'entity_id':'light.disabled','device_id':'d','disabled_by':'user'}],
   devices=[{'id':'d','name':'Vypínač','area_id':'living'}],
   areas=[{'id':'child','name':'Dětský pokoj'},{'id':'living','name':'Obývák'}])
  lamp=next(e for e in data['entities'] if e['id']=='light.a')
  disabled=next(e for e in data['entities'] if e['id']=='light.disabled')
  self.assertEqual(lamp['area'],'child');self.assertEqual(lamp['aliases'],['Lampička'])
  self.assertIsNone(disabled['state']);self.assertTrue(disabled['disabled'])
  self.assertEqual(disabled['area'],'living')

 def test_credentials_urls_private_text_and_unlisted_attributes_never_leave(self):
  data=self.build([{'entity_id':'camera.front','state':'idle','attributes':{'access_token':'PRIVATE','entity_picture':'https://PRIVATE','friendly_name':'Kamera'}},
   {'entity_id':'input_text.note','state':'PRIVATE','attributes':{}},
   {'entity_id':'sensor.api_key','state':'PRIVATE','attributes':{}},
   {'entity_id':'media_player.tv','state':'playing','attributes':{'volume_level':.4,'is_volume_muted':False,'media_content_id':'PRIVATE'}}])
  text=self.module().render_catalog(data)
  self.assertNotIn('PRIVATE',text)
  self.assertIn('volume_level',text);self.assertIn('0.4',text)

 def test_password_text_token_sensors_and_url_options_are_withheld(self):
  data=self.build([{'entity_id':'text.router_login','state':'PRIVATE_PASSWORD','attributes':{'mode':'password'}},
   {'entity_id':'sensor.api_token','state':'PRIVATE_TOKEN','attributes':{}},
   {'entity_id':'select.stream','state':'https://PRIVATE_STATE/stream','attributes':{'options':['https://user:PRIVATE_OPTION@host/stream','Local']}},
   {'entity_id':'sensor.power','state':'12','attributes':{'unit_of_measurement':'W'}}])
  text=self.module().render_catalog(data)
  self.assertNotIn('PRIVATE',text);self.assertNotIn('https://',text)
  self.assertEqual(next(e for e in data['entities'] if e['id']=='sensor.power')['state'],'12')

 def test_native_adapter_resolves_computed_aliases_using_registry_helper(self):
  import sys
  from types import ModuleType,SimpleNamespace as NS
  from unittest.mock import patch
  root=ModuleType('homeassistant');helpers=ModuleType('homeassistant.helpers')
  er=ModuleType('homeassistant.helpers.entity_registry');dr=ModuleType('homeassistant.helpers.device_registry');ar=ModuleType('homeassistant.helpers.area_registry')
  sentinel=object();entry=NS(entity_id='light.a',device_id=None,area_id=None,name=None,
      original_name='Světlo',aliases=[sentinel,'Lampička'],disabled_by=None)
  calls=[]
  er.async_get=lambda hass:NS(entities={'light.a':entry})
  def aliases(hass,value):calls.append(value);return ['Obývák světlo','Lampička']
  er.async_get_entity_aliases=aliases;dr.async_get=lambda hass:NS(devices={})
  ar.async_get=lambda hass:NS(async_list_areas=lambda:[])
  helpers.entity_registry=er;helpers.device_registry=dr;helpers.area_registry=ar;root.helpers=helpers
  modules={m.__name__:m for m in (root,helpers,er,dr,ar)}
  hass=NS(states=NS(async_all=lambda:[NS(entity_id='light.a',state='off',attributes={})]))
  with patch.dict(sys.modules,modules):data=self.module().read_catalog(hass,set())
  self.assertEqual(calls,[entry]);self.assertEqual(data['entities'][0]['aliases'],['Lampička','Obývák světlo'])

 def test_exposed_agent_states_cannot_bypass_private_value_filter(self):
  import ast
  from pathlib import Path
  from datetime import datetime,timezone
  from types import SimpleNamespace as NS
  module=self.module();tree=ast.parse(Path(__file__).with_name('conversation.py').read_text())
  cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='ExtendedOpenAIAgentEntity')
  method=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='get_exposed_entities')
  state=NS(entity_id='text.router_login',state='PRIVATE_PASSWORD',name='Router login',
           attributes={'mode':'password'},last_changed=datetime.now(timezone.utc))
  registry=NS(async_get=lambda entity:NS(aliases=[]))
  scope={'async_should_expose':lambda *a:True,'conversation':NS(DOMAIN='conversation'),
         'er':NS(async_get=lambda hass:registry,async_get_entity_aliases=lambda *a:[]),
         'safe_state':getattr(module,'safe_state',lambda *a:'PRIVATE_PASSWORD'),
         'clipped':module.clipped}
  exec(compile(ast.Module(body=[method],type_ignores=[]),'actual-exposed-getter','exec'),scope)
  hass=NS(states=NS(async_all=lambda:[state],get=lambda entity:state))
  result=scope['get_exposed_entities'](NS(hass=hass))
  self.assertNotIn('PRIVATE',str(result))

 def test_render_and_state_limits_are_explicit(self):
  states=[{'entity_id':'sensor.test_'+str(i),'state':str(i),'attributes':{'friendly_name':'X'*200}} for i in range(2000)]
  data=self.build(states);text=self.module().render_catalog(data)
  self.assertLessEqual(len(text.encode()),64*1024)
  compact=json.loads(text.partition('\n')[2])
  self.assertTrue(compact['truncated']);self.assertEqual(compact['summary']['state_count'],2000)
  self.assertLess(len(compact['entities']),2000)

 def test_budget_preserves_current_volume_before_optional_metadata(self):
  states=[{'entity_id':'sensor.reading_'+str(i),'state':'12','attributes':{'friendly_name':'Měřená hodnota '+str(i),
       'device_class':'temperature','supported_features':123,'options':['metadata'*15]*16}} for i in range(420)]
  states.append({'entity_id':'media_player.tv','state':'playing','attributes':{'volume_level':.4,'is_volume_muted':False}})
  compact=json.loads(self.module().render_catalog(self.build(states)).partition('\n')[2])
  row=next(r for r in compact['entities'] if r[0]=='media_player.tv')
  self.assertEqual(row[9]['volume_level'],.4)
  self.assertEqual(len(compact['entities']),421)

 def test_recent_whole_turns_and_tool_groups_survive_context_pruning(self):
  module=self.module();messages=[{'role':'system','content':'base'},{'role':'system','content':'current catalogue'}]
  for i in range(6):messages.extend([{'role':'user','content':str(i)},
    {'role':'assistant','tool_calls':[{'id':str(i)}]}, {'role':'tool','tool_call_id':str(i),'content':'answer'}])
  module.keep_recent_turns(messages,4)
  self.assertEqual([x['content'] for x in messages if x['role']=='user'],['2','3','4','5'])
  self.assertEqual([x['tool_call_id'] for x in messages if x['role']=='tool'],['2','3','4','5'])
  self.assertEqual(messages[1]['content'],'current catalogue')

 def test_model_byte_budget_removes_complete_old_turns_only(self):
  module=self.module();messages=[{'role':'system','content':'base'},
   {'role':'system','content':'catalogue '+('x'*50000)}]
  for i in range(6):messages.extend([{'role':'user','content':str(i)+'x'*15000},{'role':'assistant','content':'reply'}])
  module.bound_messages(messages)
  self.assertLessEqual(len(json.dumps(messages,ensure_ascii=False).encode()),96*1024)
  self.assertTrue(messages[-2]['content'].startswith('5'))
  self.assertEqual(messages[-1]['content'],'reply')
  with self.assertRaises(ValueError):module.bound_messages([{'role':'system','content':'x'*100000},{'role':'user','content':'latest'}])

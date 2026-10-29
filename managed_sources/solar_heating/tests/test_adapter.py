"""Exercise production HA adapter against a minimal event/service host."""
import ast
import asyncio
from datetime import datetime,timezone
import logging
from pathlib import Path
from types import SimpleNamespace as NS
import time
import unittest
from engine import Controller,ROOMS,numeric

class Context:
 count=0
 def __init__(self):
  Context.count+=1;self.id=str(Context.count)
class Store:
 def __init__(self,*args):self.saved=None
 async def async_load(self):return None
 def async_delay_save(self,fn,delay):self.saved=fn()
 async def async_save(self,data):self.saved=data
class Vol:
 ALLOW_EXTRA=True
 def Optional(self,x):return x
 def Schema(self,x,**kw):return x
 def Required(self,x):return x
 def In(self,x):return x
class AdapterTests(unittest.IsolatedAsyncioTestCase):
 async def asyncSetUp(self):
  source=Path(__file__).parents[1].joinpath('__init__.py').read_text();tree=ast.parse(source)
  constants=[n for n in tree.body if isinstance(n,ast.Assign)]
  fn=next(n for n in tree.body if isinstance(n,ast.AsyncFunctionDef) and n.name=='async_setup')
  g=dict(asyncio=asyncio,datetime=datetime,timezone=timezone,logging=logging,time=time,vol=Vol(),Context=Context,callback=lambda f:f,Store=Store,Controller=Controller,ROOMS=ROOMS,numeric=numeric,EVENT_HOMEASSISTANT_STARTED='start',EVENT_HOMEASSISTANT_STOP='stop')
  self.handlers=[];self.bus={};self.registered={};self.tasks=[];self.states={};self.calls=[]
  def set_state(entity,state,attrs=None,context=None):
   old=self.states.get(entity);ctx=context or Context()
   new=NS(state=state,attributes=attrs or {},last_changed=datetime.now(timezone.utc),context=ctx)
   self.states[entity]=new
   for entities,cb in self.handlers:
    if entity in entities and (not old or old.state!=state):cb(NS(data={'entity_id':entity,'old_state':old,'new_state':new},context=ctx))
  def register(domain,service,fn,**kw):self.registered[(domain,service)]=fn
  async def call(domain,service,data,**kw):
   self.calls.append((domain,service,data))
   if domain=='switch' and not getattr(self,'defer_switch',False):
    for cb in self.bus.get('call_service',[]):cb(NS(data={'domain':domain,'service':service,'service_data':data},context=kw['context']))
    set_state(data['entity_id'],'on' if service=='turn_on' else 'off',context=kw['context'])
  def task(coro):
   t=asyncio.create_task(coro);self.tasks.append(t);return t
  self.set_state=set_state
  self.hass=NS(data={},is_running=True,states=NS(get=self.states.get,async_set=set_state),services=NS(async_register=register,async_call=call),async_create_task=task,
   bus=NS(async_listen=lambda e,cb:self.bus.setdefault(e,[]).append(cb),async_listen_once=lambda e,cb:self.bus.setdefault(e,[]).append(cb)))
  g['async_track_state_change_event']=lambda h,entities,cb:self.handlers.append((entities,cb))
  exec(compile(ast.Module(body=constants+[fn],type_ignores=[]),'<production-adapter>','exec'),g)
  self.g=g
  for k,v in dict(temp=20,pv=4000,soc=70,discharge=0,load=400).items():set_state(g['SENSORS'][k],str(v))
  for entity in g['SWITCHES'].values():set_state(entity,'off')
  set_state(g['AUTOMATION'],'on')
  await g['async_setup'](self.hass,{})
  await self.drain()
 async def drain(self):
  for _ in range(10):
   pending=[t for t in self.tasks if not t.done()]
   if not pending:break
   await asyncio.gather(*pending)
 async def test_auto_switch_context_does_not_enable_manual(self):
  c=self.hass.data['jarvis_solar_heating']['controller']
  self.assertFalse(c.manual['child']);self.assertEqual(self.states['switch.aqara_smart_plug_eu'].state,'on')
  self.assertEqual(self.states['sensor.jarvis_topeni_child'].state,'Ze soláru')
 async def test_physical_off_returns_auto_and_holds_cooldown(self):
  self.set_state('switch.aqara_smart_plug_eu','off');await self.drain()
  self.assertEqual(self.states['sensor.jarvis_topeni_child'].state,'Pauza po vypnutí')
 async def test_manual_on_then_temperature_safety(self):
  self.set_state('switch.aqara_smart_plug_eu_2','on');await self.drain()
  self.assertEqual(self.states['sensor.jarvis_topeni_living'].state,'Ručně')
  self.set_state(self.g['SENSORS']['temp'],'23.5');await self.drain()
  self.assertEqual(self.states['switch.aqara_smart_plug_eu_2'].state,'off')
 async def test_disabling_visible_automation_stops_automatic_heat(self):
  self.set_state(self.g['AUTOMATION'],'off');await self.drain()
  self.assertEqual(self.states['switch.aqara_smart_plug_eu'].state,'off')

 async def test_late_switch_confirmation_clears_previous_error(self):
  self.defer_switch=True
  self.set_state(self.g['SENSORS']['temp'],'23.5');await self.drain()
  self.assertEqual(self.states['sensor.jarvis_topeni_child'].state,'Chyba ovládání')
  self.set_state('switch.aqara_smart_plug_eu','off');await self.drain()
  self.assertEqual(self.states['sensor.jarvis_topeni_child'].state,'Dosaženo 23,5 °C')
  self.assertIsNone(self.states['sensor.jarvis_topeni_child'].attributes['last_error'])

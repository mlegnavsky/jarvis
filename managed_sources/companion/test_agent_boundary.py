"""Execute actual deployed agent methods with isolated HA/API boundary doubles."""
import ast
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace as NS
import time
import asyncio
import unittest
from room_commands import async_handle_room_command,voice_input_allowed
from dialogue import is_stop, is_pause, recent_session, should_continue, is_noise_transcript, local_time_answer
class Speech:
 def __init__(self,**kw):pass
 def async_set_speech(self,text):self.text=text
 def as_dict(self):return {'speech':{'plain':{'speech':getattr(self,'text','')}}}
class MethodTests(unittest.IsolatedAsyncioTestCase):
 async def test_tv_resume_during_prepare_cannot_reach_local_action(self):
  import importlib,sys
  from unittest.mock import patch
  import room_commands
  local=str(Path(__file__).parents[1]/'local_duplex')
  with patch.object(sys,'path',[local,*sys.path]):
   Session=importlib.import_module('session').Session;Bridge=importlib.import_module('bridge').TurnBridge
  calls=[];hass=NS(data={'jarvis_voice_input_guards':{}},bus=NS(async_fire=lambda *a:None))
  class Companion:
   async def prepare(self,*a):
    session.request_close('television_audible');await asyncio.sleep(0)
    return NS(reset_history=False,principal='p',local_reply=None,prompt='memory')
  async def action(*a):calls.append('physical action');return ''
  handler=self.method('_async_handle_message');handler.__globals__['async_handle_room_command']=action
  handler.__globals__['voice_input_allowed']=getattr(room_commands,'voice_input_allowed',lambda h,u:not session.done)
  agent=NS(hass=hass,_companion=Companion(),_history_principals={},history={},get_exposed_entities=lambda:[],
   _recent_devices={},_dialogue_started={},_dialogue_turns={})
  async def transcribe(audio):return 'Zhasni'
  async def complete(*a,**kw):pass
  async def converse(**kw):
   context=kw['context'];hass.data['jarvis_voice_input_guards'][context.id]=lambda:not session.done
   user=NS(text=kw['text'],device_id='mic',satellite_id='sat',language='cs',context=context)
   try:return await handler(agent,user,NS(conversation_id='c'))
   finally:hass.data['jarvis_voice_input_guards'].pop(context.id,None)
  bridge=Bridge(transcribe,complete,converse,context_factory=lambda:NS(id='c'),device_id='mic',
      satellite_id='sat',conversation_id='c',agent_id='a',language='cs')
  async def nothing(*a):pass
  session=Session(transcribe=bridge.transcribe,respond=bridge.respond,play=nothing,stop=nothing)
  await session.submit(bytes(32000),.8,False);await session.task
  self.assertEqual(calls,[]);self.assertEqual(hass.data['jarvis_voice_input_guards'],{})
  await session.close()

 async def test_actual_service_boundary_rechecks_bound_source_guard(self):
  from room_commands import execute
  calls=[]
  async def service(*a,**kw):calls.append(a)
  speaker=NS(enforce=True,device=lambda user:'mic',gate=NS(consume=lambda *a:True))
  hass=NS(data={'jarvis_speaker_identity':speaker,'jarvis_voice_input_guards':{'c':lambda:False}},
      services=NS(async_call=service),states=NS(get=lambda entity:NS(state='off')))
  user=NS(device_id='mic',satellite_id='sat',context=NS(id='c'),text='Zhasni')
  request={'service':'turn_off','entity_ids':['light.test'],'area_id':'living','area_name':'Obývák','error':None}
  await execute(hass,request,user.context,user=user,token='one-use')
  self.assertEqual(calls,[])

 async def test_live_catalogue_refreshes_on_followup_and_is_not_retained(self):
  import copy
  requests=[];current=['10 W']
  class Companion:
   async def prepare(self,*a):return NS(reset_history=False,principal='p',local_reply=None,prompt='memory')
   async def finish(self,turn,text):return text
  async def query(user,messages,entities,n):
   requests.append(copy.deepcopy(messages))
   return NS(message=NS(content='Měřím hodnotu.',model_dump=lambda **kw:{'role':'assistant','content':'Měřím hodnotu.'}),
             response=NS(model_dump=lambda:{}))
  agent=NS(_companion=Companion(),_history_principals={},history={},get_exposed_entities=lambda:[],
   _recent_devices={},_dialogue_started={},_dialogue_turns={},hass=NS(bus=NS(async_fire=lambda *a,**kw:None)),
   options={},subentry=NS(subentry_id='test'),query=query,_generate_system_message=lambda *a:{'role':'system','content':'base'})
  fn=self.method('_async_handle_message')
  fn.__globals__['catalog_context']=lambda hass,entities:'CURRENT_CATALOGUE '+current[0]
  user=NS(text='Kolik vyrábím?',device_id='mic',language='cs',context=NS(user_id=None))
  await fn(agent,user,NS(conversation_id='c'))
  self.assertIn('CURRENT_CATALOGUE 10 W',str(requests[-1]))
  self.assertNotIn('CURRENT_CATALOGUE',str(agent.history))
  current[0]='31 W';user.text='A teď?';await fn(agent,user,NS(conversation_id='c'))
  self.assertIn('CURRENT_CATALOGUE 31 W',str(requests[-1]))
  self.assertNotIn('CURRENT_CATALOGUE 10 W',str(requests[-1]))
  self.assertIn('Kolik vyrábím?',str(requests[-1]))
  self.assertNotIn('CURRENT_CATALOGUE',str(agent.history))
  from catalog import build_catalog,render_catalog
  fn.__globals__['catalog_context']=lambda *a:render_catalog(build_catalog([
   {'entity_id':'text.router_login','state':'PRIVATE_PASSWORD','attributes':{'mode':'password'}},
   {'entity_id':'sensor.api_token','state':'PRIVATE_TOKEN','attributes':{}},
   {'entity_id':'select.stream','state':'Local','attributes':{'options':['https://PRIVATE_URL/stream']}}
  ],[],[],[],set()))
  user.text='Jaká zařízení vidíš?';await fn(agent,user,NS(conversation_id='c'))
  self.assertNotIn('PRIVATE',str(requests[-1]));self.assertNotIn('https://',str(requests[-1]))

 async def test_voice_llm_tools_cannot_bypass_local_authorization(self):
  for name in ('execute_function','execute_tool_function'):
   fn=self.method(name)
   agent=NS(hass=NS(data={'jarvis_speaker_identity':NS(enforce=True)}))
   user=NS(device_id='mic',satellite_id='sat')
   if name=='execute_function':
    with self.assertRaises(fn.__globals__['HomeAssistantError']):await fn(agent,user,[],None,[],0,{})
   else:
    result=await fn(agent,user,None,[],{});self.assertIn('ověřen',result)
 def method(self,name):
  tree=ast.parse(Path(__file__).with_name('conversation.py').read_text())
  cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='ExtendedOpenAIAgentEntity')
  fn=next(n for n in cls.body if isinstance(n,ast.AsyncFunctionDef) and n.name==name)
  fn.returns=None
  for arg in fn.args.args:arg.annotation=None
  ns={'async_handle_room_command':async_handle_room_command,'is_noise_transcript':is_noise_transcript,'local_time_answer':local_time_answer,'dt_util':NS(now=lambda:__import__('datetime').datetime(2026,10,29,7,5)),'time':time,'is_stop':is_stop,'is_pause':is_pause,'recent_session':recent_session,'should_continue':should_continue,
      'conversation':NS(ConversationResult=lambda **kw:NS(**kw)), 'intent':NS(IntentResponse=Speech),
      'async_get_chat_session':lambda hass,c:nullcontext(NS()),'async_get_chat_log':lambda *args:nullcontext(NS()),
      'CONF_ATTACH_USERNAME':'attach','DEFAULT_ATTACH_USERNAME':False,'EVENT_CONVERSATION_FINISHED':'event',
      'catalog_context':lambda *a:'','voice_input_allowed':voice_input_allowed,
      'OpenAIError':type('OpenAIError',(Exception,),{}),'HomeAssistantError':type('HAError',(Exception,),{}),'TemplateError':type('TemplateError',(Exception,),{})}
  exec(compile(ast.Module(body=[fn],type_ignores=[]),'actual-agent-method','exec'),ns)
  return ns[name]
 async def test_voice_time_answer_prepares_identity_then_skips_model(self):
  prepared=[]
  class Companion:
   async def prepare(self,*a):
    prepared.append(True);return NS(reset_history=False,principal='p',local_reply=None,prompt='memory')
  agent=NS(hass=NS(data={}),_companion=Companion(),_history_principals={},history={},get_exposed_entities=lambda:[],
    _recent_devices={},_dialogue_started={},_dialogue_turns={},
    _generate_system_message=lambda *a:(_ for _ in ()).throw(AssertionError('time must not use model')))
  result=await self.method('_async_handle_message')(agent,NS(text='Kolik je hodin?',language='cs',device_id='mic',context=NS(id='c')),NS(conversation_id='c'))
  self.assertEqual(prepared,[True]);self.assertEqual(result.response.text,'Je 7 hodin a 5 minut.')

 async def test_explicit_conversation_id_is_preserved(self):
  async def handle(user,log):return user.conversation_id
  agent=NS(hass=NS(),_companion_lock=asyncio.Lock(),_recent_devices={'dev':('old',time.monotonic())},history={'old':[]},_async_handle_message=handle)
  user=NS(text='Ahoj',device_id='dev',conversation_id='new',language='cs')
  self.assertEqual(await self.method('async_process')(agent,user),'new')
 async def test_stop_never_calls_model(self):
  async def forbidden(*args):raise AssertionError('Model must not run')
  agent=NS(hass=NS(),_recent_devices={'dev':('old',time.monotonic())},history={'old':[]},_dialogue_started={'old':1},_dialogue_turns={'old':1},_async_handle_message=forbidden)
  user=NS(text='Děkuji, konec.',device_id='dev',conversation_id='old',language='cs')
  result=await self.method('async_process')(agent,user)
  self.assertFalse(result.continue_conversation);self.assertNotIn('old',agent.history)
 async def test_stop_cancels_pending_voice_enrollment(self):
  cancelled=[]
  speaker=NS(cancel_for=lambda user:cancelled.append(user.device_id))
  agent=NS(hass=NS(data={'jarvis_speaker_identity':speaker}),_recent_devices={},history={},_dialogue_started={},_dialogue_turns={})
  user=NS(text='Děkuji, konec.',device_id='dev',conversation_id='c',language='cs')
  await self.method('async_process')(agent,user)
  self.assertEqual(cancelled,['dev'])
 async def test_turn_bound_survives_real_method_with_truncated_history(self):
  async def query(user,messages,entities,depth):
   messages[:]=messages[:1] # emulate context truncation at the API boundary
   return NS(message=NS(content='Navazuji na rozhovor.',model_dump=lambda **kw:{'role':'assistant','content':'Navazuji na rozhovor.'}),response=NS(model_dump=lambda:{}))
  class Companion:
   async def prepare(self,*args):return NS(reset_history=False,principal='guest:c',local_reply=None,prompt='memory data')
   async def finish(self,turn,response):return response
  agent=NS(_companion=Companion(),_history_principals={'c':'guest:c'},history={'c':[{'role':'system'}]},_recent_devices={},_dialogue_started={},_dialogue_turns={},options={},subentry=NS(subentry_id='s'),hass=NS(bus=NS(async_fire=lambda *args:None)),get_exposed_entities=lambda:[],query=query,_generate_system_message=lambda *a:{'role':'system'})
  user=NS(text='Pokračuj',device_id='dev',language='cs',conversation_id='c',context=NS(user_id=None))
  for i in range(32):
   result=await self.method('_async_handle_message')(agent,user,NS(conversation_id='c'))
   self.assertEqual(result.continue_conversation,i<31)
  self.assertEqual(agent._dialogue_turns['c'],32)

 async def test_room_command_uses_local_handler_and_never_model(self):
  async def forbidden(*a,**kw):raise AssertionError('model must not run')
  class Companion:
   async def prepare(self,*a):return NS(reset_history=False,principal='p',local_reply=None)
  agent=NS(_companion=Companion(),_history_principals={},history={},get_exposed_entities=lambda:[],
   _recent_devices={},_dialogue_started={},_dialogue_turns={},hass=NS(),query=forbidden,
   _generate_system_message=lambda *a:(_ for _ in ()).throw(AssertionError('local command must not prepare model prompt')))
  fn=self.method('_async_handle_message')
  async def local(*a):return ''
  fn.__globals__['async_handle_room_command']=local
  result=await fn(agent,NS(text='Rozsviť',language='cs',device_id='mic'),NS(conversation_id='c'))
  self.assertEqual(result.response.text,'')
  self.assertFalse(result.continue_conversation)
  self.assertNotIn('c',agent._dialogue_turns)
  self.assertNotIn('c',agent._dialogue_started)
 async def test_local_commands_do_not_leak_unbounded_session_counters(self):
  class Companion:
   async def prepare(self,*a):return NS(reset_history=False,principal='p',local_reply='Místní odpověď.')
  agent=NS(_companion=Companion(),_history_principals={},history={},get_exposed_entities=lambda:[],
   _recent_devices={},_dialogue_started={},_dialogue_turns={},hass=NS())
  fn=self.method('_async_handle_message')
  for n in range(40):
   await fn(agent,NS(text='Rozsviť',language='cs',device_id='mic'),NS(conversation_id=str(n)))
  self.assertLessEqual(len(agent._dialogue_turns),16)
  self.assertLessEqual(len(agent._dialogue_started),16)

 async def test_time_answer_never_calls_model_and_closes(self):
  async def forbidden(*args):raise AssertionError('Model must not run')
  agent=NS(_recent_devices={},hass=NS(),_async_handle_message=forbidden)
  result=await self.method('async_process')(agent,NS(text='Kolik je hodin?',device_id=None,conversation_id=None,language='cs'))
  self.assertEqual(result.response.text,'Je 7 hodin a 5 minut.');self.assertFalse(result.continue_conversation)
 async def test_context_artifact_never_calls_model_or_speaks(self):
  async def forbidden(*args):raise AssertionError('Model must not run')
  agent=NS(_recent_devices={},hass=NS(),_async_handle_message=forbidden)
  result=await self.method('async_process')(agent,NS(text='context:',device_id='dev',conversation_id=None,language='cs'))
  self.assertEqual(result.response.text,'');self.assertFalse(result.continue_conversation)

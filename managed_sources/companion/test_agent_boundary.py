"""Execute actual deployed agent methods with isolated HA/API boundary doubles."""
import ast
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace as NS
import time
import asyncio
import unittest
from room_commands import async_handle_room_command
from dialogue import is_stop, is_pause, recent_session, should_continue
class Speech:
 def __init__(self,**kw):pass
 def async_set_speech(self,text):self.text=text
class MethodTests(unittest.IsolatedAsyncioTestCase):
 def method(self,name):
  tree=ast.parse(Path(__file__).with_name('conversation.py').read_text())
  cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='ExtendedOpenAIAgentEntity')
  fn=next(n for n in cls.body if isinstance(n,ast.AsyncFunctionDef) and n.name==name)
  fn.returns=None
  for arg in fn.args.args:arg.annotation=None
  ns={'async_handle_room_command':async_handle_room_command,'time':time,'is_stop':is_stop,'is_pause':is_pause,'recent_session':recent_session,'should_continue':should_continue,
      'conversation':NS(ConversationResult=lambda **kw:NS(**kw)), 'intent':NS(IntentResponse=Speech),
      'async_get_chat_session':lambda hass,c:nullcontext(NS()),'async_get_chat_log':lambda *args:nullcontext(NS()),
      'CONF_ATTACH_USERNAME':'attach','DEFAULT_ATTACH_USERNAME':False,'EVENT_CONVERSATION_FINISHED':'event',
      'OpenAIError':type('OpenAIError',(Exception,),{}),'HomeAssistantError':type('HAError',(Exception,),{}),'TemplateError':type('TemplateError',(Exception,),{})}
  exec(compile(ast.Module(body=[fn],type_ignores=[]),'actual-agent-method','exec'),ns)
  return ns[name]
 async def test_explicit_conversation_id_is_preserved(self):
  async def handle(user,log):return user.conversation_id
  agent=NS(hass=NS(),_companion_lock=asyncio.Lock(),_recent_devices={'dev':('old',time.monotonic())},history={'old':[]},_async_handle_message=handle)
  user=NS(text='Ahoj',device_id='dev',conversation_id='new')
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
  agent=NS(_companion=Companion(),_history_principals={'c':'guest:c'},history={'c':[{'role':'system'}]},_recent_devices={},_dialogue_started={},_dialogue_turns={},options={},subentry=NS(subentry_id='s'),hass=NS(bus=NS(async_fire=lambda *args:None)),get_exposed_entities=lambda:[],query=query)
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
  async def local(*a):return 'Rozsvítil jsem světla. Místnost: Obývák.'
  fn.__globals__['async_handle_room_command']=local
  result=await fn(agent,NS(text='Rozsviť',language='cs',device_id='mic'),NS(conversation_id='c'))
  self.assertIn('Obývák',result.response.text)
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

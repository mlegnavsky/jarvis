import ast
import asyncio
import json
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace as NS
import unittest
import voice_policy

class QueryPolicyTests(unittest.IsolatedAsyncioTestCase):
 async def test_real_query_selects_only_primary_voice_model_and_retains_client(self):
  tree=ast.parse(Path(__file__).with_name('conversation.py').read_text())
  cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='ExtendedOpenAIAgentEntity')
  fn=next(n for n in cls.body if isinstance(n,ast.AsyncFunctionDef) and n.name=='query')
  fn.returns=None
  for arg in fn.args.args:arg.annotation=None
  scope={'time':time,'json':json,'primary_voice':voice_policy.primary_voice,'read_policy':voice_policy.read_policy,'request_policy':voice_policy.request_policy,'safe_model':voice_policy.safe_model,
    'bound_messages':lambda m:None,'HomeAssistantError':ValueError,'_LOGGER':NS(debug=lambda *a:None),
    'OpenAIQueryResponse':lambda **kw:NS(**kw)}
  for name,key,default in [('CHAT_MODEL','chat_model','gpt-4o'),('MAX_TOKENS','max_tokens',300),('TOP_P','top_p',1),('TEMPERATURE','temperature',.7),('USE_TOOLS','use_tools',True),('CONTEXT_THRESHOLD','context_threshold',10000),('MAX_FUNCTION_CALLS_PER_CONVERSATION','max_function_calls_per_conversation',1)]:
   scope['CONF_'+name]=key;scope['DEFAULT_'+name]=default
  exec(compile(ast.Module(body=[fn],type_ignores=[]),'actual-query','exec'),scope)
  requests=[]
  async def create(**kw):
   requests.append(kw)
   return NS(usage=NS(total_tokens=5,completion_tokens=3),choices=[NS(finish_reason='stop',message=NS(content='Ahoj.',function_call=None,tool_calls=None))],model_dump=lambda **kw:{})
  async def execute(func,*args):return func(*args)
  with tempfile.TemporaryDirectory() as d:
   path=Path(d)/'voice-settings.json';path.write_text(json.dumps({'schema':1,'model':'gpt-4.1-mini'}))
   hass=NS(data={},config=NS(path=lambda *a:str(path)),async_add_executor_job=execute)
   agent=NS(options={},hass=hass,client=NS(chat=NS(completions=NS(create=create))),get_functions=lambda:[])
   for satellite in (voice_policy.SATELLITE,None):
    user=NS(device_id=None,satellite_id=satellite,conversation_id='c')
    await scope['query'](agent,user,[{'role':'user','content':'Ahoj'}],[],0)
   self.assertEqual(requests[0]['model'],'gpt-4.1-mini')
   self.assertEqual(requests[0]['max_tokens'],512)
   self.assertEqual(requests[1]['model'],'gpt-4o')
   self.assertEqual(requests[1]['max_completion_tokens'],300)
   self.assertNotIn('tools',requests[0])
   self.assertEqual(hass.data['jarvis_voice_model_facts']['model'],'gpt-4.1-mini')

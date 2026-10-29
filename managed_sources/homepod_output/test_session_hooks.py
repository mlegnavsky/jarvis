"""Exercise the actual nested run-event hook without importing HA."""
import ast
import asyncio
from pathlib import Path
from types import SimpleNamespace as NS
import unittest

class SessionEventTests(unittest.IsolatedAsyncioTestCase):
 def hook(self):
  source=ast.parse(Path(__file__).with_name('__init__.py').read_text())
  setup=next(n for n in source.body if isinstance(n,ast.AsyncFunctionDef) and n.name=='async_setup')
  hook=next(n for n in setup.body if isinstance(n,ast.FunctionDef) and n.name=='session_event')
  factory=ast.parse('''
def bind(hass,television):
 tv_prepare=None;active_run=None;lease_started=None;active_pipeline=False;pending_followup=False
 restored=[]
 native_event=lambda run,event:None
 async def restore_tv(owner):restored.append(owner)
 return None
''').body[0]
  factory.body[-1:]=[hook,*ast.parse("return session_event,lambda:(active_run,active_pipeline,pending_followup),restored").body]
  ast.fix_missing_locations(factory)
  scope={'time':NS(monotonic=lambda:1),'PIPELINE':'p','SATELLITE':'s'}
  exec(compile(ast.Module(body=[factory],type_ignores=[]),'actual-session-hook','exec'),scope)
  async def acquire():pass
  tasks=[]
  hass=NS(async_create_task=lambda c:tasks.append(asyncio.create_task(c)))
  fn,state,restored=scope['bind'](hass,NS(snapshot=lambda:{'owned':False},acquire=acquire))
  def run(id):return NS(hass=hass,pipeline=NS(id='p'),_satellite_id='s',id=id)
  return fn,state,restored,tasks,run
 async def test_old_cleanup_does_not_mark_new_run_inactive(self):
  fn,state,restored,tasks,run=self.hook();a,b=run('a'),run('b')
  fn(a,NS(type='run-start',data={}));fn(b,NS(type='run-start',data={}))
  fn(a,NS(type='error',data={}));fn(a,NS(type='run-end',data={}))
  self.assertEqual(state(),('b',True,False))
  await asyncio.gather(*tasks)
  self.assertFalse(restored)
 async def test_old_intent_does_not_overwrite_current_followup(self):
  fn,state,restored,tasks,run=self.hook();a,b=run('a'),run('b')
  fn(a,NS(type='run-start',data={}));fn(b,NS(type='run-start',data={}))
  fn(b,NS(type='intent-end',data={'intent_output':{'continue_conversation':True}}))
  fn(a,NS(type='intent-end',data={'intent_output':{'continue_conversation':False}}))
  self.assertEqual(state(),('b',True,True))
  await asyncio.gather(*tasks)

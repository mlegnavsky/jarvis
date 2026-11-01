import unittest
from types import SimpleNamespace as NS
import routing

class StartupVolumeTests(unittest.IsolatedAsyncioTestCase):
 async def test_startup_primes_45_through_raop_and_never_plays_audio(self):
  calls=[];active=False
  class Player:
   volume_level=0;is_volume_muted=False
   async def async_set_volume_level(self,value):
    self_test.assertTrue(active);self.volume_level=value;calls.append(value)
   async def async_play_media(self,*args):raise AssertionError('startup must not play audio')
  def takeover(entity):
   nonlocal active
   active=True
   def release():
    nonlocal active
    active=False
   return release
  self_test=self
  result=await routing.prime_startup_volume(Player(),takeover_audio=takeover)
  self.assertEqual(calls,[.45]);self.assertEqual(result,.45);self.assertFalse(active)
 async def test_snapshot_reads_raop_instead_of_idle_companion_zero(self):
  active=False;calls=[]
  class Player:
   is_volume_muted=False
   @property
   def volume_level(self):return .45 if active else 0
   async def async_set_volume_level(self,value):calls.append(('volume',value))
   async def async_play_media(self,*args):calls.append(('play',args))
  def takeover(entity):
   nonlocal active
   active=True
   def release():
    nonlocal active
    active=False
   return release
  result=await routing.play_at_current_volume(Player(),'speech',takeover_audio=takeover)
  self.assertTrue(result['played']);self.assertEqual(result['volume'],.45)
  self.assertEqual(calls[0],('volume',.45));self.assertFalse(active)
 async def test_real_raop_zero_is_still_respected(self):
  async def forbidden(*args):raise AssertionError('zero must not play')
  result=await routing.play_at_current_volume(NS(volume_level=0,is_volume_muted=False,async_set_volume_level=forbidden,async_play_media=forbidden),'speech',takeover_audio=lambda e:lambda:None)
  self.assertFalse(result['played'])
 async def test_failed_startup_releases_protocol_and_does_not_claim_success(self):
  released=[]
  async def fail(value):raise TimeoutError()
  player=NS(volume_level=0,async_set_volume_level=fail)
  with self.assertRaises(TimeoutError):await routing.prime_startup_volume(player,takeover_audio=lambda e:lambda:released.append(True))
  self.assertEqual(released,[True])
 async def test_startup_hook_applies_once_and_leaves_later_manual_volume_alone(self):
  import ast,asyncio
  from pathlib import Path
  source=ast.parse(Path(__file__).with_name('__init__.py').read_text())
  setup=next(n for n in source.body if isinstance(n,ast.AsyncFunctionDef) and n.name=='async_setup')
  start=next(n for n in setup.body if isinstance(n,ast.AsyncFunctionDef) and n.name=='start')
  calls=[];player=NS(volume_level=0)
  async def prime(entity):calls.append(.45);entity.volume_level=.45;return .45
  async def update():pass
  env={'asyncio':asyncio,'startup_volume':{'status':'pending'},'prime_startup_volume':prime,'player':lambda:player,'update':update,'router':NS(lock=asyncio.Lock())}
  exec(compile(ast.fix_missing_locations(ast.Module(body=[start],type_ignores=[])),'startup-hook','exec'),env)
  await env['start']();player.volume_level=.22;await env['start']()
  self.assertEqual(calls,[.45]);self.assertEqual(player.volume_level,.22)
 async def test_answer_waits_until_startup_releases_raop_takeover(self):
  import ast,asyncio
  from pathlib import Path
  source=ast.parse(Path(__file__).with_name('__init__.py').read_text())
  setup=next(n for n in source.body if isinstance(n,ast.AsyncFunctionDef) and n.name=='async_setup')
  start=next(n for n in setup.body if isinstance(n,ast.AsyncFunctionDef) and n.name=='start')
  priming=asyncio.Event();release=asyncio.Event();answer_entered=asyncio.Event();lock=asyncio.Lock()
  async def prime(entity):priming.set();await release.wait();return .45
  async def update():pass
  env={'asyncio':asyncio,'startup_volume':{'status':'pending'},'prime_startup_volume':prime,'player':lambda:NS(volume_level=0),'update':update,'router':NS(lock=lock)}
  exec(compile(ast.fix_missing_locations(ast.Module(body=[start],type_ignores=[])),'startup-hook','exec'),env)
  async def answer():
   async with lock:answer_entered.set()
  startup=asyncio.create_task(env['start']());await priming.wait();reply=asyncio.create_task(answer());await asyncio.sleep(0)
  try:self.assertFalse(answer_entered.is_set())
  finally:release.set();await startup;await reply
  self.assertTrue(answer_entered.is_set())

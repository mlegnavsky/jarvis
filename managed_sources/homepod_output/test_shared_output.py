"""Exercise the actual production play closure across the owned TV pause."""
import ast,asyncio,unittest
from pathlib import Path
from types import SimpleNamespace as NS
import routing
from tv_session import TVSession

class SharedOutputTests(unittest.IsolatedAsyncioTestCase):
 def route(self,tv_volume=.55,muted=False,enabled=True,initial='playing'):
  source=ast.parse(Path(__file__).with_name('__init__.py').read_text())
  setup=next(n for n in source.body if isinstance(n,ast.AsyncFunctionDef) and n.name=='async_setup')
  play=next(n for n in setup.body if isinstance(n,ast.AsyncFunctionDef) and n.name=='play')
  calls=[]
  class Player:
   volume_level=.55;is_volume_muted=False
   async def async_set_volume_level(self,value):self.volume_level=value;calls.append(('volume',value))
   async def async_play_media(self,kind,media):calls.append(('play',media))
  player=Player()
  state={'state':initial,'attributes':{'media_title':'Film','app_id':'tv','volume_level':tv_volume,'is_volume_muted':muted}}
  async def service(name):
   self.assertEqual(name,'media_pause')
   state['state']='paused';player.volume_level=0
  television=TVSession(lambda:state,service)
  factory=ast.parse("""
def bind(player,television,shared_volume_source):
 last_volume={}
 tv_prepare=asyncio.create_task(television.acquire())
 return None
""").body[0]
  factory.body[-1:]=[play,*ast.parse('return play,tv_prepare').body]
  ast.fix_missing_locations(factory)
  async def native_play(entity,media,**kwargs):
   return await routing.play_at_current_volume(entity,media,takeover_audio=lambda _:lambda:None,**kwargs)
  scope={'asyncio':asyncio,'play_at_current_volume':native_play,'TELEVISION':'media_player.tv'}
  exec(compile(ast.Module(body=[factory],type_ignores=[]),'actual-shared-play','exec'),scope)
  fn,prepare=scope['bind'](lambda:player,television,'media_player.tv' if enabled else None)
  return fn,prepare,calls,state,player,television
 async def test_owned_pause_uses_actual_shared_volume_instead_of_idle_raop_zero(self):
  play,prepare,calls,*_=self.route()
  await play('answer')
  self.assertEqual(calls,[('volume',.55),('play','answer')])
 async def test_latest_shared_zero_or_mute_does_not_unmute_the_homepod(self):
  for volume,muted in [(0,False),(.55,True)]:
   play,prepare,calls,*_=self.route(tv_volume=volume,muted=muted)
   await play('answer');self.assertEqual(calls,[])
 async def test_volume_changed_after_pause_is_used_for_answer(self):
  play,prepare,calls,state,*_=self.route();await prepare
  state['attributes']['volume_level']=.21
  await play('answer');self.assertEqual(calls,[('volume',.21),('play','answer')])
 async def test_shared_unknown_volume_never_uses_a_positive_default(self):
  play,prepare,calls,state,*_=self.route();await prepare
  state['attributes']['volume_level']=None
  with self.assertRaises(ValueError):await play('answer')
  self.assertEqual(calls,[])
 async def test_disabled_or_replaced_shared_route_preserves_idle_homepod_zero(self):
  for enabled in (False,True):
   play,prepare,calls,state,player,tv=self.route(enabled=enabled);await prepare
   if enabled:state['attributes']['media_title']='Different film'
   await play('answer');self.assertEqual(calls,[])
 async def test_explicit_homepod_mute_overrides_shared_positive_level(self):
  play,prepare,calls,state,player,*_=self.route();await prepare
  player.is_volume_muted=True
  await play('answer');self.assertEqual(calls,[])
 async def test_intentionally_silent_output_is_not_counted_as_completed_audio(self):
  async def forbidden(*args):raise AssertionError('muted audio cannot play')
  entity=NS(volume_level=0,is_volume_muted=False,async_set_volume_level=forbidden,async_play_media=forbidden)
  async def play(media):return await routing.play_at_current_volume(entity,media,takeover_audio=lambda _:lambda:None)
  async def stop():pass
  router=routing.Router(play,stop)
  await router.answer(NS(id='run'),{'media_id':'answer'})
  self.assertEqual(router.completed,0)
  self.assertEqual(router.snapshot().get('skipped'),1)
  self.assertEqual(router.snapshot()['last_playback']['outcome'],'skipped')

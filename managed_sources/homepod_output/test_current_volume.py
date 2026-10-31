import unittest
from types import SimpleNamespace
import routing


class CurrentVolumeTests(unittest.IsolatedAsyncioTestCase):
 async def test_each_answer_uses_current_setting_not_fixed_speech_level(self):
  calls=[]
  class Player:
   volume_level=.22;is_volume_muted=False
   async def async_set_volume_level(self,level):calls.append(('volume',level))
   async def async_play_media(self,kind,media):calls.append(('play',media))
  player=Player()
  play=getattr(routing,'play_at_current_volume',None)
  self.assertIsNotNone(play)
  first=await play(player,'first',takeover_audio=lambda entity:lambda:None)
  player.volume_level=.61
  second=await play(player,'second',takeover_audio=lambda entity:lambda:None)
  self.assertEqual(calls,[('volume',.22),('play','first'),('volume',.61),('play','second')])
  self.assertEqual(first['volume'],.22);self.assertEqual(second['volume'],.61)
 async def test_zero_and_mute_are_preserved_without_starting_audio(self):
  async def forbidden(*args):raise AssertionError('silent output must remain silent')
  for level,muted in [(0,False),(.5,True)]:
   entity=SimpleNamespace(volume_level=level,is_volume_muted=muted,
    async_set_volume_level=forbidden,async_play_media=forbidden)
   play=getattr(routing,'play_at_current_volume',None)
   self.assertIsNotNone(play)
   result=await play(entity,'speech',takeover_audio=lambda entity:lambda:None)
   self.assertFalse(result['played'])
   self.assertEqual(result['volume'],level)
 async def test_unavailable_volume_never_falls_back_to_a_louder_default(self):
  play=getattr(routing,'play_at_current_volume',None)
  self.assertIsNotNone(play)
  for level in (None,True,float('nan'),float('inf'),-1,1.1):
   with self.assertRaises(ValueError):
    await play(SimpleNamespace(volume_level=level,is_volume_muted=False),'speech')


if __name__=='__main__':unittest.main()

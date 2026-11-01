"""Local output owns exact announcement commands and waits for real state."""
import asyncio
import importlib
import io
import wave
from types import SimpleNamespace as NS
import unittest


class NativeOutputTests(unittest.IsolatedAsyncioTestCase):
    def output(self, *, muted=False, volume=.4):
        module=importlib.import_module('ha_io')
        self.commands=[];self.levels=[];self.player=NS(state='idle',available=True,is_volume_muted=muted,volume_level=volume)
        self.time=0.
        async def tts(text):return NS(media_id='tts-file',pcm=bytes(32000))
        async def start(player,media):self.commands.append(('play',media));player.state='playing'
        async def stop(player):self.commands.append(('stop',));player.state='idle'
        async def wait(seconds):
            self.time+=seconds
            if self.time>.15:self.player.state='idle'
            await asyncio.sleep(0)
        return module.LocalOutput(lambda:self.player,tts,start,stop,clock=lambda:self.time,sleep=wait)

    async def test_completion_awaits_player_end_not_dispatch(self):
        output=self.output();await output.play('answer')
        self.assertGreater(self.time,.15)
        self.assertEqual(output.snapshot()['completed'],1)
        self.assertFalse(output.owned)

    async def test_muted_or_zero_volume_never_speaks(self):
        for kwargs in ({'muted':True},{'volume':0}):
            output=self.output(**kwargs);await output.play('answer')
            self.assertEqual(self.commands,[])
            self.assertEqual(output.snapshot()['skipped'],1)

    async def test_foreign_existing_playback_is_not_overwritten(self):
        output=self.output();self.player.state='playing'
        with self.assertRaises(ValueError):await output.play('answer')
        self.assertEqual(self.commands,[])

    async def test_cancel_sends_stop_only_for_own_playback(self):
        output=self.output();await output.stop();self.assertEqual(self.commands,[])
        output.owned=True;await output.stop()
        self.assertEqual(self.commands,[('stop',)])

    async def test_external_ownership_loss_does_not_stop_new_audio(self):
        output=self.output();output.owned=True;output.disown()
        await output.stop();self.assertEqual(self.commands,[])

    async def test_cancelled_playback_stops_owned_native_audio(self):
        output=self.output();playing=asyncio.Event()
        async def start(player,media):player.state='playing';playing.set()
        async def wait(seconds):await asyncio.Event().wait()
        output.start=start;output.sleep=wait
        task=asyncio.create_task(output.play('answer'));await playing.wait()
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):await task
        self.assertIn(('stop',),self.commands)
        self.assertFalse(output.owned)

    async def test_foreign_playback_started_during_synthesis_is_preserved(self):
        output=self.output()
        async def tts(text):
            self.player.state='playing'
            return NS(media_id='own',pcm=bytes(32000))
        output.tts=tts
        with self.assertRaises(ValueError):await output.play('answer')
        self.assertEqual(self.commands,[])

    def test_indirect_external_targets_resolve_before_relinquishing(self):
        io=importlib.import_module('ha_io');player='media_player.local'
        for key in ('device_id','area_id','label_id','entity_id'):
            with self.subTest(key=key):
                data={'domain':'media_player','service':'play_media','service_data':{key:'indirect-target'}}
                seen=[]
                def resolve(target):
                    seen.append(target)
                    return NS(referenced=set(),indirectly_referenced={player})
                self.assertTrue(io.is_output_change(data,player,resolve))
                self.assertEqual(seen,[data['service_data']])
                self.assertFalse(io.is_output_change(data,'media_player.other',resolve))

    async def test_disconnect_is_not_a_verified_stop(self):
        output=self.output();output.owned=True;self.player.available=False
        with self.assertRaises(ValueError):await output.stop()
        self.assertEqual(output.snapshot()['stopped'],0)

    def test_wave_reference_checks_actual_pcm_and_format(self):
        module=importlib.import_module('ha_io')
        for rate in (16000,48000):
            data=io.BytesIO()
            with wave.open(data,'wb') as writer:
                writer.setnchannels(1);writer.setsampwidth(2);writer.setframerate(rate);writer.writeframes(bytes(3200))
            if rate==16000:self.assertEqual(module.decode_reference(data.getvalue()),bytes(3200))
            else:
                with self.assertRaises(ValueError):module.decode_reference(data.getvalue())

    def test_stop_packet_explicitly_targets_announcement_and_device(self):
        module=importlib.import_module('ha_io');sent=[]
        player=NS(_client=NS(media_player_command=lambda *a,**kw:sent.append((a,kw))),_key=19,_static_info=NS(device_id=7))
        module.stop_announcement(player,stop_command='STOP')
        self.assertEqual(sent,[((19,),{'command':'STOP','announcement':True,'device_id':7})])

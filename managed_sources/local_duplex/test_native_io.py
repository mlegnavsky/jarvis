"""Local output owns exact announcement commands and waits for real state."""
import asyncio
import importlib
import io
import wave
from types import SimpleNamespace as NS
import unittest


class NativeOutputTests(unittest.IsolatedAsyncioTestCase):
    def test_pcm_signal_distinguishes_silent_and_real_audio_without_retaining_it(self):
        io=importlib.import_module('ha_io')
        self.assertTrue(io.pcm_signal(bytes(3200))['silent'])
        result=io.pcm_signal(b'\x00\x20'*1600)
        self.assertFalse(result['silent'])
        self.assertAlmostEqual(result['peak_dbfs'],-12.04,places=2)
        self.assertAlmostEqual(result['rms_dbfs'],-12.04,places=2)
        self.assertNotIn('audio',result)

    def test_restart_only_selects_exact_device_restart_button(self):
        io=importlib.import_module('ha_io');sent=[];button_type=object()
        client=NS(button_command=lambda key,**kw:sent.append((key,kw)))
        infos={(0,3):NS(key=3,device_id=0,name='Factory Reset'),
               (7,9):NS(key=9,device_id=7,name='Restart'),
               (0,8):NS(key=8,device_id=0,name='Restart')}
        player=NS(_client=client,_static_info=NS(device_id=0),_entry_data=NS(client=client,info={button_type:infos}))
        io.restart_native(player,button_type=button_type)
        self.assertEqual(sent,[(8,{'device_id':0})])
        del infos[(0,8)]
        with self.assertRaises(ValueError):io.restart_native(player,button_type=button_type)

    def test_renamed_user_disabled_restart_cannot_be_pressed(self):
        io=importlib.import_module('ha_io');sent=[];button_type=object();info=NS(key=8,device_id=0,name='Restart')
        client=NS(button_command=lambda *a,**kw:sent.append((a,kw)))
        player=NS(_client=client,_static_info=NS(device_id=0),_entry_data=NS(client=client,
            device_info=NS(mac_address='aa:bb:cc:00:11:22'),info={button_type:{(0,8):info}}))
        looked_up=[]
        registry=NS(async_get_entity_id=lambda domain,platform,unique:looked_up.append((domain,platform,unique)) or 'button.renamed_restart',
            async_get=lambda entity_id:NS(disabled_by='user') if entity_id=='button.renamed_restart' else None)
        allowed=lambda button:io.restart_allowed(registry,player,button,lambda mac,button:'exact-native-unique-id')
        with self.assertRaises(ValueError):io.restart_native(player,button_type=button_type,allowed=allowed)
        self.assertEqual(looked_up,[('button','esphome','exact-native-unique-id')])
        self.assertEqual(sent,[])

    def test_reassert_output_preserves_zero_and_mute(self):
        io=importlib.import_module('ha_io');sent=[]
        player=NS(available=True,volume_level=0,is_volume_muted=True,_key=19,_static_info=NS(device_id=0),
            _client=NS(media_player_command=lambda *a,**kw:sent.append((a,kw))))
        io.reassert_output(player,mute_command='MUTE',unmute_command='UNMUTE')
        self.assertEqual(sent,[((19,),{'volume':0,'device_id':0}),((19,),{'command':'MUTE','device_id':0})])

    async def test_software_recovery_requires_observed_disconnect_and_reconnect(self):
        io=importlib.import_module('ha_io');self.time=0.;events=[]
        player=NS(available=True,state='idle',_state=NS(),_key=19,_static_info=NS(device_id=0),_entry_data=NS(stale_state=set()))
        def restart(p):events.append('restart');player.available=False
        def reassert(p):events.append('reassert')
        async def wait(seconds):
            self.time+=seconds
            if self.time>=.4:player.available=True
        result=await io.recover_native_output(lambda:player,restart,reassert,clock=lambda:self.time,sleep=wait)
        self.assertEqual(events,['restart','reassert'])
        self.assertTrue(result['disconnect_observed'] and result['reconnect_observed'])
        self.assertFalse(result['microphone_opened'])
        async def quick(seconds):self.time+=20
        with self.assertRaises(TimeoutError):
            await io.recover_native_output(lambda:player,lambda p:None,reassert,clock=lambda:self.time,sleep=quick)

    async def test_recovery_waits_for_fresh_exact_player_state_before_reassert(self):
        io=importlib.import_module('ha_io');self.time=0.;sent=[];state=NS()
        key=(type(state),0,19)
        player=NS(available=True,state='idle',_state=state,_key=19,_static_info=NS(device_id=0),
            _entry_data=NS(stale_state=set()),volume_level=.8,is_volume_muted=False)
        def restart(p):player.available=False;player._entry_data.stale_state.add(key)
        async def wait(seconds):
            self.time+=seconds
            if self.time>=.2:player.available=True
            if self.time>=.6:
                player.volume_level=0;player.is_volume_muted=True
                player._entry_data.stale_state.discard(key)
        result=await io.recover_native_output(lambda:player,restart,
            lambda p:sent.append((self.time,p.volume_level,p.is_volume_muted)),clock=lambda:self.time,sleep=wait)
        self.assertGreaterEqual(sent[0][0],.6)
        self.assertEqual(sent[0][1:],(0,True))
        self.assertTrue(result['fresh_state_observed'])

    def test_native_vad_priming_waits_for_probability_without_mic_audio(self):
        io=importlib.import_module('ha_io');seen=[]
        def process(audio):
            seen.append(audio)
            return -1 if len(seen)<77 else .01
        enhancer=NS(vad=NS(Process10ms=process))
        count,probability=io.prime_native_vad(enhancer)
        self.assertEqual((count,probability),(77,.01))
        self.assertTrue(all(audio==bytes(320) for audio in seen))
        with self.assertRaises(ValueError):io.prime_native_vad(NS(vad=NS(Process10ms=lambda audio:float('nan'))))
        with self.assertRaises(ValueError):io.prime_native_vad(NS(vad=NS(Process10ms=lambda audio:-1)))

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

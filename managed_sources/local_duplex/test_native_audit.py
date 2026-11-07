import asyncio
import importlib
import logging
from types import SimpleNamespace as NS
import unittest


class AudioAuditTests(unittest.IsolatedAsyncioTestCase):
    def module(self):return importlib.import_module('native_audit')

    def test_only_fixed_facts_and_numeric_audio_format_escape(self):
        facts=self.module().AudioFacts()
        for line in (
            '[C][aic3204:140]: AIC3204:',
            '[E][aic3204:142]: Communication with AIC3204 failed!',
            '[D][speaker_media_player.pipeline:130]: Decoded audio has 1 channels, 48000 Hz sample rate, and 16 bits per sample',
            '[E][speaker_media_player:100]: The announcement pipeline\'s file reader encountered an error.',
            '[D][speaker_source:123]: URL: http://private/token=PRIVATE',
            '[I][wifi:123]: password PRIVATE',
            '[E][speaker_source:123]: Error playing https://private/PRIVATE',
        ):facts.feed(NS(message=line.encode()))
        result=facts.snapshot()
        self.assertIn({'component':'aic3204','event':'communication_error'},result['facts'])
        self.assertIn({'component':'speaker_media_player.pipeline','event':'decoded_format','channels':1,'sample_rate':48000,'bits_per_sample':16},result['facts'])
        self.assertIn({'component':'speaker_media_player','event':'announcement_reader_error'},result['facts'])
        self.assertNotIn('PRIVATE',str(result));self.assertNotIn('http',str(result))
        self.assertNotIn('wifi',str(result))

    def test_bounded_and_multiline_config_dump(self):
        facts=self.module().AudioFacts()
        facts.feed(NS(message=b'\x1b[0;32m[C][i2s_audio.speaker:040]: Speaker:\n  Pin: 10\n  Buffer duration: 100\x1b[0m'))
        self.assertIn({'component':'i2s_audio.speaker','event':'pin','value':10},facts.snapshot()['facts'])
        for _ in range(1000):facts.feed(NS(message=b'[D][speaker_mixer:123]: Starting'))
        result=facts.snapshot()
        self.assertLessEqual(result['messages_processed'],512)
        self.assertLessEqual(len(result['facts']),64)
        self.assertTrue(result['truncated'])

    def test_error_suffix_is_never_copied_as_enum(self):
        facts=self.module().AudioFacts()
        facts.feed(NS(message=b'[E][audio_decoder:1]: Decoder encountered an error: ESP_ERR_PRIVATE_TOKEN_ABC123'))
        self.assertNotIn('PRIVATE_TOKEN',str(facts.snapshot()))
        self.assertEqual(facts.snapshot()['facts'][0]['code'],'unknown_error')

    async def test_existing_raw_subscription_or_transport_debug_blocks_before_request(self):
        for client_debug,ha_logs in ((True,False),(False,True)):
            calls=[];client=NS(_debug_enabled=client_debug,subscribe_logs=lambda *a,**kw:calls.append(kw))
            player=NS(_client=client,_entry_data=NS(client=client),available=True)
            with self.assertRaisesRegex(ValueError,'native_raw_logging_active'):
                await self.module().audit_native(player,None,lambda:0,ha_logging=lambda:ha_logs)
            self.assertEqual(calls,[])

    async def test_other_raw_callbacks_and_transport_logs_cannot_escape_mid_audit(self):
        module=self.module();records=[];callbacks=[];ha_enabled=[False]
        class Sink(logging.Handler):
            def emit(self,record):records.append(record.getMessage())
        sink=Sink();loggers=[logging.getLogger(name) for name in (
            'homeassistant.components.esphome.manager','aioesphomeapi.connection','aioesphomeapi._frame_helper.base')]
        old=[logger.level for logger in loggers]
        for logger in loggers:logger.addHandler(sink);logger.setLevel(logging.DEBUG)
        client=NS(log_name='exact-device',_debug_enabled=False)
        def subscribe(cb,**kw):
            callbacks.append(cb)
            return lambda:callbacks.remove(cb)
        client.subscribe_logs=subscribe
        player=NS(_client=client,_entry_data=NS(client=client,title='exact-title'),available=True)
        def raw_callback(message):loggers[0].warning('%s: %s','exact-title',message.message)
        callbacks.append(raw_callback)
        async def playback():
            # Simulate a logging/options change after the initial preflight.
            ha_enabled[0]=True;client._debug_enabled=True
            msg=NS(message=b'[I][wifi:1]: PRIVATE_PASSWORD')
            for cb in list(callbacks):cb(msg)
            loggers[1].debug('%s: Got message of type %s (len=%d): %s','exact-device','SubscribeLogsResponse',1,msg)
            loggers[2].debug('%s: Sending frame: [%s]','exact-device','PRIVATE_FRAME')
            loggers[0].info('%s: %s','other-device','unrelated retained')
            return {}
        try:
            await module.audit_native(player,playback,lambda:2,ha_logging=lambda:ha_enabled[0],debug_level=5,sleep=lambda _s:asyncio.sleep(0))
            self.assertEqual(records,['other-device: unrelated retained'])
            self.assertEqual(callbacks,[raw_callback])
            loggers[0].info('%s: %s','exact-title','logging restored')
            self.assertEqual(records[-1],'exact-title: logging restored')
        finally:
            for logger,level in zip(loggers,old):logger.removeHandler(sink);logger.setLevel(level)

    async def run_audit(self,fail=None):
        calls=[];callback=None;level=[0]
        def subscribe(cb,log_level=None,dump_config=None):
            nonlocal callback
            callback=cb;calls.append(('subscribe',log_level,dump_config))
            def unsubscribe():calls.append(('unsubscribe',log_level))
            return unsubscribe
        client=NS(subscribe_logs=subscribe)
        player=NS(_client=client,_entry_data=NS(client=client),available=True)
        async def playback():
            callback(NS(message=b'[D][speaker_mixer:123]: Starting'))
            level[0]=2
            if fail:raise fail
            return {'completed':1}
        result=None
        try:result=await self.module().audit_native(player,playback,lambda:level[0],debug_level=5,sleep=lambda _s:asyncio.sleep(0))
        finally:
            self.assertEqual(calls,[('subscribe',5,True),('unsubscribe',5),('subscribe',2,False),('unsubscribe',2)])
        return result

    async def test_subscription_restores_current_level_and_unsubscribes(self):
        result=await self.run_audit()
        self.assertTrue(result['logging_restored'])
        self.assertFalse(result['microphone_opened'])
        self.assertEqual(result['playback'],{'completed':1})

    async def test_restore_on_failure_and_cancellation(self):
        for exc in (ValueError('private-error'),asyncio.CancelledError()):
            with self.assertRaises(type(exc)):await self.run_audit(exc)

    async def test_mismatched_native_connection_never_subscribes(self):
        player=NS(_client=NS(),_entry_data=NS(client=NS()),available=True)
        with self.assertRaisesRegex(ValueError,'native_connection_mismatch'):
            await self.module().audit_native(player,None,lambda:0)

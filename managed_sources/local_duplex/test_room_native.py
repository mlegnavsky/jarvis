"""Fixed native start and terminal events preserve a foreign owner."""
import asyncio
import importlib
import importlib.util
from types import SimpleNamespace as NS
import unittest


class NativeRoomTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.assertIsNotNone(importlib.util.find_spec('room_native'),'fixed native room link missing')
        self.module=importlib.import_module('room_native');self.events=[];self.calls=[];self.announcements=[]
        async def start(**kwargs):self.calls.append(kwargs)
        self.entity=NS(entity_id='assist_satellite.home_assistant_voice_0a8bde_assist_satellite',
            _pipeline_task=None,_extra_system_prompt=None,async_internal_start_conversation=start,
            on_pipeline_event=self.events.append)
        self.link=self.module.NativeRoomLink(self.entity,
            lambda:self.announcements.append('stop'),lambda kind,data=None:NS(kind=kind,data=data))
        self.media='media-source://media_source/local/jarvis_speech/jarvis-'+'a'*32+'.wav'
        self.marker='jarvis-room-test:'+'b'*32

    async def test_fixed_native_start_has_no_text_and_disables_preannounce(self):
        await self.link.start(self.media,self.marker)
        self.assertEqual(self.calls,[{'start_media_id':self.media,
            'extra_system_prompt':self.marker,'preannounce':False}])

    async def test_terminal_stop_clears_continuation_and_prompt_before_announcement_stop(self):
        await self.link.start(self.media,self.marker)
        self.entity._extra_system_prompt=self.marker
        await self.link.stop(self.marker,None)
        self.assertEqual([x.kind for x in self.events],['intent_end','run_end'])
        self.assertFalse(self.events[0].data['intent_output']['continue_conversation'])
        self.assertIsNone(self.entity._extra_system_prompt)
        self.assertEqual(self.announcements,['stop'])

    async def test_foreign_pipeline_and_external_announcement_are_never_stopped(self):
        await self.link.start(self.media,self.marker)
        task=asyncio.create_task(asyncio.sleep(10));self.entity._pipeline_task=task
        self.entity._extra_system_prompt=self.marker
        try:
            await self.link.stop(self.marker,None)
            self.assertFalse(task.cancelled());self.assertEqual(self.events,[])
            self.assertEqual(self.announcements,[])
            self.assertIsNone(self.entity._extra_system_prompt)
        finally:task.cancel();await asyncio.gather(task,return_exceptions=True)
        self.entity._pipeline_task=None;self.link.disown()
        await self.link.stop(self.marker,None)
        self.assertEqual(self.events,[]);self.assertEqual(self.announcements,[])

    async def test_wrong_target_media_and_marker_cannot_start(self):
        for media,marker in [('https://other.invalid/audio',self.marker),(self.media,'arbitrary')]:
            with self.assertRaises(ValueError):await self.link.start(media,marker)
        self.entity.entity_id='assist_satellite.other'
        with self.assertRaises(ValueError):await self.link.start(self.media,self.marker)
        self.assertEqual(self.calls,[])

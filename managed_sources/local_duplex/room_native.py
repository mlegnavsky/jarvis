"""Fixed Core2026.6.4 satellite protocol for the consented room test."""
import re

TARGET='assist_satellite.home_assistant_voice_0a8bde_assist_satellite'
MEDIA=re.compile(r'media-source://media_source/local/jarvis_speech/jarvis-[a-f0-9]{32}\.wav')
MARKER=re.compile(r'jarvis-room-test:[a-f0-9]{32}')


class NativeRoomLink:
    def __init__(self,entity,stop_announcement,event):
        self.entity=entity;self.stop_announcement=stop_announcement;self.event=event
        self.marker=None;self.owned=False;self.terminal_sent=False;self.foreign_preserved=False
        self.original_client=getattr(entity,'cli',None)

    async def start(self,media_id,marker):
        if (self.entity.entity_id!=TARGET or not isinstance(media_id,str) or not MEDIA.fullmatch(media_id)
                or not isinstance(marker,str) or not MARKER.fullmatch(marker)):
            raise ValueError('fixed_room_test_target_and_generated_media_required')
        if self.entity._pipeline_task is not None:raise ValueError('satellite_pipeline_busy')
        self.marker=marker;self.owned=True
        await self.entity.async_internal_start_conversation(start_media_id=media_id,
            extra_system_prompt=marker,preannounce=False)

    def disown(self):self.owned=False;self.foreign_preserved=True

    async def stop(self,marker,owned_pipeline):
        current=self.entity._pipeline_task
        if self.entity._extra_system_prompt==self.marker:self.entity._extra_system_prompt=None
        if (not self.owned or marker!=self.marker or self.entity.entity_id!=TARGET
                or current is not None and current is not owned_pipeline):
            self.foreign_preserved=True;return
        # START_CONVERSATION leaves the device's continuation bit set. Clear it
        # before stopping an unfinished announcement so it cannot reopen a mic.
        self.entity.on_pipeline_event(self.event('intent_end',{'intent_output':{
            'conversation_id':getattr(self.entity,'_conversation_id',None) or '',
            'continue_conversation':False}}))
        try:self.stop_announcement()
        finally:
            self.entity.on_pipeline_event(self.event('run_end'))
            self.terminal_sent=True;self.owned=False

    def snapshot(self):
        return {'owned':self.owned,'terminal_sent':self.terminal_sent,
            'foreign_owner_preserved':self.foreign_preserved,
            'scope':'fixed_native_satellite_protocol_not_receiver_stop_ack'}

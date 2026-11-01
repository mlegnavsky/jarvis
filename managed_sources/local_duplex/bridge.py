"""Completed fresh utterances enter the existing voice-authorized agent."""
from types import SimpleNamespace

INTERRUPTION_MARKER='jarvis_local_duplex:previous_answer_interrupted'


def response_facts(response):
    data=response.as_dict();speech=((data.get('speech') or {}).get('plain') or {}).get('speech') or ''
    kind=data.get('response_type','unknown')
    kind=kind if kind in ('error','action_done','query_answer') else 'unknown'
    facts={'response_type':kind,'speech_chars':len(speech),'question':str(speech).rstrip().endswith('?')}
    if kind=='error':
        code=(data.get('data') or {}).get('code','unknown')
        facts['error_code']=code if code in ('unknown','no_intent_match','no_intent_handler','failed_to_handle','no_valid_targets','not_supported') else 'unknown'
        value=str(speech).lower()
        facts['parameter_hint']=next((p for p in ('max_completion_tokens','max_tokens','temperature','top_p') if p in value),None)
        facts['authentication_hint']='invalid_api_key' in value or 'api key' in value
        facts['quota_hint']='insufficient_quota' in value or 'rate limit' in value
    return facts


class TurnBridge:
    def __init__(self,transcriber,complete,converse,*,context_factory,device_id,
                 satellite_id,conversation_id,agent_id,language,extra_system_prompt=None,
                 playback_overlap=lambda audio:False):
        self.transcriber=transcriber;self.complete=complete;self.converse=converse
        self.context_factory=context_factory;self.device_id=device_id;self.satellite_id=satellite_id
        self.conversation_id=conversation_id;self.agent_id=agent_id;self.language=language
        self.extra_system_prompt=extra_system_prompt;self.playback_overlap=playback_overlap
        self.audio=None;self.voiced=0.;self.interruption_pending=False
        self.last_response=None

    def interrupted(self):self.interruption_pending=True

    def clear(self):self.audio=None;self.voiced=0.

    async def transcribe(self,audio,voiced,truncated):
        self.clear()
        if truncated:return ''
        self.audio=audio;self.voiced=voiced
        return await self.transcriber(audio)

    async def respond(self,text):
        if self.audio is None:raise ValueError('fresh_utterance_required')
        context=self.context_factory()
        extra=self.extra_system_prompt
        if self.interruption_pending:
            extra=(extra+'\n' if extra else '')+INTERRUPTION_MARKER
            self.interruption_pending=False
        try:
            await self.complete(self.satellite_id,self.audio,self.voiced,text,
                context_id=context.id,playback=self.playback_overlap(self.audio))
            result=await self.converse(text=text,conversation_id=self.conversation_id,
                device_id=self.device_id,satellite_id=self.satellite_id,context=context,
                language=self.language,agent_id=self.agent_id,extra_system_prompt=extra)
            self.conversation_id=result.conversation_id
            self.last_response=response_facts(result.response)
            speech=((result.response.as_dict().get('speech') or {}).get('plain') or {}).get('speech') or ''
            return SimpleNamespace(speech=speech,continuing=result.continue_conversation is True)
        finally:self.clear()

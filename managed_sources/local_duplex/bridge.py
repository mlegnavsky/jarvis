"""Completed fresh utterances enter the existing voice-authorized agent."""
from types import SimpleNamespace
import time
if __package__:
    from .runtime_diagnostics import notify
else:
    from runtime_diagnostics import notify

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
                 playback_overlap=lambda audio:False,transcript_filter=lambda text,audio,at:text,
                 clock=time.monotonic,input_allowed=lambda:True):
        self.transcriber=transcriber;self.complete=complete;self.converse=converse
        self.context_factory=context_factory;self.device_id=device_id;self.satellite_id=satellite_id
        self.conversation_id=conversation_id;self.agent_id=agent_id;self.language=language
        self.extra_system_prompt=extra_system_prompt;self.playback_overlap=playback_overlap
        self.audio=None;self.voiced=0.;self.interruption_pending=False
        self.last_response=None
        self.transcript_filter=transcript_filter;self.clock=clock
        self.input_allowed=input_allowed;self.input_blocked=0
        self.capture_ended_at=None
        self.timings_ms={}
        self.on_event=None

    def set_capture_time(self,ended_at):self.capture_ended_at=ended_at

    def allowed(self):
        try:return self.input_allowed() is True
        except Exception:return False

    def rejected(self):
        self.input_blocked+=1
        return SimpleNamespace(speech='',continuing=False)

    def interrupted(self):self.interruption_pending=True

    def clear(self):self.audio=None;self.voiced=0.

    async def transcribe(self,audio,voiced,truncated):
        self.clear()
        if truncated:return ''
        if not self.allowed():self.input_blocked+=1;return ''
        self.audio=audio;self.voiced=voiced
        captured_until=self.clock() if self.capture_ended_at is None else self.capture_ended_at
        self.capture_ended_at=None
        self.timings_ms={}
        started=self.clock()
        notify(self.on_event,'stt_start')
        try:text=await self.transcriber(audio)
        except BaseException as exc:
            notify(self.on_event,'stage_error',stage='stt',error_type=type(exc).__name__,
                   duration_ms=round((self.clock()-started)*1000,1))
            raise
        finally:self.timings_ms['stt']=round((self.clock()-started)*1000,1)
        notify(self.on_event,'stt_end',transcript=text,duration_ms=self.timings_ms['stt'],
               outcome='text' if text else 'empty')
        if not self.allowed():self.input_blocked+=1;self.clear();return ''
        text=self.transcript_filter(text,audio,captured_until)
        if not text:self.clear()
        return text

    async def respond(self,text):
        if not self.allowed():self.clear();return self.rejected()
        if self.audio is None:raise ValueError('fresh_utterance_required')
        context=self.context_factory()
        extra=self.extra_system_prompt
        if self.interruption_pending:
            extra=(extra+'\n' if extra else '')+INTERRUPTION_MARKER
            self.interruption_pending=False
        try:
            started=self.clock()
            notify(self.on_event,'identity_start')
            try:
                await self.complete(self.satellite_id,self.audio,self.voiced,text,
                    context_id=context.id,playback=self.playback_overlap(self.audio))
            except BaseException as exc:
                notify(self.on_event,'stage_error',stage='identity',error_type=type(exc).__name__,
                       duration_ms=round((self.clock()-started)*1000,1))
                raise
            finally:self.timings_ms['identity']=round((self.clock()-started)*1000,1)
            notify(self.on_event,'identity_end',duration_ms=self.timings_ms['identity'])
            if not self.allowed():return self.rejected()
            started=self.clock()
            notify(self.on_event,'agent_start')
            try:
                result=await self.converse(text=text,conversation_id=self.conversation_id,
                    device_id=self.device_id,satellite_id=self.satellite_id,context=context,
                    language=self.language,agent_id=self.agent_id,extra_system_prompt=extra)
            except BaseException as exc:
                notify(self.on_event,'stage_error',stage='agent',error_type=type(exc).__name__,
                       duration_ms=round((self.clock()-started)*1000,1))
                raise
            finally:self.timings_ms['agent']=round((self.clock()-started)*1000,1)
            if not self.allowed():return self.rejected()
            self.conversation_id=result.conversation_id
            self.last_response=response_facts(result.response)
            notify(self.on_event,'agent_end',duration_ms=self.timings_ms['agent'],
                   response_type=self.last_response['response_type'],continuing=result.continue_conversation is True)
            speech=((result.response.as_dict().get('speech') or {}).get('plain') or {}).get('speech') or ''
            return SimpleNamespace(speech=speech,continuing=result.continue_conversation is True)
        finally:self.clear()

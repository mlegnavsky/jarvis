"""Target-scoped local continuous capture with existing Jarvis voice authority."""
import asyncio
from dataclasses import asdict, replace
from datetime import timedelta
import hashlib
import json
from pathlib import Path
import time
from types import SimpleNamespace

import voluptuous as vol
from homeassistant.components import conversation, tts
from homeassistant.components.assist_pipeline.pipeline import (
    PipelineEvent, PipelineEventType, PipelineInput, async_get_pipeline,
)
from homeassistant.components.assist_pipeline.audio_enhancer import MicroVadSpeexEnhancer
from homeassistant.components.media_player import DATA_COMPONENT
from homeassistant.components.esphome.entry_data import build_device_unique_id
from homeassistant.components.tts.media_source import generate_media_source_id
from homeassistant.const import EVENT_CALL_SERVICE, EVENT_HOMEASSISTANT_STOP, __version__ as CORE_VERSION
from homeassistant.core import Context
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_interval
from homeassistant.helpers import entity_registry
from homeassistant.helpers.target import TargetSelection, async_extract_referenced_entity_ids
from homeassistant.util import dt as dt_util

from custom_components.extended_openai_conversation.dialogue import is_noise_transcript
from .tv_session import TVSession
from custom_components.jarvis_voice_diagnostics.turn_taking import spoken_name
from .adapter import DELEGATE, install, native_session
from .bridge import TurnBridge, response_facts
from .control import read_control
from .ha_io import (decode_reference, is_output_change, pcm_signal,
    prime_native_vad, reassert_output, recover_native_output, restart_allowed, restart_native)
from .session import Session
from .speech_file import SpeechFiles, create_owned_file, release_prepared
from .homepod_io import HOME, HomePodNotReady, HomePodOutput, homepod_state, homepod_timing, play_homepod_file, prime_homepod

DOMAIN='jarvis_local_duplex'
VERSION='1.2.0'
PIPELINE='01kw4sat65taw1y72xzrv2xyj4'
SATELLITE='assist_satellite.home_assistant_voice_0a8bde_assist_satellite'
PLAYER='media_player.home_assistant_voice_0a8bde_media_player'
MUTE='switch.home_assistant_voice_0a8bde_mute'
TELEVISION='media_player.obyvaci_pokoj_obyvaci_pokoj'
AGENT='conversation.extended_openai_conversation'
CONFIG_SCHEMA=vol.Schema({vol.Optional(DOMAIN):vol.Schema({vol.Optional('enabled',default=True):bool})},extra=vol.ALLOW_EXTRA)


def pipeline_signature(pipeline):
    return hashlib.sha256(json.dumps([pipeline.tts_engine,pipeline.tts_language,pipeline.tts_voice]).encode()).hexdigest()


class LocalDialogue:
    def __init__(self,hass):
        self.hass=hass;self.active=None;self.output=None;self.active_run=None
        self.root=Path(hass.config.path('jarvis_workspace','local_duplex'))
        self.lock=asyncio.Lock();self.save_lock=asyncio.Lock();self.probing=False
        self.source_revision=None
        self.speech_files=None
        self.homepod_init_task=None
        self.homepod_initializing=False
        self.report={'runtime_version':VERSION,'core_version':CORE_VERSION,'mode':'local_microphone_homepod_speech',
            'speaker':HOME,'microphone':SATELLITE,'volume_policy':'homepod_raop_only_tv_pause_separate','cloud_audio':'completed_utterances_only',
            'raw_microphone_saved':False,'acoustic_acceptance_verified':False,
            'firmware_changed':False,'sessions':0,'last_session':None,'self_test':{'status':'not_run'},
            'homepod_startup':{'status':'pending','policy':'startup45_once_then_current_volume'}}

    def player(self):
        component=self.hass.data.get(DATA_COMPONENT)
        return component.get_entity(PLAYER) if component else None

    def homepod(self):
        component=self.hass.data.get(DATA_COMPONENT)
        return component.get_entity(HOME) if component else None

    def speech_ready(self):
        player=self.homepod()
        return bool(player and player.available and getattr(player,'atv',None)
            and self.report['homepod_startup']['status']=='applied')

    def schedule_homepod_initialization(self):
        player=self.homepod()
        if (self.report['homepod_startup']['status']=='pending' and player and player.available
                and not self.homepod_initializing
                and (self.homepod_init_task is None or self.homepod_init_task.done())):
            self.homepod_initializing=True
            try:self.homepod_init_task=self.hass.async_create_task(self.initialize_homepod())
            except BaseException:self.homepod_initializing=False;raise

    async def initialize_homepod(self):
        self.report['homepod_startup']={'status':'running','policy':'startup45_once_then_current_volume'}
        try:self.report['homepod_startup']=await prime_homepod(self.homepod())
        except HomePodNotReady as exc:
            self.report['homepod_startup']={'status':'pending','error':type(exc).__name__,
                'policy':'startup45_once_then_current_volume'}
        except Exception as exc:
            self.report['homepod_startup']={'status':'failed',
                'error':type(exc).__name__,'policy':'startup45_once_then_current_volume'}
        finally:
            try:await self.save()
            finally:self.homepod_initializing=False

    async def ensure_homepod_initialized(self):
        self.schedule_homepod_initialization()
        if self.homepod_init_task is not None and not self.homepod_init_task.done():
            await asyncio.shield(self.homepod_init_task)
        return self.report['homepod_startup']['status']=='applied'

    def homepod_audio_state(self,player):
        if self.report['homepod_startup']['status']!='applied':raise ValueError('homepod_not_initialized')
        return homepod_state(player)

    def make_output(self,pipeline):
        return HomePodOutput(self.homepod,lambda text:self.synthesize(text,pipeline),
            play_homepod_file,self.homepod_audio_state,homepod_timing)

    def television(self):
        def read_tv():
            state=self.hass.states.get(TELEVISION)
            return state.as_dict() if state else None
        async def tv_call(service):
            await self.hass.services.async_call('media_player',service,{'entity_id':TELEVISION},blocking=True)
        return TVSession(read_tv,tv_call)

    def ready(self):
        player=self.player();speaker=self.hass.data.get('jarvis_speaker_identity')
        return bool(player and player.available and hasattr(player,'_client') and hasattr(player,'_key')
            and speaker and speaker.enforce and speaker.public_controls)

    async def synthesize(self,text,pipeline):
        options={tts.ATTR_PREFERRED_FORMAT:'wav',tts.ATTR_PREFERRED_SAMPLE_RATE:16000,
            tts.ATTR_PREFERRED_SAMPLE_CHANNELS:1,tts.ATTR_PREFERRED_SAMPLE_BYTES:2}
        if pipeline.tts_voice is not None:options[tts.ATTR_VOICE]=pipeline.tts_voice
        media_id=generate_media_source_id(self.hass,spoken_name(text),
            engine=pipeline.tts_engine,language=pipeline.tts_language,options=options,cache=True)
        _extension,data=await tts.async_get_media_source_audio(self.hass,media_id)
        pcm=decode_reference(data)
        signal=await self.hass.async_add_executor_job(pcm_signal,pcm)
        self.report['last_tts_signal']=signal
        if signal['silent']:raise ValueError('tts_reference_is_silent')
        if self.speech_files is None:
            media_root=self.hass.config.media_dirs.get('local')
            if not media_root:raise ValueError('local_media_directory_required')
            self.speech_files=SpeechFiles(media_root)
        prepared=await create_owned_file(self.hass.async_add_executor_job,self.speech_files,pcm)
        prepared.pcm=pcm;prepared.signal=signal
        return prepared

    def output_changed(self,event):
        return is_output_change(event.data,HOME,
            lambda data:async_extract_referenced_entity_ids(self.hass,TargetSelection(data)))

    async def handle(self,value):
        if self.probing:
            async def maintenance(_value):return None
            return await native_session(value,maintenance)
        await self.ensure_homepod_initialized()
        async with self.lock:
            proof=self.report['self_test']
            if not self.ready() or proof.get('status')!='passed' or proof.get('pipeline_signature')!=pipeline_signature(value.run.pipeline):
                async def unavailable(_value):return None
                return await native_session(value,unavailable)
            return await native_session(value,self.dialogue)

    async def dialogue(self,value):
        hass=self.hass;run=value.run
        mute=hass.states.get(MUTE)
        if mute is None or mute.state!='off':return
        if getattr(run.intent_agent,'id',None)!=AGENT:
            raise ValueError('voice_authorized_agent_required')
        pipeline=run.pipeline
        async def transcribe(pcm):
            from homeassistant.components.stt import SpeechResultState
            async def chunks():
                for offset in range(0,len(pcm),3200):yield pcm[offset:offset+3200]
            result=await run.stt_provider.async_process_audio_stream(value.stt_metadata,chunks())
            if result.result!=SpeechResultState.SUCCESS:raise ValueError('stt_failed')
            text=str(result.text or '').strip()
            return '' if is_noise_transcript(text) else text
        async def converse(**kwargs):
            guards=hass.data.setdefault('jarvis_voice_input_guards',{})
            key=kwargs['context'].id
            guards[key]=input_allowed
            try:return await conversation.async_converse(hass,**kwargs)
            finally:
                if guards.get(key) is input_allowed:guards.pop(key,None)
        television=self.television()
        output=self.make_output(pipeline)
        def input_allowed():return not session.done and not session.closed and television.input_safe()
        def overlap(audio):return output.last_overlap_at is not None and time.monotonic()-output.last_overlap_at<len(audio)/32000+1
        bridge=TurnBridge(transcribe,hass.data['jarvis_speaker_identity'].complete,converse,
            context_factory=lambda:Context(parent_id=run.context.id),device_id=value.device_id,
            satellite_id=value.satellite_id,conversation_id=value.session.conversation_id,
            agent_id=AGENT,language=pipeline.stt_language or run.language,
            extra_system_prompt=value.conversation_extra_system_prompt,playback_overlap=overlap,
            transcript_filter=lambda text,audio,at:'' if output.is_own_transcript(text,audio,at) else text,
            input_allowed=input_allowed)
        session=Session(transcribe=bridge.transcribe,respond=bridge.respond,play=output.play,stop=output.stop,
            gate=output.gate,silence_seconds=run.audio_settings.silence_seconds,on_interrupt=bridge.interrupted,
            playback_active=output.playing,on_capture=bridge.set_capture_time)
        self.active=session;self.output=output;self.active_run=str(run.id);self.report['sessions']+=1
        async def changed(event):
            state=event.data.get('new_state')
            if event.data['entity_id']==MUTE and (state is None or state.state!='off'):
                session.request_close('microphone_muted')
            elif event.data['entity_id']==TELEVISION:
                owned=television.snapshot()['owned']
                television.observe(state.as_dict() if state else None)
                if not television.input_safe():session.request_close('television_audible')
                elif owned and not television.snapshot()['owned']:session.request_close('television_changed')
        def service_called(event):
            if self.output_changed(event):
                output.disown();television.abandon();session.request_close('speaker_changed_externally')
        unsubscribe=async_track_state_change_event(hass,[MUTE,TELEVISION],changed)
        unsubscribe_service=hass.bus.async_listen(EVENT_CALL_SERVICE,service_called)
        try:
            await television.acquire()
            if not television.input_safe():session.request_close('television_not_quiet')
            if session.done:return
            if not run.audio_settings.is_vad_enabled:
                run.audio_settings=replace(run.audio_settings,is_vad_enabled=True)
                run.audio_enhancer=MicroVadSpeexEnhancer(run.audio_settings.auto_gain_dbfs,
                    run.audio_settings.noise_suppression_level,True)
            prime_native_vad(run.audio_enhancer)
            run.process_event(PipelineEvent(PipelineEventType.STT_START,{
                'engine':pipeline.stt_engine,'metadata':asdict(value.stt_metadata),
                'audio_processing':asdict(run.stt_provider.audio_processing)}))
            await self.save()
            await session.run(run.process_enhance_audio(value.stt_stream))
        finally:
            unsubscribe();unsubscribe_service()
            try:await session.close()
            finally:
                bridge.clear()
                await television.release()
                self.report['last_session']={'run_id':str(run.id),**session.snapshot(),
                    'output':output.snapshot(),'television':television.snapshot(),
                    'agent_response':bridge.last_response,'input_blocked':bridge.input_blocked}
                self.active=None;self.output=None;self.active_run=None
                await self.save()

    async def probe(self):
        if self.probing:return
        self.probing=True
        prepared=None
        self.report['self_test']={'status':'running','scope':'native_VAD_and_TTS_reference_no_playback'}
        try:
            enhancer=MicroVadSpeexEnhancer(0,0,True)
            warmup_frames,probability=prime_native_vad(enhancer)
            pipeline=async_get_pipeline(self.hass,PIPELINE)
            async with asyncio.timeout(30):prepared=await self.synthesize('Zkouška hlasu na HomePodu.',pipeline)
            self.report['self_test']={'status':'passed','scope':'native_VAD_and_TTS_reference_no_playback',
                'native_vad_probability':probability,'native_vad_warmup_frames':warmup_frames,
                'reference_seconds':len(prepared.pcm)/32000,'reference_signal':prepared.signal,
                'microphone_opened':False,'audible_playback':False,'source_revision':self.source_revision,
                'pipeline_signature':pipeline_signature(pipeline)}
        except Exception as exc:
            self.report['self_test']={'status':'failed','error':type(exc).__name__,
                'microphone_opened':False,'audible_playback':False}
        finally:
            try:
                if prepared is not None:await release_prepared(prepared)
            finally:
                self.probing=False
                await self.save()

    async def audio_recover(self):
        if self.probing:return
        self.probing=True
        self.report['audio_recovery']={'status':'running','microphone_opened':False}
        try:
            registry=entity_registry.async_get(self.hass)
            def restart(player):
                restart_native(player,allowed=lambda info:restart_allowed(registry,player,info,build_device_unique_id))
            if self.active:self.active.request_close('software_audio_recovery')
            async with asyncio.timeout(85):
                async with self.lock:
                    await self.save()
                    self.report['audio_recovery']=await recover_native_output(self.player,restart,reassert_output)
        except Exception as exc:
            self.report['audio_recovery']={'status':'failed','error':type(exc).__name__,
                'reason':str(exc) if str(exc) in ('restart_disabled_by_user','exact_restart_button_unavailable',
                    'native_connection_mismatch','idle_speaker_required','restart_disconnect_unobserved',
                    'restart_reconnect_unobserved','fresh_output_settings_required') else 'native_audio_recovery_failed',
                'microphone_opened':False}
        finally:
            self.probing=False
            await self.save()

    async def voice_agent_probe(self):
        if self.active or self.probing:
            self.report['voice_agent_probe']={'status':'busy','microphone_opened':False};return
        self.probing=True
        self.report['voice_agent_probe']={'status':'running','microphone_opened':False}
        try:
            async with self.lock:
                async with asyncio.timeout(65):
                    result=await conversation.async_converse(self.hass,
                        text='Vyprávěj krátký příběh ve dvou větách.',conversation_id=None,
                        context=Context(),device_id=None,satellite_id=SATELLITE,
                        language='cs',agent_id=AGENT)
            facts=response_facts(result.response)
            self.report['voice_agent_probe']={'status':'failed' if facts['response_type']=='error' or not facts['speech_chars'] else 'passed',
                **facts,'microphone_opened':False,'audible_playback':False,
                'voice_identity_fabricated':False,'scope':'fixed_voice_scoped_story_no_actions'}
        except Exception as exc:
            self.report['voice_agent_probe']={'status':'failed','error':type(exc).__name__,'microphone_opened':False}
        finally:
            self.probing=False
            await self.save()

    async def output_test(self):
        if self.probing:
            self.report['output_test']={'status':'busy','microphone_opened':False,'speaker':HOME};return
        self.probing=True
        if self.active:self.active.request_close('operator_homepod_output_test')
        television=self.television()
        output=self.make_output(async_get_pipeline(self.hass,PIPELINE))
        def service_called(event):
            if self.output_changed(event):output.disown();television.abandon()
        unsubscribe=self.hass.bus.async_listen(EVENT_CALL_SERVICE,service_called)
        try:
            await self.ensure_homepod_initialized()
            async with asyncio.timeout(45):
                async with self.lock:
                    await television.acquire()
                    await output.play('Zkouška hlasu na HomePodu.')
            self.report['output_test']={'status':'passed' if output.completed==1 else 'skipped',
                'speaker':HOME,'microphone_opened':False,'native_playback':output.snapshot(),'audibility_confirmed':False}
        except Exception as exc:
            self.report['output_test']={'status':'failed','speaker':HOME,'error':type(exc).__name__,
                'microphone_opened':False,'native_playback':output.snapshot()}
        finally:
            unsubscribe()
            try:await output.stop()
            finally:
                await television.release()
                self.probing=False
                await self.save()

    async def audio_audit(self):
        # Retained control name now verifies the requested output, never Voice PE speech.
        await self.output_test()

    async def save(self,_now=None):
        if not self.probing and self.active is None:self.schedule_homepod_initialization()
        request=await self.hass.async_add_executor_job(read_control,self.root,
            self.report.get('last_control_nonce'),time.time())
        if request and not self.probing:
            self.report['last_control_nonce']=request['nonce']
            handler={'probe':self.probe,'output_test':self.output_test,
                'audio_recover':self.audio_recover,'voice_agent_probe':self.voice_agent_probe,
                'audio_audit':self.audio_audit}[request['action']]
            self.hass.async_create_task(handler())
        report=dict(self.report)
        report.update(updated_at=dt_util.utcnow().isoformat(),adapter=getattr(self,'adapter','starting'),
            status='configured' if self.ready() and self.speech_ready() and getattr(self,'adapter',None)=='active' else 'waiting_for_speaker',
            active_run=self.active_run,active=self.active.snapshot() if self.active else None,
            output=self.output.snapshot() if self.output else None)
        report['source_revision']=self.source_revision
        report['household_catalog']=self.hass.data.get('jarvis_household_catalog_summary')
        player=self.player()
        report['local_player']={'available':bool(player and player.available),
            'state':str(player.state) if player else None,'volume':player.volume_level if player else None,
            'muted':player.is_volume_muted if player else None}
        homepod=self.homepod()
        report['homepod_player']={'entity_id':HOME,'available':bool(homepod and homepod.available),
            'state':str(homepod.state) if homepod else None}
        self.hass.states.async_set('sensor.jarvis_prerusitelny_hlas',report['status'],
            {'friendly_name':'Jarvis · konverzace přes HomePod','version':VERSION,'speaker':HOME,
             'active':self.active is not None,'acoustic_acceptance_verified':False,
             'microphone_while_speaking':self.active.frames_during_output if self.active else None})
        def write():
            self.root.mkdir(parents=True,exist_ok=True,mode=0o700)
            path=self.root/'report.tmp';path.write_text(json.dumps(report,ensure_ascii=False,indent=2))
            path.chmod(0o600);path.replace(self.root/'report.json')
        async with self.save_lock:
            pending=self.hass.async_add_executor_job(write)
            try:await asyncio.shield(pending)
            except asyncio.CancelledError:
                await pending
                raise


async def async_setup(hass,config):
    if not config[DOMAIN]['enabled']:return True
    app=LocalDialogue(hass)
    def previous():
        source=hashlib.sha256(''.join(hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(Path(__file__).parent.glob('*.py')) if not p.name.startswith('test_')).encode()).hexdigest()
        try:
            path=app.root/'report.json'
            data=json.loads(path.read_text()) if path.stat().st_size<128*1024 else {}
        except (OSError,ValueError):data={}
        if not isinstance(data,dict):data={}
        return source,data
    app.source_revision,old=await hass.async_add_executor_job(previous)
    proof=old.get('self_test') or {}
    if not isinstance(proof,dict):proof={}
    if proof.get('source_revision')==app.source_revision and proof.get('status')=='passed':app.report['self_test']=proof
    app.report['last_control_nonce']=old.get('last_control_nonce')
    app.adapter=install(hass,PipelineInput,CORE_VERSION,PIPELINE,SATELLITE,app.handle,
        error_event=lambda error:PipelineEvent(PipelineEventType.ERROR,{
            'code':getattr(error,'code','local-voice-preparation-failed'),
            'message':getattr(error,'message','Voice provider preparation failed')}))
    hass.data[DOMAIN]=app
    async_track_time_interval(hass,app.save,timedelta(seconds=3))
    async def stopping(_event):
        if app.active:app.active.request_close('homeassistant_stopping')
    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP,stopping)
    await app.save()
    return True

"""Controlled STT tests and temporary, bounded local microphone diagnostics."""
import asyncio
from dataclasses import asdict
from datetime import timedelta
import json
from pathlib import Path
import time
import wave
import voluptuous as vol
from homeassistant.components import stt, tts
from homeassistant.components.assist_pipeline.const import DATA_CONFIG, CONF_DEBUG_RECORDING_DIR
from homeassistant.components.tts.media_source import generate_media_source_id
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.helpers.event import async_track_time_interval, async_track_state_change_event
from homeassistant.util import dt as dt_util
from .analysis import audio_metrics, summarize_run, word_error

DOMAIN='jarvis_voice_diagnostics'
CONFIG_SCHEMA=vol.Schema({vol.Optional(DOMAIN):vol.Schema({})},extra=vol.ALLOW_EXTRA)
ENGINES=('stt.faster_whisper','stt.speech_to_phrase','stt.openai_stt')
PHRASES=('Kolik je hodin?','Jaká je teplota v obýváku?','Zhasni v obýváku.')
PLAYER='media_player.home_assistant_voice_0a8bde_media_player'
SATELLITE='assist_satellite.home_assistant_voice_0a8bde_assist_satellite'

async def async_setup(hass, config):
    root=Path(hass.config.path('jarvis_workspace/voice_diagnostics'))
    capture=root/'capture'
    report={'version':1,'started_at':dt_util.utcnow().isoformat(),'self_test':{'status':'pending'},
            'runs':[],'audio':[],'playback':[],'status':'starting','capture_expires_at':None,'capture_deadline_scope':'New recordings disabled after 15 minutes; an active HA run may finish afterward (pipeline timeout up to 5 minutes).'}
    lock=asyncio.Lock()
    poll_lock=asyncio.Lock()
    save_lock=asyncio.Lock()
    seen_audio=set()
    playback_start=None
    capture_deadline=0
    previous_capture=None

    def save_sync(snapshot):
        root.mkdir(parents=True,exist_ok=True)
        temp=root/'report.tmp'
        temp.write_text(json.dumps(snapshot,ensure_ascii=False,indent=2),encoding='utf-8')
        temp.chmod(0o600)
        temp.replace(root/'report.json')

    async def save():
        snapshot=json.loads(json.dumps(report))
        async with save_lock:
            await hass.async_add_executor_job(save_sync,snapshot)
        test=report['self_test']
        hass.states.async_set('sensor.jarvis_hlas_diagnostika',report['status'],
            {'friendly_name':'Jarvis · diagnostika hlasu','self_test':test.get('status'),
             'capture_expires_at':report['capture_expires_at'],'last_run':report['runs'][-1] if report['runs'] else None,
             'last_audio':report['audio'][-1] if report['audio'] else None,
             'report':'jarvis_workspace/voice_diagnostics/report.json'})

    def audio_scan():
        output=[]
        if not capture.exists(): return output
        files=sorted((p for p in capture.rglob('*.wav') if not p.is_symlink()),key=lambda p:p.stat().st_mtime,reverse=True)
        total=0
        for index,path in enumerate(files):
            size=path.stat().st_size
            total+=size
            if index>=5 or total>10*1024*1024:
                path.unlink(missing_ok=True)
                continue
            # Native pipeline closes WAV at run-end. Ignore files still being written.
            if time.time()-path.stat().st_mtime<3 or str(path) in seen_audio: continue
            try:
                with wave.open(str(path),'rb') as wav:
                    if (wav.getframerate(),wav.getnchannels(),wav.getsampwidth())!=(16000,1,2):
                        raise ValueError('unsupported_audio_format')
                    total_frames=wav.getnframes()
                    pcm=wav.readframes(16000*20)
                result=audio_metrics(pcm,total_frames=total_frames)
                result.update(file=str(path.relative_to(root)),modified_at=dt_util.utc_from_timestamp(path.stat().st_mtime).isoformat())
                output.append(result)
                seen_audio.add(str(path))
            except (ValueError,EOFError,wave.Error,OSError):
                continue
        return output

    def arm_capture():
        nonlocal capture_deadline,previous_capture
        cfg=hass.data.get(DATA_CONFIG)
        if not isinstance(cfg,dict): return False
        if not capture_deadline:
            previous_capture=cfg.get(CONF_DEBUG_RECORDING_DIR)
        cfg[CONF_DEBUG_RECORDING_DIR]=str(capture)
        capture_deadline=time.monotonic()+900
        report['capture_expires_at']=(dt_util.utcnow()+timedelta(minutes=15)).isoformat()
        return True

    async def poll(_now=None):
        nonlocal capture_deadline
        if poll_lock.locked(): return
        async with poll_lock:
            try:
                data=hass.data.get('assist_pipeline')
                runs=[]
                for pipeline_id,debug in getattr(data,'pipeline_debug',{}).items():
                    for run_id,run in list(debug.items()):
                        summary=summarize_run(run_id,[asdict(e) for e in list(run.events)])
                        summary['pipeline_id']=pipeline_id
                        runs.append(summary)
                report['runs']=sorted(runs,key=lambda r:r['started_at'] or '')[-20:]
                if capture_deadline and time.monotonic()>=capture_deadline:
                    cfg=hass.data.get(DATA_CONFIG,{})
                    if cfg.get(CONF_DEBUG_RECORDING_DIR)==str(capture):
                        if previous_capture is None: cfg.pop(CONF_DEBUG_RECORDING_DIR,None)
                        else: cfg[CONF_DEBUG_RECORDING_DIR]=previous_capture
                    capture_deadline=0
                    report['capture_expires_at']=None
                report['audio']=(report['audio']+await hass.async_add_executor_job(audio_scan))[-5:]
                await save()
            except Exception as exc:
                report['monitor_error']=type(exc).__name__
                report['status']='diagnostic_error'
                await save()

    async def state_changed(event):
        nonlocal playback_start
        state=event.data.get('new_state')
        if state is None:return
        entry={'entity_id':state.entity_id,'state':state.state,'at':dt_util.utcnow().isoformat()}
        if state.entity_id==PLAYER:
            if state.state=='playing' and playback_start is None: playback_start=time.monotonic()
            elif state.state!='playing' and playback_start is not None:
                entry['observed_playback_s']=round(time.monotonic()-playback_start,3)
                playback_start=None
        report['playback']=(report['playback']+[entry])[-30:]

    async def transcribe(engine_id,pcm):
        provider=stt.async_get_speech_to_text_engine(hass,engine_id)
        if provider is None: return {'status':'unavailable','engine':engine_id}
        metadata=stt.SpeechMetadata(language='cs-CZ' if engine_id=='stt.openai_stt' else 'cs',format=stt.AudioFormats.WAV,codec=stt.AudioCodecs.PCM,
            bit_rate=stt.AudioBitRates.BITRATE_16,sample_rate=stt.AudioSampleRates.SAMPLERATE_16000,
            channel=stt.AudioChannels.CHANNEL_MONO)
        if not provider.check_metadata(metadata):return {'status':'unsupported_metadata','engine':engine_id}
        async def stream():
            for offset in range(0,len(pcm),3200):yield pcm[offset:offset+3200]
        start=time.monotonic()
        try:
            async with asyncio.timeout(60):
                result=await provider.async_process_audio_stream(metadata,stream())
            return {'status':('ok' if result.text and result.text.strip() else 'no_text') if result.result==stt.SpeechResultState.SUCCESS else 'failed',
                    'engine':engine_id,'duration_s':round(time.monotonic()-start,3),'text':str(result.text or '')[:500]}
        except Exception as exc:
            return {'status':'error','engine':engine_id,'duration_s':round(time.monotonic()-start,3),'error':type(exc).__name__}

    async def self_test(_call=None):
        if lock.locked():return
        async with lock:
            report['self_test']={'status':'running','started_at':dt_util.utcnow().isoformat(),'samples':[]}
            report['status']='testing'
            await save()
            try:
                for phrase in PHRASES:
                    sample={'expected':phrase,'source':'local Piper cs_CZ-jirka-medium; direct STT only; no command execution','results':[]}
                    report['self_test']['current_stage']='synthesis'
                    report['self_test']['current_phrase']=phrase
                    await save()
                    start=time.monotonic()
                    async with asyncio.timeout(60):
                        media=generate_media_source_id(hass,phrase,engine='tts.piper',language='cs_CZ',options={'voice':'cs_CZ-jirka-medium'},cache=False)
                        ext,audio=await tts.async_get_media_source_audio(hass,media)
                        if len(audio)>2*1024*1024: raise ValueError('tts_audio_too_large')
                        async def input_audio():yield audio
                        pcm=b''.join([chunk async for chunk in tts._async_convert_audio(hass,ext,input_audio(),'s16le',16000,1,2)])
                    sample['tts_voice']='cs_CZ-jirka-medium'
                    sample['tts_and_decode_s']=round(time.monotonic()-start,3)
                    sample['audio']=audio_metrics(pcm)
                    if sample['audio']['duration_s']>15: raise ValueError('test_audio_too_long')
                    for engine in ENGINES:
                        report['self_test']['current_stage']=engine
                        await save()
                        result=await transcribe(engine,pcm)
                        if result['status']=='ok':result['word_error_rate']=word_error(phrase,result['text'])
                        sample['results'].append(result)
                    report['self_test']['samples'].append(sample)
                    await save()
                report['self_test']['status']='complete'
                report['self_test']['current_stage']='complete'
                report['self_test']['all_exact']=all(r.get('word_error_rate')==0 for sample in report['self_test']['samples'] for r in sample['results'])
                report['status']='ready_for_microphone_test'
            except Exception as exc:
                report['self_test']['status']='error'
                report['self_test']['error']=type(exc).__name__
                report['status']='diagnostic_error'
            report['self_test']['finished_at']=dt_util.utcnow().isoformat()
            await poll()

    async def arm(_call=None):
        arm_capture()
        await save()
    hass.services.async_register(DOMAIN,'run_self_test',self_test,schema=vol.Schema({}))
    hass.services.async_register(DOMAIN,'arm_capture',arm,schema=vol.Schema({}))
    async_track_time_interval(hass,poll,timedelta(seconds=5))
    async_track_state_change_event(hass,[PLAYER,SATELLITE],state_changed)
    async def start(_event=None):
        arm_capture()
        report['status']='monitoring'
        await poll()
        await asyncio.sleep(30)
        await self_test()
    if hass.is_running:hass.async_create_task(start())
    else:hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED,start)
    await save()
    return True

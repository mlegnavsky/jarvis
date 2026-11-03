"""A single target's native microphone remains open for the local dialogue."""
import asyncio

DELEGATE=object()


def operator_installed(hass,input_class,operator_handle):
    proof=input_class.__dict__.get('_jarvis_local_duplex_proof')
    return bool(isinstance(proof,tuple) and len(proof)==3 and proof[0] is hass
        and proof[1] is input_class.execute and proof[2]==operator_handle)


def install(hass, input_class, core_version, pipeline_id, satellite_id, handle,error_event=None,operator_handle=None):
    if core_version!='2026.6.4':return 'unsupported_core'
    if '_jarvis_local_duplex' in input_class.__dict__:return 'already_installed'
    original=input_class.execute
    async def execute(value,validate=False):
        run=value.run
        matches=(run.hass is hass and run.pipeline.id==pipeline_id
                 and value.satellite_id==satellite_id and str(run.start_stage)=='stt'
                 and str(run.end_stage)=='tts'
                 and value.wake_word_phrase not in ('rozsviť','zhasni')
                 and not str(run.id).startswith('synthetic-')
                 and value.stt_stream is not None and value.stt_metadata is not None
                 and int(value.stt_metadata.sample_rate)==16000)
        # A reserved/isolated operator input must not reach Core's providers
        # even if the selected pipeline or its parameters changed in flight.
        if run.hass is hass and value.satellite_id==satellite_id and operator_handle is not None:
            result=await operator_handle(value)
            if result is not DELEGATE:return result
        if not matches:return await original(value,validate=validate)
        if validate:
            try:await value.validate()
            except BaseException as error:
                async def failed(_value):
                    if error_event is not None and not isinstance(error,asyncio.CancelledError):
                        run.process_event(error_event(error))
                await native_session(value,failed)
                raise
        result=await handle(value)
        if result is DELEGATE:return await original(value,validate=False)
        return result
    input_class.execute=execute
    input_class._jarvis_local_duplex=True
    input_class._jarvis_local_duplex_proof=(hass,execute,operator_handle)
    return 'active'


async def native_session(value,body,*,begin=None):
    run=value.run
    if run.tts_stream:
        run.tts_stream.delete();run.tts_stream=None
    run._jarvis_suppressed_activation=True
    try:
        if begin is None:
            run.start(conversation_id=value.session.conversation_id,
                      device_id=value.device_id,satellite_id=value.satellite_id)
        else:begin()
        return await body(value)
    finally:
        try:await run.end()
        finally:del run._jarvis_suppressed_activation

"""A single target's native microphone remains open for the local dialogue."""
import asyncio

DELEGATE=object()


def install(hass, input_class, core_version, pipeline_id, satellite_id, handle,error_event=None):
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
    return 'active'


async def native_session(value,body):
    run=value.run
    if run.tts_stream:
        run.tts_stream.delete();run.tts_stream=None
    run._jarvis_suppressed_activation=True
    try:
        run.start(conversation_id=value.session.conversation_id,
                  device_id=value.device_id,satellite_id=value.satellite_id)
        return await body(value)
    finally:
        try:await run.end()
        finally:del run._jarvis_suppressed_activation

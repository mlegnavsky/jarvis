import asyncio
import unittest
import ast
from pathlib import Path
from types import SimpleNamespace as NS
from bridge import TurnBridge
from session import Session


class RuntimeDiagnosticsTests(unittest.IsolatedAsyncioTestCase):
    def make_bridge(self, emit):
        async def stt(audio): return 'Rozsviť světlo'
        async def identity(*args, **kwargs): pass
        async def agent(**kwargs):
            return NS(conversation_id='next', continue_conversation=True,
                response=NS(as_dict=lambda:{'speech':{'plain':{'speech':'Soukromá odpověď'}}}))
        bridge=TurnBridge(stt,identity,agent,context_factory=lambda:NS(id='c'),
            device_id='d',satellite_id='s',conversation_id='c',agent_id='a',language='cs')
        bridge.on_event=emit
        return bridge

    async def test_actual_bridge_records_transcript_and_stage_boundaries(self):
        events=[];bridge=self.make_bridge(lambda event,**facts:events.append((event,facts)))
        text=await bridge.transcribe(b'PCM must not be saved',1,False)
        await bridge.respond(text)
        self.assertEqual([e[0] for e in events],['stt_start','stt_end','identity_start','identity_end','agent_start','agent_end'])
        self.assertEqual(events[1][1]['transcript'],'Rozsviť světlo')
        self.assertNotIn('PCM',str(events));self.assertNotIn('Soukromá',str(events))
        self.assertIn('duration_ms',events[1][1])

    async def test_empty_and_failed_stt_are_distinct(self):
        events=[];bridge=self.make_bridge(lambda event,**facts:events.append((event,facts)))
        async def empty(audio):return ''
        bridge.transcriber=empty
        self.assertEqual(await bridge.transcribe(b'x',1,False),'')
        self.assertEqual(events[-1][1]['outcome'],'empty')
        async def failure(audio):raise ValueError('private credential')
        bridge.transcriber=failure
        with self.assertRaises(ValueError):await bridge.transcribe(b'x',1,False)
        self.assertEqual(events[-1][0],'stage_error')
        self.assertEqual(events[-1][1]['error_type'],'ValueError')
        self.assertNotIn('credential',str(events))

    async def test_diagnostic_callback_failure_does_not_break_command(self):
        def fail(*args,**kwargs):raise RuntimeError('observer failed')
        bridge=self.make_bridge(fail)
        text=await bridge.transcribe(b'x',1,False)
        result=await bridge.respond(text)
        self.assertTrue(result.continuing)

    async def test_session_records_cancelled_provider_and_close_reason(self):
        events=[];started=asyncio.Event()
        async def stt(*a):started.set();await asyncio.Event().wait()
        async def noop(*a):pass
        s=Session(transcribe=stt,respond=noop,play=noop,stop=noop,
            on_event=lambda event,**facts:events.append((event,facts)))
        await s.submit(b'x',1,False);await started.wait()
        s.request_close('microphone_muted');await s.close()
        self.assertIn(('session_end',{'reason':'microphone_muted'}),events)
        self.assertTrue(any(e[0]=='turn_cancelled' for e in events))

    def test_trace_is_bounded_detached_and_does_not_guess_wake_word(self):
        from runtime_diagnostics import RuntimeTrace
        now=[10.];trace=RuntimeTrace('run',clock=lambda:now[0])
        for i in range(100):trace.emit('stt_end',transcript='x'*1000,duration_ms=1.)
        snap=trace.snapshot()
        self.assertEqual(len(snap['events']),48)
        self.assertEqual(len(snap['events'][-1]['transcript']),240)
        self.assertEqual(snap['dropped_events'],53)
        self.assertIsNone(snap['wake_word'])
        self.assertFalse(snap['raw_microphone_saved'])
        snap['events'].clear();self.assertEqual(len(trace.snapshot()['events']),48)

    async def test_identity_failure_is_not_misattributed_to_agent(self):
        events=[];bridge=self.make_bridge(lambda event,**facts:events.append((event,facts)))
        now=[0.];bridge.clock=lambda:now[0]
        async def fail(*a,**kw):now[0]+=1.25;raise LookupError('secret message')
        bridge.complete=fail
        text=await bridge.transcribe(b'x',1,False)
        with self.assertRaises(LookupError):await bridge.respond(text)
        self.assertEqual(events[-1][0],'stage_error')
        self.assertEqual(events[-1][1],{'stage':'identity','error_type':'LookupError','duration_ms':1250.})
        self.assertNotIn('agent_start',[e[0] for e in events])
        self.assertNotIn('secret',str(events))

    async def test_repeated_turns_have_fresh_stage_durations(self):
        events=[];bridge=self.make_bridge(lambda event,**facts:events.append((event,facts)))
        now=[0.];bridge.clock=lambda:now[0]
        async def transcribe(audio):now[0]+=len(audio);return audio.decode()
        bridge.transcriber=transcribe
        for audio in (b'a',b'bbb'):
            text=await bridge.transcribe(audio,1,False);await bridge.respond(text)
        stt=[facts for event,facts in events if event=='stt_end']
        self.assertEqual([f['duration_ms'] for f in stt],[1000.,3000.])
        self.assertEqual([f['transcript'] for f in stt],['a','bbb'])

    async def test_source_end_is_recorded_without_provider_calls(self):
        events=[]
        async def forbidden(*a):raise AssertionError('unexpected provider')
        async def stop():pass
        async def source():
            if False:yield None
        s=Session(transcribe=forbidden,respond=forbidden,play=forbidden,stop=stop,
            on_event=lambda event,**facts:events.append((event,facts)))
        await s.run(source())
        self.assertIn(('session_end',{'reason':'audio_source_ended'}),events)
        self.assertEqual(s.accepted_turns,0)

    def test_reported_native_wake_hint_is_recorded_without_acoustic_claim(self):
        from runtime_diagnostics import RuntimeTrace
        trace=RuntimeTrace('run',wake_word='Jarvis')
        self.assertEqual(trace.snapshot()['wake_word'],'Jarvis')
        self.assertFalse(trace.snapshot()['acoustic_verified'])

    async def test_production_dialogue_observer_failure_preserves_tv_and_cleanup(self):
        # Execute the actual dialogue method, not a reimplementation of its wiring.
        from half_duplex import HalfDuplexSession
        tree=ast.parse(Path(__file__).with_name('__init__.py').read_text())
        cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='LocalDialogue')
        method=next(n for n in cls.body if isinstance(n,ast.AsyncFunctionDef) and n.name=='dialogue')
        events=[]
        class BrokenTrace:
            def __init__(self,*a,**kw):pass
            def emit(self,*a,**kw):raise ValueError('observer failed')
        class TV:
            async def acquire(self):events.append('pause')
            async def release(self):events.append('resume')
            def input_safe(self):return True
            def snapshot(self):return {'owned':False}
        async def nothing(*a,**kw):pass
        class FakeSession:
            def __init__(self,**kw):self.done=False;self.segmenter=NS(silence_seconds=.7)
            async def run(self,source):events.append('dialogue')
            def enhanced_source(self,*a):return None
            async def close(self):events.append('close')
            def snapshot(self):return {}
        import runtime_diagnostics
        scope={'RuntimeTrace':BrokenTrace,'notify':runtime_diagnostics.notify,
            'TurnBridge':TurnBridge,'HalfDuplexSession':FakeSession,
            'MUTE':'mute','AGENT':'agent','SATELLITE':'sat','TELEVISION':'tv',
            'Context':NS,'prime_native_vad':lambda x:None,'PipelineEvent':lambda *a:None,
            'PipelineEventType':NS(STT_START='stt-start'),'asdict':lambda x:{},
            'async_track_state_change_event':lambda *a:lambda:None,'EVENT_CALL_SERVICE':'call'}
        exec(compile(ast.Module(body=[method],type_ignores=[]),'actual-dialogue','exec'),scope)
        output=NS(play=nothing,stop=nothing,playing=lambda:False,tail_until=0.,snapshot=lambda:{})
        hass=NS(states=NS(get=lambda x:NS(state='off')),data={'jarvis_speaker_identity':NS(complete=nothing)},
            bus=NS(async_listen=lambda *a:lambda:None))
        app=NS(hass=hass,runtime_traces=[],television=lambda:TV(),make_output=lambda p:output,
            report={'sessions':0},save=nothing,output_changed=lambda e:False)
        run=NS(id='run',intent_agent=NS(id='agent'),pipeline=NS(stt_engine='stt',stt_language='cs'),
            audio_settings=NS(silence_seconds=.7,is_vad_enabled=True),audio_enhancer=None,
            stt_provider=NS(audio_processing=None),process_event=lambda e:None,process_enhance_audio=None)
        value=NS(run=run,device_id='d',satellite_id='sat',session=NS(conversation_id='c'),
            conversation_extra_system_prompt=None,stt_metadata=None,stt_stream=None,wake_word_phrase='Jarvis')
        await scope['dialogue'](app,value)
        self.assertEqual(events,['pause','dialogue','close','resume'])
        self.assertIsNone(app.active);self.assertIsNone(app.output)


if __name__=='__main__':unittest.main()

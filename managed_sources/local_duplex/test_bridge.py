"""A continuous session still submits fresh PCM and normal voice authority."""
import importlib
from types import SimpleNamespace as NS
import unittest


class BridgeTests(unittest.IsolatedAsyncioTestCase):
    async def test_stage_timings_measure_real_awaits_without_speech_content(self):
        bridge=self.setup_bridge();clock=[0.];bridge.clock=lambda:clock[0]
        async def transcribe(audio):clock[0]+=1.;return 'dotaz'
        async def complete(*a,**kw):clock[0]+=.25
        async def converse(**kw):
            clock[0]+=2.
            return NS(conversation_id='c',continue_conversation=True,
                response=NS(as_dict=lambda:{'speech':{'plain':{'speech':'odpověď'}}}))
        bridge.transcriber=transcribe;bridge.complete=complete;bridge.converse=converse
        text=await bridge.transcribe(b'captured',1,False);await bridge.respond(text)
        self.assertEqual(bridge.timings_ms,{'stt':1000.,'identity':250.,'agent':2000.})

    async def test_tv_audible_before_or_during_stt_never_reaches_authority(self):
        bridge=self.setup_bridge();safe=[False];bridge.input_allowed=lambda:safe[0]
        self.assertEqual(await bridge.transcribe(b'captured',1,False),'')
        self.assertEqual(self.events,[])
        safe[0]=True
        async def transcribe(audio):safe[0]=False;return 'Zhasni'
        bridge.transcriber=transcribe
        self.assertEqual(await bridge.transcribe(b'captured',1,False),'')
        self.assertIsNone(bridge.audio);self.assertEqual(self.events,[])

    async def test_tv_resuming_during_identity_blocks_agent_and_actions(self):
        bridge=self.setup_bridge();safe=[True];bridge.input_allowed=lambda:safe[0]
        async def complete(*a,**kw):safe[0]=False
        bridge.complete=complete
        text=await bridge.transcribe(b'captured',1,False);result=await bridge.respond(text)
        self.assertEqual(result.speech,'');self.assertFalse(result.continuing)
        self.assertIsNone(self.kwargs);self.assertIsNone(bridge.audio)

    async def test_tv_resuming_while_agent_thinks_discards_its_speech(self):
        bridge=self.setup_bridge();safe=[True];bridge.input_allowed=lambda:safe[0]
        async def converse(**kw):
            safe[0]=False
            return NS(conversation_id='c',continue_conversation=True,
                      response=NS(as_dict=lambda:{'speech':{'plain':{'speech':'stale answer'}}}))
        bridge.converse=converse
        text=await bridge.transcribe(b'captured',1,False);result=await bridge.respond(text)
        self.assertEqual(result.speech,'');self.assertFalse(result.continuing)
    def test_response_error_facts_do_not_expose_message_or_credentials(self):
        module=importlib.import_module('bridge')
        response=NS(as_dict=lambda:{'response_type':'error','data':{'code':'unknown'},
            'speech':{'plain':{'speech':'PRIVATE api key sk-PRIVATE invalid temperature status 400'}}})
        facts=module.response_facts(response)
        self.assertEqual(facts['error_code'],'unknown')
        self.assertEqual(facts['parameter_hint'],'temperature')
        self.assertNotIn('PRIVATE',str(facts))

    def setup_bridge(self):
        module=importlib.import_module('bridge');self.events=[];self.kwargs=None
        context=NS(id='fresh-context')
        async def transcribe(audio):self.events.append(('stt',audio));return 'Zhasni'
        async def complete(*args,**kwargs):self.events.append(('identity',args,kwargs))
        async def converse(**kwargs):
            self.events.append(('agent',));self.kwargs=kwargs
            return NS(conversation_id='next',continue_conversation=False,response=NS(as_dict=lambda:{'speech':{'plain':{'speech':''}}}))
        return module.TurnBridge(transcribe,complete,converse,context_factory=lambda:context,
            device_id='device',satellite_id='satellite',conversation_id='first',
            agent_id='agent',language='cs-CZ',extra_system_prompt='existing',playback_overlap=lambda audio:True)

    async def test_fresh_pcm_context_and_source_reach_existing_agent(self):
        bridge=self.setup_bridge();text=await bridge.transcribe(b'captured',.2,False)
        result=await bridge.respond(text)
        identity=self.events[1]
        self.assertEqual(identity[1],('satellite',b'captured',.2,'Zhasni'))
        self.assertEqual(identity[2],{'context_id':'fresh-context','playback':True})
        self.assertEqual(self.kwargs['context'].id,'fresh-context')
        self.assertEqual(self.kwargs['device_id'],'device');self.assertEqual(self.kwargs['satellite_id'],'satellite')
        self.assertEqual(self.kwargs['conversation_id'],'first')
        self.assertEqual(bridge.conversation_id,'next')
        self.assertFalse(result.continuing);self.assertEqual(result.speech,'')
        self.assertIsNone(bridge.audio)

    async def test_interruption_adds_bounded_note_without_changing_command(self):
        bridge=self.setup_bridge();bridge.interrupted()
        text=await bridge.transcribe(b'captured',1,False);await bridge.respond(text)
        self.assertEqual(self.kwargs['text'],'Zhasni')
        self.assertIn('previous_answer_interrupted',self.kwargs['extra_system_prompt'])
        self.assertIn('existing',self.kwargs['extra_system_prompt'])

    async def test_missing_fresh_pcm_never_calls_agent(self):
        bridge=self.setup_bridge()
        with self.assertRaises(ValueError):await bridge.respond('Zhasni')
        self.assertIsNone(self.kwargs)

    async def test_own_question_filter_uses_capture_time_and_never_enters_agent(self):
        module=importlib.import_module('bridge');events=[];now=[12.]
        async def transcribe(audio):now[0]=40.;return 'Co pro tebe můžu udělat?'
        async def forbidden(*a,**kw):events.append('unexpected')
        observed=[]
        def reject(text,audio,captured_until):observed.append(captured_until);return ''
        bridge=module.TurnBridge(transcribe,forbidden,forbidden,context_factory=lambda:NS(id='c'),
            device_id='d',satellite_id='s',conversation_id='c',agent_id='a',language='cs',
            transcript_filter=reject,clock=lambda:now[0])
        self.assertEqual(await bridge.transcribe(b'captured',.8,False),'')
        self.assertEqual(observed,[12.]);self.assertIsNone(bridge.audio);self.assertEqual(events,[])

    async def test_real_session_cannot_answer_its_own_question_but_accepts_yes(self):
        import asyncio
        bridge_module=importlib.import_module('bridge');session_module=importlib.import_module('session')
        guard=importlib.import_module('text_echo').TextEcho()
        guard.remember('Chceš mi říct něco dalšího?',started_at=10,duration=3,tail=2)
        captured=['Chceš mi říct něco dalšího?'];calls=[]
        async def transcribe(audio):return captured[0]
        async def complete(*a,**kw):calls.append('identity')
        async def converse(**kw):
            calls.append(('agent',kw['text']))
            return NS(conversation_id='next',continue_conversation=True,
                response=NS(as_dict=lambda:{'speech':{'plain':{'speech':''}}}))
        bridge=bridge_module.TurnBridge(transcribe,complete,converse,context_factory=lambda:NS(id='c'),
            device_id='d',satellite_id='s',conversation_id='c',agent_id='a',language='cs',clock=lambda:12.,
            transcript_filter=lambda text,audio,at:'' if guard.matches(text,
                captured_from=at-len(audio)/32000,captured_until=at) else text)
        async def nothing(*a):return None
        session=session_module.Session(transcribe=bridge.transcribe,respond=bridge.respond,
            play=nothing,stop=nothing,clock=lambda:12.)
        await session.submit(bytes(32000),.8,False);await session.task
        self.assertEqual(calls,[]);self.assertEqual(session.completed_turns,0)
        captured[0]='Ano';await session.submit(bytes(32000),.8,False);await session.task
        self.assertEqual(calls,['identity',('agent','Ano')]);self.assertEqual(session.completed_turns,1)
        await session.close()

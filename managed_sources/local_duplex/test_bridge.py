"""A continuous session still submits fresh PCM and normal voice authority."""
import importlib
from types import SimpleNamespace as NS
import unittest


class BridgeTests(unittest.IsolatedAsyncioTestCase):
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

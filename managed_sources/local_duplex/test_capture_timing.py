"""Echo identity uses immutable capture time across cancellation and queues."""
import asyncio
import importlib
from types import SimpleNamespace as NS
import unittest


class CaptureTimingTests(unittest.IsolatedAsyncioTestCase):
 async def exercise(self,mode,text):
  clock=[12.];calls=[];echo=importlib.import_module('text_echo').TextEcho()
  echo.remember('Co pro tebe můžu udělat?',started_at=10,duration=3,tail=.4)
  async def transcribe(audio):return text
  async def complete(*a,**kw):calls.append('identity')
  async def converse(**kw):
   calls.append('agent')
   return NS(conversation_id='c',continue_conversation=True,
       response=NS(as_dict=lambda:{'speech':{'plain':{'speech':''}}}))
  bridge=importlib.import_module('bridge').TurnBridge(transcribe,complete,converse,
   context_factory=lambda:NS(id='c'),device_id='d',satellite_id='s',conversation_id='c',
   agent_id='a',language='cs',clock=lambda:clock[0],
   transcript_filter=lambda value,audio,at:'' if echo.matches(value,
       captured_from=at-len(audio)/32000,captured_until=at) else value)
  async def nothing(*a):pass
  session=importlib.import_module('session').Session(transcribe=bridge.transcribe,
       respond=bridge.respond,play=nothing,stop=nothing,clock=lambda:clock[0])
  session.on_capture=lambda ended:setattr(bridge,'capture_ended_at',ended)
  if mode=='interruption':
   async def cleanup():clock[0]=14.5
   session.interrupt_task=asyncio.create_task(cleanup())
   await session.submit(bytes(32000),.8,False);await session.task
  else:
   event=asyncio.Event();busy=asyncio.create_task(event.wait());session.task=busy
   session.stage='thinking';await session.submit(bytes(32000),.8,False)
   clock[0]=14.5;event.set();await busy
   async def frames():
    for _ in range(20):
     yield NS(audio=bytes(320),speech_probability=0.)
     await asyncio.sleep(0)
   await session.run(frames())
  await session.close();return calls

 async def test_own_echo_survives_interruption_cleanup_delay(self):
  self.assertEqual(await self.exercise('interruption','Co pro tebe můžu udělat?'),[])

 async def test_own_echo_survives_deferred_turn_delay(self):
  self.assertEqual(await self.exercise('deferred','Co pro tebe můžu udělat?'),[])

 async def test_real_yes_after_cleanup_remains_a_user_turn(self):
  self.assertEqual(await self.exercise('interruption','Ano'),['identity','agent'])

 async def test_real_yes_after_deferral_remains_a_user_turn(self):
  self.assertEqual(await self.exercise('deferred','Ano'),['identity','agent'])

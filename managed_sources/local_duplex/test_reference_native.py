import importlib
import json
import unittest
from types import SimpleNamespace as NS
try:
    module=importlib.import_module('reference_native')
except ModuleNotFoundError:
    module=None

class Client:
    connected_address='192.0.2.10'
    api_version=(1,14)
    def __init__(self):self.calls=[];self.response={'status':json.dumps(dict(schema=1,boot_id=9,generation=1,state=0,fault=0,clock_us=100,physical_stopped=True,buffer_empty=True,stream_open=False,acoustic_verified=False,receiver_timing_verified=False))}
    async def execute_service(self,service,data,**kw):
        self.calls.append((service.name,data,kw));return NS(success=True,response_data=json.dumps(self.response).encode())

class NativeReferenceTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.assertIsNotNone(module,'native reference API adapter missing')
        self.client=Client()
        expected={'jarvis_reference_status':{},'jarvis_reference_pairing':{},
            'jarvis_reference_arm':{'generation':1,'owner':3,'duration_ms':1},
            'jarvis_reference_cancel':{'generation':1}}
        services={i:NS(name=k,key=i,supports_response=2,args=[NS(name=n,type=t) for n,t in v.items()]) for i,(k,v) in enumerate(expected.items())}
        self.entry=NS(client=self.client,services=services,available=True,device_info=NS(mac_address='84:f7:03:0a:8b:de'))
        self.player=NS(entity_id=module.TARGET,_client=self.client,_entry_data=self.entry,available=True)
        self.link=module.NativeReferenceEndpoint(self.player,encrypted=True)
    async def test_public_45_api_shape_and_response_used(self):
        status=await self.link.status();self.assertEqual(status['generation'],1)
        name,data,kw=self.client.calls[0]
        self.assertEqual(name,'jarvis_reference_status');self.assertEqual(data,{})
        self.assertIs(kw['return_response'],True)
    async def test_requires_exact_device_and_encrypted_connection(self):
        with self.assertRaises(ValueError):module.NativeReferenceEndpoint(self.player,encrypted=False)
        self.player.entity_id='media_player.other'
        with self.assertRaises(ValueError):module.NativeReferenceEndpoint(self.player,encrypted=True)
    async def test_replaced_client_and_disconnected_address_rejected_before_write(self):
        self.entry.client=Client()
        with self.assertRaises(ValueError):await self.link.cancel(1)
        self.entry.client=self.client;self.client.connected_address=None
        with self.assertRaises(ValueError):await self.link.cancel(1)
        self.assertEqual(self.client.calls,[])
    async def test_service_schema_must_match_not_just_name(self):
        service=next(s for s in self.entry.services.values() if s.name=='jarvis_reference_cancel')
        service.args[0].type=3
        with self.assertRaises(ValueError):await self.link.cancel(1)
        self.assertEqual(self.client.calls,[])
    async def test_arm_and_cancel_cannot_take_arbitrary_parameters(self):
        for gen in (0,-1,True,2**31,'1'):
            with self.assertRaises(ValueError):await self.link.cancel(gen)
        for duration in (0,245001,True):
            with self.assertRaises(ValueError):await self.link.arm(1,'A'*43,duration)
        self.assertEqual(self.client.calls,[])
    async def test_bad_or_oversized_response_is_not_echoed(self):
        self.client.response={'status':'PRIVATE\n'*1000}
        with self.assertRaises(ValueError) as exc:await self.link.status()
        self.assertNotIn('PRIVATE',str(exc.exception))

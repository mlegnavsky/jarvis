"""Four exact native actions on the configured Voice PE; aioesphomeapi45.3.1."""
import ipaddress
import json
import re

TARGET='media_player.home_assistant_voice_0a8bde_media_player'
SCHEMAS={'status':{},'pairing':{},'arm':{'generation':1,'owner':3,'duration_ms':1},
         'cancel':{'generation':1}}
INT_FIELDS=('schema','boot_id','generation','state','fault','clock_us','submitted_frames',
            'dma_frames','last_dma_us','nonzero_frames','first_signal_dma_us')
BOOL_FIELDS=('muted','physical_stopped','buffer_empty','stream_open',
             'receiver_timing_verified','acoustic_verified')


class NativeReferenceEndpoint:
    def __init__(self, player, *, encrypted):
        if (encrypted is not True or getattr(player,'entity_id',None)!=TARGET or
                not getattr(player,'available',False)):
            raise ValueError('fixed_encrypted_reference_endpoint_required')
        self.player=player;self.entry=player._entry_data;self.client=player._client
        self.mac=self.entry.device_info.mac_address
        raw=self.client.connected_address
        address=ipaddress.ip_address(raw)
        if not (address.is_private or address.is_link_local) or address.is_unspecified or address.is_multicast:
            raise ValueError('local_native_endpoint_required')
        self.address=raw
        literal=str(address).replace('%','%25')
        self.url=f'ws://[{literal}]:8927/sendspin' if address.version==6 else f'ws://{literal}:8927/sendspin'
        self.check()

    def check(self):
        if (self.player.entity_id!=TARGET or self.player._entry_data is not self.entry or
                self.player._client is not self.client or self.entry.client is not self.client or
                not self.player.available or not self.entry.available or
                self.entry.device_info.mac_address!=self.mac or
                self.client.connected_address!=self.address or self.client.api_version is None):
            raise ValueError('reference_native_connection_changed')

    async def invoke(self, action, data):
        self.check()
        if action not in SCHEMAS or set(data)!=set(SCHEMAS[action]):
            raise ValueError('reference_native_action_invalid')
        services=[s for s in self.entry.services.values() if s.name=='jarvis_reference_'+action]
        if len(services)!=1:raise ValueError('reference_native_action_unavailable')
        service=services[0]
        if (service.supports_response!=2 or len(service.args)!=len(SCHEMAS[action]) or
                {a.name:a.type for a in service.args}!=SCHEMAS[action]):
            raise ValueError('reference_native_action_schema_changed')
        response=await self.client.execute_service(service,data,return_response=True,timeout=1)
        self.check()
        if (response is None or response.success is not True or
                not isinstance(response.response_data,bytes) or len(response.response_data)>4096):
            raise ValueError('reference_native_response_invalid')
        try:
            value=json.loads(response.response_data)
            if not isinstance(value,dict):raise ValueError()
            return value
        except (ValueError,TypeError):raise ValueError('reference_native_response_invalid') from None

    async def status(self):
        response=await self.invoke('status',{})
        try:
            data=json.loads(response['status'])
            if not isinstance(data,dict):raise ValueError()
            if (data['schema']!=1 or any(type(data[k]) is not int or data[k]<0 for k in
                    ('boot_id','generation','state','fault','clock_us')) or
                    any(type(data[k]) is not bool for k in ('physical_stopped','buffer_empty','stream_open')) or
                    data.get('receiver_timing_verified') is not False or data.get('acoustic_verified') is not False):
                raise ValueError()
            result={k:v for k in INT_FIELDS if type(v:=data.get(k)) is int and 0<=v<2**63}
            result.update({k:v for k in BOOL_FIELDS if type(v:=data.get(k)) is bool})
            return result
        except (ValueError,KeyError,TypeError):raise ValueError('reference_native_status_invalid') from None

    @staticmethod
    def generation(value):
        if type(value) is not int or not 0<value<2**31:
            raise ValueError('reference_generation_invalid')

    async def arm(self, generation, owner, duration_ms):
        self.generation(generation)
        if (not isinstance(owner,str) or not re.fullmatch(r'[A-Za-z0-9_-]{43}',owner) or
                type(duration_ms) is not int or not 0<duration_ms<=245000):
            raise ValueError('reference_arm_invalid')
        return await self.invoke('arm',dict(generation=generation,owner=owner,duration_ms=duration_ms))

    async def cancel(self, generation):
        self.generation(generation)
        return await self.invoke('cancel',{'generation':generation})

    async def pairing_token(self):
        value=(await self.invoke('pairing',{})).get('pairing_token')
        if not isinstance(value,str) or not 20<len(value)<512:
            raise ValueError('reference_pairing_unavailable')
        return value  # Private caller only: never include this in reports/errors.

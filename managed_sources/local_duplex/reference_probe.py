"""Bounded generated-only test of the silent digital reference endpoint.

No HomePod, microphone, ASR, conversation model or household command is invoked.
Native endpoint and Sendspin must independently agree on ownership and stopping.
"""
import asyncio
import contextlib
from importlib.metadata import version
import math
import os
from pathlib import Path
import stat
import struct
import uuid

if __package__:
    from .reference_timing import ClockBounds, TimedPCM
    from .reference_tap import ReferenceQueue
    from .reference_writer import ReferenceWriter, stop_reference
else:
    from reference_timing import ClockBounds, TimedPCM
    from reference_tap import ReferenceQueue
    from reference_writer import ReferenceWriter, stop_reference


def private_dir(root):
    root=Path(root);directory=root/'reference-private'
    if root.is_symlink() or directory.is_symlink():raise ValueError('reference_secret_path_invalid')
    directory.mkdir(mode=0o700,parents=True,exist_ok=True)
    directory.chmod(0o700)
    return directory


def private_key(root):
    directory=private_dir(root);path=directory/'identity.key'
    if not path.exists() and not path.is_symlink():
        try:
            fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
        except FileExistsError:pass
        else:
            with os.fdopen(fd,'wb') as target:
                target.write(os.urandom(32));target.flush();os.fsync(target.fileno())
    if path.is_symlink() or not stat.S_ISREG(path.stat().st_mode):
        raise ValueError('reference_secret_path_invalid')
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
    with os.fdopen(fd,'rb') as source: data=source.read(33)
    if len(data)!=32:raise ValueError('reference_identity_invalid')
    return data


def public_identity(root):
    """Provision locally; return only the stable public ID for firmware pinning."""
    from aiosendspin.noise.keys import Identity
    if version('aiosendspin')!='10.3.0':raise ValueError('reference_sendspin_version_changed')
    return Identity.from_private_bytes(private_key(root)).peer_id


def pin_peer(root, peer):
    path=private_dir(root)/'peer.id'
    if path.is_symlink():raise ValueError('reference_peer_path_invalid')
    try:fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    except FileExistsError:
        if not path.is_file() or path.stat().st_size>64 or path.read_text()!=peer:
            raise ValueError('reference_peer_identity_changed')
    else:
        with os.fdopen(fd,'w') as target:
            target.write(peer);target.flush();os.fsync(target.fileno())


def client_ready(client, peer):
    return bool(client and client.client_id==peer and client.is_connected and
                client.is_paired and client.available and client.role('player@v1') is not None)


def generated_pcm(start):
    # Fixed 700Hz, about -21dBFS peak, stereo S16BE. Never persisted.
    values=[]
    for i in range(start,start+352):
        value=round(2800*math.sin(2*math.pi*700*i/44100))
        values.extend((value,value))
    return struct.pack('!704h',*values)


def check_health(status, boot, generation):
    if (status.get('schema')!=1 or status.get('boot_id')!=boot or
            status.get('generation')!=generation or status.get('state') not in (1,2) or
            status.get('fault')!=0 or status.get('muted') is not True):
        raise ValueError('reference_endpoint_health_failed')


class GeneratedReferenceProbe:
    def __init__(self, endpoint, root, executor):
        self.endpoint=endpoint;self.root=Path(root);self.executor=executor
        self.server=None;self.client=None;self.peer=None
        self.report={'status':'running','stage':'preflight','microphone_opened':False,
            'homepod_playback':False,'acoustic_verified':False,'receiver_timing_verified':False,
            'scope':'generated_only_silent_electrical_endpoint','generations':[]}

    async def run(self):
        from aiosendspin.server import SendspinServer
        from aiosendspin.noise.keys import Identity
        from aiosendspin.noise.pairing_token import decode_psk_token
        from aiosendspin.noise.pairing import PairingAttempt
        from aiosendspin.noise.trust_store import FileServerPairingStore
        from aiosendspin.models.types import PairMethod, AudioCodec
        from aiosendspin.audio.format import AudioFormat
        if version('aiosendspin')!='10.3.0':raise ValueError('reference_sendspin_version_changed')
        try:
            async with asyncio.timeout(25):
                initial=await self.endpoint.status()
                if not (initial['state']==0 and initial['physical_stopped'] and
                        initial['buffer_empty'] and not initial['stream_open']):
                    raise ValueError('reference_endpoint_busy')
                # Native API is the authenticated side channel; token is never logged.
                self.report['stage']='pairing'
                token=decode_psk_token(await self.endpoint.pairing_token())
                self.peer=token.client_id
                await self.executor(pin_peer,self.root,self.peer)
                identity=Identity.from_private_bytes(await self.executor(private_key,self.root))
                directory=await self.executor(private_dir,self.root)
                path=directory/'pairings.json'
                if path.is_symlink():raise ValueError('reference_pairing_path_invalid')
                store=await FileServerPairingStore.open(path)
                attempt=None
                if await store.record_by_client_id(self.peer) is None:
                    attempt=PairingAttempt(method=PairMethod.PAIRING_PSK,
                        pairing_psk=token.pairing_psk,client_id=self.peer,owner='jarvis-silent-reference')
                self.server=SendspinServer(asyncio.get_running_loop(),identity,'Jarvis silent reference',
                    pairing_store=store,allow_unencrypted=False)
                # No listener/discovery is started. Dial one native-authenticated address.
                await self.server.connect_to_client_and_wait(self.endpoint.url,
                    retry_initial_connection=False,pairing_attempt=attempt)
                async with asyncio.timeout(8):
                    while not client_ready(self.server.get_client(self.peer),self.peer):await asyncio.sleep(.05)
                self.client=self.server.get_client(self.peer)
                if self.client.group.clients!=[self.client] or self.client.group.has_active_stream:
                    raise ValueError('reference_group_busy')
                role=self.client.role('player@v1')
                fmt=AudioFormat(sample_rate=48000,bit_depth=16,channels=2,sample_type='int')
                if not role.set_preferred_format(fmt,AudioCodec.PCM):raise ValueError('reference_format_unavailable')
                # Warm AV outside the first timestamped commit's 200ms budget.
                await self.executor(__import__,'av')
                self.report['stage']='clock_sync'
                # Firmware refuses arming until the paired client's sync is fresh.
                # Wait for standard protocol clock exchanges, without starting audio.
                await asyncio.sleep(1)
                for interrupted in (True,False):
                    result=await self.phase(role,interrupted=interrupted)
                    self.report['generations'].append(result)
                self.report.update(status='passed',stage='stopped_and_empty',
                    electrical_output_observed=True,authenticated_long_term_noise=True)
        except BaseException as exc:
            self.report.update(status='failed',error=type(exc).__name__)
            raise
        finally:
            if self.server is not None:
                try:
                    async with asyncio.timeout(3):await self.server.close()
                except BaseException as exc:
                    self.report.update(status='failed',close_error=type(exc).__name__)
        return dict(self.report)

    async def phase(self, role, *, interrupted):
        endpoint=self.endpoint;server=self.server;client=self.client;group=client.group
        initial=await endpoint.status();boot=initial['boot_id'];generation=initial['generation']+1
        if not (initial['state']==0 and initial['physical_stopped'] and initial['buffer_empty'] and not initial['stream_open']):
            raise ValueError('reference_endpoint_not_drained')
        def owned():return client_ready(client,self.peer) and client.group is group and group.clients==[client]
        if not owned() or group.has_active_stream:raise ValueError('reference_group_busy')
        self.report['stage']='arm'
        armed=await endpoint.arm(generation,server.id,12000)
        if armed.get('accepted') is not True:raise ValueError('reference_arm_not_accepted')
        push=None;queue=ReferenceQueue(max_packets=8);clock=server.clock;bounds=ClockBounds()
        latest={};max_rtt=0;result=None
        try:
            if not owned() or group.has_active_stream:raise ValueError('reference_group_changed')
            push=group.start_stream();push.set_live_source(True)
            nonce=uuid.uuid4().hex
            writer=ReferenceWriter(queue,push,role,clock,nonce,owned)
            base=clock.now_us()+1500000
            async def feed():
                for i in range(400 if interrupted else 251):
                    deadline=base+i*352*1000000//44100
                    await asyncio.sleep(max(0,(deadline-1500000-clock.now_us())/1e6))
                    packet=TimedPCM(nonce,i,i*352,deadline*1000,1000,generated_pcm(i*352))
                    queue.commit(queue.reserve(packet))
                queue.finish()
            async def health():
                nonlocal latest,max_rtt
                while True:
                    if not owned():raise ValueError('reference_connection_changed')
                    sent=clock.now_us()*1000;latest=await endpoint.status();received=clock.now_us()*1000
                    check_health(latest,boot,generation)
                    bounds.observe(str(boot),sent,latest['clock_us'],received)
                    bounds.to_device_us(received,now_ns=received)
                    max_rtt=max(max_rtt,(received-sent)//1000)
                    await asyncio.sleep(.35)
            self.report['stage']='cancel_during_signal' if interrupted else 'complete_signal'
            async with asyncio.TaskGroup() as tasks:
                producer=tasks.create_task(feed());consumer=tasks.create_task(writer.run())
                monitor=tasks.create_task(health())
                if interrupted:
                    await asyncio.sleep(2.5)
                    producer.cancel();consumer.cancel();queue.close('intentional_probe_cancel')
                else:
                    await consumer
                    await asyncio.sleep(max(0,(writer.last_end_ns/1000+100000-clock.now_us())/1e6))
                monitor.cancel()
            before_stop=await endpoint.status();check_health(before_stop,boot,generation)
            if before_stop.get('nonzero_frames',0)<=0 or before_stop.get('first_signal_dma_us',0)<=0:
                raise ValueError('reference_real_signal_dma_not_observed')
            result={'generation':generation,'interrupted':interrupted,
                'before_stop':before_stop,'clock_rtt_max_us':max_rtt,'queue_peak_bytes':queue.peak,
                'acoustic_verified':False}
            return result
        finally:
            queue.close('probe_finished')
            self.report['stage']='physical_stop'
            if push is not None:
                # The helper awaits the matching device boot/generation, empty I2S
                # output AND the ended Sendspin stream; clear alone is insufficient.
                cleanup=asyncio.create_task(stop_reference(push,group,endpoint,
                    generation=generation,boot_id=boot,owned=owned))
                try:ack=await asyncio.shield(cleanup)
                except asyncio.CancelledError:
                    await cleanup
                    raise
                self.report['last_stop_ack']=ack
                if result is not None:result['stop_ack']=ack
            else:
                await endpoint.cancel(generation)


def claim_probe(root, nonce, now):
    """Persist the fixed generated-only request before touching the endpoint."""
    import json
    import re
    if not isinstance(nonce,str) or not re.fullmatch(r'[a-f0-9]{32}',nonce):
        raise ValueError('reference_probe_nonce_invalid')
    root=Path(root);path=root/'reference-probe-state.json'
    if root.is_symlink() or path.is_symlink():raise ValueError('reference_probe_state_invalid')
    root.mkdir(parents=True,exist_ok=True)
    if path.exists():
        if not path.is_file() or path.stat().st_size>1024:raise ValueError('reference_probe_state_invalid')
        if json.loads(path.read_text()).get('nonce')==nonce:return False
    temp=root/'reference-probe-state.tmp'
    fd=os.open(temp,os.O_WRONLY|os.O_CREAT|os.O_TRUNC|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'w') as target:
        json.dump({'nonce':nonce,'consumed_at':now,'microphone_authorized':False},target)
        target.flush();os.fsync(target.fileno())
    temp.replace(path)
    return True

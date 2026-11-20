#!/usr/bin/env python3
"""One bounded integration run of repository modules; endpoint status is simulated."""
import asyncio, contextlib, hashlib, heapq, json, logging, os, shutil, sys, time, traceback
from pathlib import Path
from types import SimpleNamespace as NS
import numpy as np
from aiohttp import web
from aiosendspin.client import SendspinClient
from aiosendspin.clock import RawMonotonicClock
from aiosendspin.models.player import ClientHelloPlayerSupport, SupportedAudioFormat
from aiosendspin.models.types import AudioCodec, Roles
from aiosendspin.noise.keys import Identity, generate_psk, psk_id_for
from aiosendspin.noise.pairing_token import PSKPairingToken, encode_psk_token
from aiosendspin.noise.trust_store import InMemoryClientPairingStore, PairingPsk, ClientPairingConfig

ROOT=Path(__file__).resolve().parent
SOURCE=Path("/workspace/scratch/698c1908029a/jarvis-echo-measurement/managed_sources/local_duplex")
sys.path.insert(0,str(SOURCE))
from reference_probe import GeneratedReferenceProbe
from reference_native import NativeReferenceEndpoint, TARGET, SCHEMAS
CLOCK=RawMonotonicClock()
FILES=("reference_probe.py","reference_writer.py","reference_native.py","reference_timing.py","reference_tap.py")
R={"scope":"actual repository probe/writer/native adapter plus official encrypted Sendspin loopback",
   "endpoint_native_api_simulated":True,"endpoint_counters_and_stop_ack_simulated":True,
   "physical_electrical_proof":False,"acoustic_proof":False,"audio_device_opened":False,
   "house_calls":0,"input_rate":44100,"advertised_output_rate":48000,
   "source_sha256":{n:hashlib.sha256((SOURCE/n).read_bytes()).hexdigest() for n in FILES},
   "audio_chunks":0,"audio_frames":0,"sink_queue_limit":96,"sink_queue_peak":0,
   "server_queue_peak":0,"stream_starts":0,"stream_ends":0,"clear_callbacks":0,
   "cancel_calls":[],"arm_calls":[],"native_actions":{},"formats":[],
   "timestamp_continuity_error_max_us":0,"late_chunks":0,"violations":[]}
def audit(event,args):
    if event in ("socket.bind","socket.connect"):
        address=args[1]
        if isinstance(address,tuple) and address[0] not in ("127.0.0.1","::1"):
            raise RuntimeError("non_loopback_refused")
    elif event=="open" and isinstance(args[0],str) and args[0].startswith(("/dev/snd","/dev/audio","/dev/dsp")):
        raise RuntimeError("audio_device_refused")
sys.addaudithook(audit)

class SimulatedNativeClient:
    connected_address="127.0.0.1"
    api_version=NS(major=1,minor=13)
    def __init__(self,client,token):
        self.client=client;self.token=token;self.generation=0;self.state=0;self.stream_open=False
        self.submitted=0;self.dma=0;self.nonzero=0;self.first_signal=0;self.last_dma=0
        self.queue=[];self.running=True;self.last_end=None;self.snippet=[]
    def status(self):
        return dict(schema=1,boot_id=417,generation=self.generation,state=self.state,fault=0,
            clock_us=CLOCK.now_us(),submitted_frames=self.submitted,dma_frames=self.dma,
            last_dma_us=self.last_dma,nonzero_frames=self.nonzero,first_signal_dma_us=self.first_signal,
            muted=True,physical_stopped=self.state==0,buffer_empty=not self.queue,
            stream_open=self.stream_open,receiver_timing_verified=False,acoustic_verified=False)
    async def execute_service(self,service,data,return_response,timeout):
        assert return_response is True and timeout==1
        action=service.name.removeprefix("jarvis_reference_")
        R["native_actions"][action]=R["native_actions"].get(action,0)+1
        if action=="status":out={"status":json.dumps(self.status())}
        elif action=="pairing":out={"pairing_token":self.token}
        elif action=="arm":
            accepted=(self.state==0 and not self.queue and not self.stream_open and
                data["generation"]==self.generation+1 and self.client.is_time_synchronized() and
                self.client.server_info is not None and data["owner"]==self.client.server_info.server_id)
            if accepted:
                self.generation=data["generation"];self.state=1;self.submitted=self.dma=self.nonzero=0
                self.first_signal=self.last_dma=0;self.last_end=None
                R["arm_calls"].append(self.generation)
            out={"accepted":accepted}
        elif action=="cancel":
            accepted=data["generation"]==self.generation
            if accepted:
                self.state=0;self.queue.clear();R["cancel_calls"].append(self.generation)
            out={"accepted":accepted}
        else:raise AssertionError("unknown_native_action")
        return NS(success=True,response_data=json.dumps(out).encode())
    def start(self,message):
        self.stream_open=True;R["stream_starts"]+=1
    def end(self,roles):
        self.stream_open=False;R["stream_ends"]+=1
    def clear(self,roles):
        R["clear_callbacks"]+=1
    def audio(self,ts,data,fmt,send_ahead):
        spec=(fmt.codec.value,fmt.pcm_format.sample_rate,fmt.pcm_format.channels,fmt.pcm_format.bit_depth)
        if list(spec) not in R["formats"]:R["formats"].append(list(spec))
        if spec!=("pcm",48000,2,16):
            R["violations"].append("unexpected_output_format");return
        n=len(data)//4
        if self.last_end is not None:
            R["timestamp_continuity_error_max_us"]=max(R["timestamp_continuity_error_max_us"],abs(ts-self.last_end))
        self.last_end=ts+n*1000000//48000
        play=self.client.compute_play_time(ts)
        if play<=CLOCK.now_us():R["late_chunks"]+=1
        if len(self.queue)>=96:
            R["violations"].append("simulated_sink_overflow");return
        if self.state==0:
            R["violations"].append("audio_after_simulated_stop");return
        values=np.frombuffer(data,dtype="<i2").reshape(-1,2)
        if not np.array_equal(values[:,0],values[:,1]):R["violations"].append("stereo_mismatch")
        if len(self.snippet)<4800:self.snippet.extend(values[:4800-len(self.snippet),0].tolist())
        nonzero=int(np.count_nonzero(values[:,0]))
        heapq.heappush(self.queue,(play,self.generation,n,nonzero))
        self.submitted+=n;R["audio_frames"]+=n;R["audio_chunks"]+=1
        R["sink_queue_peak"]=max(R["sink_queue_peak"],len(self.queue))
    async def schedule(self):
        while self.running:
            now=CLOCK.now_us()
            while self.queue and self.queue[0][0]<=now:
                _,gen,n,nonzero=heapq.heappop(self.queue)
                if gen!=self.generation or self.state==0:
                    R["violations"].append("stale_simulated_output");continue
                self.state=2;self.dma+=n;self.nonzero+=nonzero;self.last_dma=now
                if nonzero and not self.first_signal:self.first_signal=now
            await asyncio.sleep(.001)

async def main():
    with (ROOT/"attempt-started.json").open("x") as out:json.dump({"created_unix_ns":time.time_ns()},out)
    logging.basicConfig(level=logging.WARNING,filename=ROOT/"library.log")
    key=generate_psk();identity=Identity.generate();store=InMemoryClientPairingStore()
    await store.store_pairing_config(ClientPairingConfig(dynamic_pairing_code_enabled=False,unpaired_access_enabled=False))
    await store.set_pairing_psk(PairingPsk(psk_id_for(key),key))
    client=SendspinClient(identity,"Simulated reference endpoint",[Roles.PLAYER],pairing_store=store,
        clock=CLOCK,required_lead_time_ms=100,min_buffer_ms=100,state_supported_commands=[],
        player_support=ClientHelloPlayerSupport([SupportedAudioFormat(AudioCodec.PCM,2,48000,16)],524288))
    native=SimulatedNativeClient(client,encode_psk_token(PSKPairingToken(identity.peer_id,key)))
    services={name:NS(name="jarvis_reference_"+name,supports_response=2,
        args=[NS(name=k,type=v) for k,v in args.items()]) for name,args in SCHEMAS.items()}
    entry=NS(client=native,available=True,device_info=NS(mac_address="00:00:00:00:00:01"),services=services)
    player=NS(entity_id=TARGET,available=True,_entry_data=entry,_client=native)
    endpoint=NativeReferenceEndpoint(player,encrypted=True)
    async def handle(request):
        ws=web.WebSocketResponse();await ws.prepare(request)
        await client.attach_websocket(ws)
        return ws
    app=web.Application();app.router.add_get("/sendspin",handle)
    runner=web.AppRunner(app);await runner.setup()
    site=web.TCPSite(runner,"127.0.0.1",8927);await site.start()
    client.add_stream_start_listener(native.start);client.add_stream_end_listener(native.end)
    client.add_stream_clear_listener(native.clear);client.add_audio_chunk_listener(native.audio)
    scheduler=asyncio.create_task(native.schedule())
    async def executor(fn,*args):return await asyncio.to_thread(fn,*args)
    probe=GeneratedReferenceProbe(endpoint,ROOT/"probe-state",executor)
    started=time.monotonic()
    try:
        async with asyncio.timeout(30):
            raw=await probe.run()
        R["elapsed_s"]=time.monotonic()-started
        # These probe claims came from the SIMULATED native counters/ACK, not I2S.
        R["raw_probe_report_simulated_endpoint"]=raw
        R["probe_electrical_claim_is_simulated_only"]=raw.get("electrical_output_observed") is True
        R["noise_authenticated"]=raw.get("authenticated_long_term_noise") is True
        R["probe_queue_peaks_bytes"]=[g["queue_peak_bytes"] for g in raw["generations"]]
        R["taskgroup_children_remaining"]=[t.get_coro().__qualname__ for t in asyncio.all_tasks()
            if not t.done() and any(x in t.get_coro().__qualname__ for x in ("GeneratedReferenceProbe.phase.<locals>","ReferenceWriter.run"))]
        snippet=np.asarray(native.snippet,dtype=float)
        spectrum=np.abs(np.fft.rfft(snippet*np.hanning(len(snippet))))
        R["received_tone_frequency_hz"]=float(np.argmax(spectrum)*48000/len(snippet))
        R["received_tone_rms_s16"]=float(np.sqrt(np.mean(snippet**2)))
        R["native_final_state"]=native.status()
        R["source_unchanged"]={n:hashlib.sha256((SOURCE/n).read_bytes()).hexdigest()==R["source_sha256"][n] for n in FILES}
        assert raw["status"]=="passed"
        assert R["arm_calls"]==[1,2] and R["cancel_calls"]==[1,2]
        assert R["stream_starts"]==2 and R["stream_ends"]==2
        assert R["formats"]==[["pcm",48000,2,16]]
        assert abs(R["received_tone_frequency_hz"]-700)<=10
        assert 1500<R["received_tone_rms_s16"]<2300
        assert R["timestamp_continuity_error_max_us"]<=2
        assert R["late_chunks"]==0 and not R["violations"]
        assert max(R["probe_queue_peaks_bytes"])<=8*1408
        assert not R["taskgroup_children_remaining"]
        assert all(R["source_unchanged"].values())
        R["pass"]=True
    finally:
        R["elapsed_s"]=time.monotonic()-started
        if "raw_probe_report_simulated_endpoint" not in R:R["raw_probe_report_simulated_endpoint"]=dict(probe.report)
        native.running=False;scheduler.cancel();await asyncio.gather(scheduler,return_exceptions=True)
        await client.disconnect();await runner.cleanup()
        # Remove only this attempt's generated identities/pairings; never include keys in evidence.
        if (ROOT/"probe-state").exists():shutil.rmtree(ROOT/"probe-state")
if __name__=="__main__":
    try:asyncio.run(main())
    except BaseException as exc:
        R["pass"]=False;R["exception_type"]=type(exc).__name__;R["exception"]=str(exc)
        (ROOT/"exception.txt").write_text(traceback.format_exc())
    finally:
        (ROOT/"results.json").write_text(json.dumps(R,indent=2,sort_keys=True)+"\n")
        print(json.dumps({"pass":R.get("pass"),"elapsed_s":R.get("elapsed_s"),"exception":R.get("exception_type"),
            "violations":R["violations"],"chunks":R["audio_chunks"],"formats":R["formats"]}))
    raise SystemExit(0 if R.get("pass") else 1)


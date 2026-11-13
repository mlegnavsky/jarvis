#!/usr/bin/env python3
"""One real-time 240 s official Sendspin loopback transport experiment. No audio output."""
from __future__ import annotations
import asyncio, contextlib, hashlib, heapq, importlib.metadata, json, logging, os, platform, sys, time, traceback
from pathlib import Path
import numpy as np
import av  # Warm the officially-required codec dependency before the timed stream.
from aiohttp import web
from aiosendspin.client import SendspinClient
from aiosendspin.clock import RawMonotonicClock
from aiosendspin.models.player import ClientHelloPlayerSupport, SupportedAudioFormat
from aiosendspin.models.types import AudioCodec, Roles, PairMethod
from aiosendspin.noise.keys import Identity, generate_psk, psk_id_for
from aiosendspin.noise.pairing import PairingAttempt
from aiosendspin.noise.trust_store import InMemoryClientPairingStore, InMemoryServerPairingStore, PairingPsk, ClientPairingConfig
from aiosendspin.server import SendspinServer, AudioFormat

ROOT=Path(__file__).resolve().parent
DURATION_US=240_000_000
RATE=44100
CHANNELS=2
BLOCK=352
LEAD_US=1_500_000
IN_QUEUE_MAX=8
SINK_QUEUE_MAX=96
CLOCK=RawMonotonicClock()
REPORT={"experiment":"official Sendspin encrypted loopback transport only","duration_requested_s":240,
        "acoustic_proof":False,"audio_device_opened":False,"house_calls":0,"attempt":1,
        "signal":"authored deterministic voiced/syllabic PCM, 20 s signal / 10 s silence",
        "format":{"sample_rate":RATE,"channels":CHANNELS,"bits":16,"endian":"little"},
        "input_block_frames":BLOCK,"explicit_lead_us":LEAD_US,
        "python":platform.python_version(),"machine":platform.machine(),
        "versions":{p:importlib.metadata.version(p) for p in ("aiosendspin","av","numpy","pillow")},
        "violations":[],"socket_binds":0,"socket_connects":0,
        "input_queue_limit":IN_QUEUE_MAX,"sink_queue_limit":SINK_QUEUE_MAX,
        "input_queue_peak":0,"sink_queue_peak":0,"server_queue_peak":0,
        "received_chunks":0,"received_frames":0,"rendered_chunks":0,"rendered_frames":0,
        "clear_events":0,"end_events":0,"start_events":0,"cancelled_queued_frames":0,
        "stale_received_frames":0,"stale_rendered_frames":0,"pcm_mismatch_frames":0,
        "timestamp_error_max_us":0,"noncontiguous_chunks":0,"late_receive_chunks":0,
        "deadline_miss_over_50ms":0,"input_deadline_lead_min_us":10**12,
        "received_silence_frames":0,"received_signal_frames":0,"cancellations":0}
def audit(event,args):
    if event in ("socket.bind","socket.connect"):
        address=args[1]
        if isinstance(address,tuple) and address[0] not in ("127.0.0.1","::1"):
            raise RuntimeError("Non-loopback socket refused")
        REPORT["socket_binds" if event=="socket.bind" else "socket_connects"]+=1
    elif event=="open" and isinstance(args[0],str) and args[0].startswith(("/dev/snd","/dev/audio","/dev/dsp")):
        raise RuntimeError("Audio-device open refused")
sys.addaudithook(audit)

def violation(reason):
    if reason not in REPORT["violations"]: REPORT["violations"].append(reason)
def pcm(gen,start,count):
    # Integral sample generation is independent of input/output packet boundaries.
    i=np.arange(start,start+count,dtype=np.int64)
    phase=(i*(113+17*gen))%RATE
    triangle=10000-np.abs(phase*40000//RATE-20000)
    envelope=((i//2205)%4+1)
    val=(triangle*envelope//4).astype(np.int16)
    val[((i//RATE)%30)>=20]=0
    stereo=np.empty((count,2),dtype="<i2")
    stereo[:,0]=val
    stereo[:,1]=-val
    return stereo.tobytes()
async def until(deadline):
    while (remaining:=deadline-CLOCK.now_us())>0:
        await asyncio.sleep(remaining/1_000_000)

async def main():
    # Exclusive marker prevents accidentally repeating the experiment.
    with (ROOT/"attempt-started.json").open("x") as f:
        json.dump({"attempt":1,"created_unix_ns":time.time_ns()},f)
    logging.basicConfig(level=logging.WARNING,filename=ROOT/"library.log")
    loop=asyncio.get_running_loop()
    server_identity,client_identity=Identity.generate(),Identity.generate()
    cstore,sstore=InMemoryClientPairingStore(),InMemoryServerPairingStore()
    await cstore.store_pairing_config(ClientPairingConfig(dynamic_pairing_code_enabled=False,
         static_pairing_code_enabled=False,unpaired_access_enabled=False))
    pairing_psk=generate_psk()
    await cstore.set_pairing_psk(PairingPsk(psk_id=psk_id_for(pairing_psk),psk=pairing_psk))
    client=SendspinClient(client_identity,"Transport simulation sink",[Roles.PLAYER],
        pairing_store=cstore,clock=CLOCK,required_lead_time_ms=150,min_buffer_ms=100,
        state_supported_commands=[],player_support=ClientHelloPlayerSupport(
            supported_formats=[SupportedAudioFormat(codec=AudioCodec.PCM,channels=2,sample_rate=RATE,bit_depth=16)],
            buffer_capacity=524288))
    server=SendspinServer(loop,server_identity,"Transport simulation source",
        pairing_store=sstore,allow_unencrypted=False,allow_noncompliant_clients=False,clock=CLOCK)
    async def handler(request):
        ws=web.WebSocketResponse()
        await ws.prepare(request)
        await client.attach_websocket(ws,expected_server_id=server_identity.peer_id)
        return ws
    app=web.Application(); app.router.add_get("/sendspin",handler)
    runner=web.AppRunner(app); await runner.setup()
    site=web.TCPSite(runner,"127.0.0.1",0); await site.start()
    port=runner.addresses[0][1]
    sink=[]
    bases={}
    sent_frames={}
    next_frame={}
    current={"generation":0,"requested_generation":0,"done":False}
    receive_lead=[]; render_late=[]; clock_error=[]
    digest=hashlib.sha256()
    tasks=[]
    def flush_sink(kind):
        REPORT[kind]+=1
        REPORT["cancelled_queued_frames"]+=sum(row[3] for row in sink)
        sink.clear()
        current["generation"]=current["requested_generation"]
    def on_start(message):
        REPORT["start_events"]+=1
        current["generation"]=current["requested_generation"]
    def on_audio(ts,data,fmt,send_ahead):
        now=CLOCK.now_us()
        candidates=[g for g,b in bases.items() if b<=ts]
        if not candidates:
            violation("timestamp_before_any_generation"); return
        gen=max(candidates)
        n=len(data)//4
        frame=round((ts-bases[gen])*RATE/1_000_000)
        expected_ts=bases[gen]+frame*1_000_000//RATE
        REPORT["timestamp_error_max_us"]=max(REPORT["timestamp_error_max_us"],abs(ts-expected_ts))
        if abs(ts-expected_ts)>2: violation("timestamp_error_over_2us")
        if frame!=next_frame.get(gen,0):
            REPORT["noncontiguous_chunks"]+=1; violation("noncontiguous_PCM")
        next_frame[gen]=frame+n
        valid=max(0,min(n,sent_frames.get(gen,0)-frame))
        expected=pcm(gen,frame,valid)+bytes((n-valid)*4)
        if data!=expected:
            REPORT["pcm_mismatch_frames"]+=n; violation("PCM_mismatch")
        if gen<current["generation"]:
            REPORT["stale_received_frames"]+=n; violation("stale_receive_after_clear")
        play=client.compute_play_time(ts)
        clock_error.append(play-ts)
        receive_lead.append(play-now)
        if play<=now:
            REPORT["late_receive_chunks"]+=1; violation("late_receive")
        REPORT["received_chunks"]+=1; REPORT["received_frames"]+=n
        nonzero=int(np.count_nonzero(np.frombuffer(data,dtype="<i2")[::2]))
        REPORT["received_signal_frames"]+=nonzero
        REPORT["received_silence_frames"]+=n-nonzero
        digest.update(data)
        if len(sink)>=SINK_QUEUE_MAX:
            violation("sink_queue_overflow"); return
        heapq.heappush(sink,(play,ts,gen,n))
        REPORT["sink_queue_peak"]=max(REPORT["sink_queue_peak"],len(sink))
    client.add_stream_start_listener(on_start)
    client.add_stream_clear_listener(lambda roles:flush_sink("clear_events"))
    client.add_stream_end_listener(lambda roles:flush_sink("end_events"))
    client.add_audio_chunk_listener(on_audio)
    client.add_disconnect_listener(lambda: violation("unexpected_disconnect") if not current["done"] else None)
    try:
        attempt=PairingAttempt(method=PairMethod.PAIRING_PSK,pairing_psk=pairing_psk,client_id=client_identity.peer_id,owner="generated-only-simulation")
        await server.connect_to_client_and_wait(f"ws://127.0.0.1:{port}/sendspin",pairing_attempt=attempt)
        async with asyncio.timeout(20):
            while True:
                peer=server.get_client(client_identity.peer_id)
                if peer and peer.is_connected and peer.is_paired and peer.available and client.is_time_synchronized(): break
                await asyncio.sleep(.02)
        assert peer.connection and peer.connection.is_encrypted
        assert await sstore.record_by_client_id(client_identity.peer_id) is not None
        REPORT["authenticated_long_term_noise"]=True
        REPORT["time_synchronized_at_start"]=client.is_time_synchronized()
        role=peer.role("player@v1")
        fmt=AudioFormat(sample_rate=RATE,bit_depth=16,channels=2)
        assert role and role.set_preferred_format(fmt,AudioCodec.PCM)
        group=peer.group
        assert group.clients==[peer] and not group.has_active_stream
        start=CLOCK.now_us(); end=start+DURATION_US
        REPORT["measurement_start_unix_ns"]=time.time_ns()
        print(json.dumps({"event":"measurement_started","duration_s":240,"noise_long_term":True,"loopback_only":True}),flush=True)
        async def render():
            next_heartbeat=start+30_000_000
            while CLOCK.now_us()<end:
                now=CLOCK.now_us()
                while sink and sink[0][0]<=now:
                    play,ts,gen,n=heapq.heappop(sink)
                    if gen!=current["generation"]:
                        REPORT["stale_rendered_frames"]+=n; violation("stale_render")
                    late=now-play; render_late.append(late)
                    if late>50_000:
                        REPORT["deadline_miss_over_50ms"]+=1; violation("scheduler_late_over_50ms")
                    REPORT["rendered_chunks"]+=1; REPORT["rendered_frames"]+=n
                if peer.connection:
                    REPORT["server_queue_peak"]=max(REPORT["server_queue_peak"],peer.connection.queue_status()[0])
                if not peer.is_connected or not peer.is_paired or not peer.available or not client.is_time_synchronized():
                    violation("readiness_lost")
                if now>=next_heartbeat:
                    print(json.dumps({"event":"progress","elapsed_s":round((now-start)/1e6,2),"chunks":REPORT["received_chunks"],"violations":len(REPORT["violations"])}),flush=True)
                    next_heartbeat+=30_000_000
                await asyncio.sleep(.001)
        renderer=asyncio.create_task(render()); tasks.append(renderer)
        for gen in range(4):
            segment_start=start+gen*60_000_000
            segment_end=start+(gen+1)*60_000_000
            await until(segment_start)
            current["requested_generation"]=gen
            bases[gen]=CLOCK.now_us()+LEAD_US
            sent_frames[gen]=0
            q=asyncio.Queue(maxsize=IN_QUEUE_MAX)
            push=group.start_stream(); push.set_live_source(True)
            async def produce(g=gen,base=bases[gen],queue=q):
                frame=0
                while True:
                    await until(base-LEAD_US+frame*1_000_000//RATE)
                    block=pcm(g,frame,BLOCK)
                    try: queue.put_nowait((frame,block))
                    except asyncio.QueueFull: violation("input_queue_overflow"); return
                    REPORT["input_queue_peak"]=max(REPORT["input_queue_peak"],queue.qsize())
                    frame+=BLOCK
            async def consume(g=gen,base=bases[gen],queue=q,owned=push):
                while True:
                    frame,block=await queue.get()
                    deadline=base+frame*1_000_000//RATE
                    lead=deadline-CLOCK.now_us()
                    REPORT["input_deadline_lead_min_us"]=min(REPORT["input_deadline_lead_min_us"],lead)
                    if lead<250_000: violation("insufficient_producer_lead")
                    sent_frames[g]=frame+BLOCK
                    owned.prepare_audio(block,fmt)
                    actual=await owned.commit_audio(play_start_us=deadline)
                    if actual!=deadline: violation("commit_timestamp_rebased")
                    queue.task_done()
            producer=asyncio.create_task(produce()); consumer=asyncio.create_task(consume())
            tasks.extend((producer,consumer))
            finish=segment_end if gen<3 else end-LEAD_US-100_000
            await until(finish)
            producer.cancel()
            await asyncio.gather(producer,return_exceptions=True)
            await q.join()
            consumer.cancel()
            await asyncio.gather(consumer,return_exceptions=True)
            if gen<3:
                current["requested_generation"]=gen+1
                push.clear()
                await group.stop()
                REPORT["cancellations"]+=1
            else:
                await push.flush_audio()
                await until(end)
                await renderer
                current["done"]=True
                await group.stop()
        REPORT["measurement_elapsed_s"]=(CLOCK.now_us()-start)/1_000_000
        REPORT["received_pcm_sha256"]=digest.hexdigest()
        REPORT["generated_frames_by_generation"]=sent_frames
        REPORT["received_frames_by_generation"]=next_frame
        def summary(values):
            return {"count":len(values),"min":min(values),"max":max(values),
                    "p50":float(np.percentile(values,50)),"p95":float(np.percentile(values,95)),
                    "p99":float(np.percentile(values,99))} if values else {}
        REPORT["receive_lead_us"]=summary(receive_lead)
        REPORT["simulated_scheduler_lateness_us"]=summary(render_late)
        REPORT["client_to_server_clock_mapping_error_us"]=summary(clock_error)
        REPORT["pass"]=not REPORT["violations"] and REPORT["cancellations"]==3 and REPORT["clear_events"]>=3 and REPORT["received_chunks"]>9000
    finally:
        current["done"]=True
        for task in tasks: task.cancel()
        await asyncio.gather(*tasks,return_exceptions=True)
        await client.disconnect()
        await server.close()
        await runner.cleanup()

if __name__=="__main__":
    try: asyncio.run(main())
    except BaseException as exc:
        REPORT["pass"]=False
        REPORT["exception_type"]=type(exc).__name__
        REPORT["exception"]=str(exc)
        (ROOT/"exception.txt").write_text(traceback.format_exc())
    finally:
        REPORT["finished_unix_ns"]=time.time_ns()
        (ROOT/"results.json").write_text(json.dumps(REPORT,indent=2,sort_keys=True)+"\n")
        print(json.dumps({"event":"measurement_finished","pass":REPORT.get("pass",False),"elapsed_s":REPORT.get("measurement_elapsed_s"),"violations":REPORT["violations"],"exception":REPORT.get("exception_type")}),flush=True)
    sys.exit(0 if REPORT.get("pass") else 1)


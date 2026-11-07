#!/usr/bin/env python3
"""Single focused real-protocol clear-only experiment; no endpoint model or audio device."""
import asyncio, hashlib, json, time, traceback
from pathlib import Path
import run as f
from aiohttp import web
from aiosendspin.client import SendspinClient
from aiosendspin.models.player import ClientHelloPlayerSupport, SupportedAudioFormat
from aiosendspin.models.types import AudioCodec, Roles, PairMethod
from aiosendspin.noise.keys import Identity, generate_psk, psk_id_for
from aiosendspin.noise.pairing import PairingAttempt
from aiosendspin.noise.trust_store import InMemoryClientPairingStore, InMemoryServerPairingStore, PairingPsk, ClientPairingConfig
from aiosendspin.server import SendspinServer, AudioFormat

ROOT=Path(__file__).resolve().parent
R={"experiment":"official paired Sendspin clear-only protocol","attempt":1,
   "long_run_verdict_unchanged":False,"audio_device_opened":False,"endpoint_model":False,
   "physical_flush_proof":False,"start_events":0,"clear_events":0,"end_events":0,
   "audio_chunks":0,"pcm_matches":[]}
async def main():
    with (ROOT/"clear-only-attempt-started.json").open("x") as out:
        json.dump({"created_unix_ns":time.time_ns()},out)
    sidentity,cidentity=Identity.generate(),Identity.generate()
    cstore,sstore=InMemoryClientPairingStore(),InMemoryServerPairingStore()
    await cstore.store_pairing_config(ClientPairingConfig(dynamic_pairing_code_enabled=False,unpaired_access_enabled=False))
    key=generate_psk()
    await cstore.set_pairing_psk(PairingPsk(psk_id_for(key),key))
    client=SendspinClient(cidentity,"Clear-only sink",[Roles.PLAYER],pairing_store=cstore,clock=f.CLOCK,
        state_supported_commands=[],required_lead_time_ms=100,min_buffer_ms=100,
        player_support=ClientHelloPlayerSupport(
          [SupportedAudioFormat(AudioCodec.PCM,2,f.RATE,16)],524288))
    server=SendspinServer(asyncio.get_running_loop(),sidentity,"Clear-only source",
          pairing_store=sstore,allow_unencrypted=False,allow_noncompliant_clients=False,clock=f.CLOCK)
    async def handle(request):
        ws=web.WebSocketResponse(); await ws.prepare(request)
        await client.attach_websocket(ws,expected_server_id=sidentity.peer_id)
        return ws
    app=web.Application();app.router.add_get("/sendspin",handle)
    runner=web.AppRunner(app); await runner.setup()
    site=web.TCPSite(runner,"127.0.0.1",0);await site.start()
    audio_event=asyncio.Event();clear_event=asyncio.Event();end_event=asyncio.Event()
    expected=[]
    def on_audio(ts,data,fmt,send_ahead):
        index=R["audio_chunks"];R["audio_chunks"]+=1
        R["pcm_matches"].append(index<len(expected) and data==expected[index])
        audio_event.set()
    def on_start(message): R["start_events"]+=1
    def on_clear(roles): R["clear_events"]+=1; clear_event.set()
    def on_end(roles): R["end_events"]+=1; end_event.set()
    client.add_audio_chunk_listener(on_audio)
    client.add_stream_start_listener(on_start)
    client.add_stream_clear_listener(on_clear)
    client.add_stream_end_listener(on_end)
    try:
        await server.connect_to_client_and_wait(f"ws://127.0.0.1:{runner.addresses[0][1]}/sendspin",
            pairing_attempt=PairingAttempt(PairMethod.PAIRING_PSK,pairing_psk=key,client_id=cidentity.peer_id))
        async with asyncio.timeout(20):
            while True:
                peer=server.get_client(cidentity.peer_id)
                if peer and peer.is_connected and peer.is_paired and peer.available and client.is_time_synchronized():break
                await asyncio.sleep(.02)
        assert peer.connection.is_encrypted
        R["authenticated_long_term_noise"]=True
        role=peer.role("player@v1")
        fmt=AudioFormat(f.RATE,16,2)
        assert role.set_preferred_format(fmt,AudioCodec.PCM)
        group=peer.group;push=group.start_stream();push.set_live_source(True)
        expected.append(f.pcm(0,0,1102))
        push.prepare_audio(f.pcm(0,0,1200),fmt)
        await push.commit_audio(play_start_us=f.CLOCK.now_us()+f.LEAD_US)
        await asyncio.wait_for(audio_event.wait(),2)
        assert R["audio_chunks"]==1 and R["pcm_matches"]==[True]
        audio_event.clear()
        clear_requested=f.CLOCK.now_us()
        push.clear()
        await asyncio.wait_for(peer.wait_role_drained("player"),2)
        R["local_drain_elapsed_us"]=f.CLOCK.now_us()-clear_requested
        R["client_clear_received_when_local_drain_returned"]=clear_event.is_set()
        await asyncio.wait_for(clear_event.wait(),2)
        R["clear_received_elapsed_us"]=f.CLOCK.now_us()-clear_requested
        R["end_events_after_clear_only"]=R["end_events"]
        R["start_events_after_clear_only"]=R["start_events"]
        R["server_stream_active_after_clear"]=role.stream_started
        R["connection_alive_after_clear"]=peer.is_connected and client.connected
        assert R["clear_events"]==1 and R["end_events"]==0 and R["start_events"]==1
        assert role.stream_started
        # The encoder's 98 pre-clear pending frames must not contaminate this PCM.
        expected.append(f.pcm(1,0,1102))
        push.prepare_audio(f.pcm(1,0,1200),fmt)
        await push.commit_audio(play_start_us=f.CLOCK.now_us()+f.LEAD_US)
        await asyncio.wait_for(audio_event.wait(),2)
        R["start_events_after_resume"]=R["start_events"]
        assert R["audio_chunks"]==2 and R["pcm_matches"]==[True,True]
        assert R["start_events"]==1 and R["end_events"]==0
        await group.stop()
        await asyncio.wait_for(peer.wait_role_drained("player"),2)
        await asyncio.wait_for(end_event.wait(),2)
        assert R["end_events"]==1
        R["pass"]=True
    finally:
        await client.disconnect();await server.close();await runner.cleanup()
if __name__=="__main__":
    before=hashlib.sha256((ROOT/"results.json").read_bytes()).hexdigest()
    try:asyncio.run(main())
    except BaseException as exc:
        R["pass"]=False;R["exception_type"]=type(exc).__name__;R["exception"]=str(exc)
        (ROOT/"clear-only-exception.txt").write_text(traceback.format_exc())
    finally:
        R["long_run_results_sha256"]=before
        R["long_run_verdict_unchanged"]=before==hashlib.sha256((ROOT/"results.json").read_bytes()).hexdigest()
        R["socket_binds"]=f.REPORT["socket_binds"];R["socket_connects"]=f.REPORT["socket_connects"]
        (ROOT/"clear-only-results.json").write_text(json.dumps(R,indent=2,sort_keys=True)+"\n")
        print(json.dumps(R,sort_keys=True))
    raise SystemExit(0 if R.get("pass") else 1)


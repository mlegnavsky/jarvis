const vm=require('node:vm'),fs=require('node:fs'),assert=require('node:assert/strict');
const classes={},calls=[],uploads=[];let requested=0,trackStops=0,recorder;
class Element{attachShadow(){const nodes={};this.shadowRoot={set innerHTML(s){for(const [,id] of s.matchAll(/id="([^"]+)"/g))nodes[id]={textContent:'',disabled:false,open:false,showModal(){this.open=true;},close(){this.open=false;},focus(){}};},getElementById:id=>nodes[id]};}}
class Recorder{static isTypeSupported(t){return t==='audio/mp4';}constructor(s,o){this.mimeType=o.mimeType;recorder=this;}start(){this.state='recording';}stop(){this.state='inactive';this.ondataavailable?.({data:new Blob(['audio'],{type:this.mimeType})});this.onstop?.();}}
const context={HTMLElement:Element,window:{MediaRecorder:Recorder},navigator:{mediaDevices:{getUserMedia:async()=>{requested++;return {getTracks:()=>[{stop:()=>trackStops++}]};}}},Blob,FormData,Date,Math,ArrayBuffer,DataView,Float32Array,setTimeout:()=>1,clearTimeout(){},setInterval:()=>2,clearInterval(){},customElements:{get:n=>classes[n],define:(n,c)=>classes[n]=c}};
vm.runInNewContext(fs.readFileSync(__dirname+'/../intercom.js','utf8'),context);
(async()=>{
 const c=new classes['jarvis-home-intercom']();c.setConfig({entity:'media_player.homepod'});c.hass={states:{'media_player.homepod':{state:'off'}},fetchWithAuth:async(url,opts)=>{uploads.push({url,body:opts.body});return {ok:true,json:async()=>({media_content_id:'media-source://media_source/local/jarvis_intercom/test.m4a'})};},callService:async(...a)=>calls.push(a),callWS:async()=>{}};
 const pending=c.shadowRoot.getElementById('record').onclick({stopPropagation(){}});assert.equal(requested,1,'first floorplan tap immediately requests microphone');await pending;
 assert.equal(c.phase,'recording');assert.equal(c.shadowRoot.getElementById('dialog').open,true);
 await c.start();assert.equal(requested,1,'second start cannot create parallel recording');
 c.stop();await new Promise(r=>setImmediate(r));assert.equal(uploads.length,1);assert.equal(calls.length,1);assert.equal(calls[0][0],'media_player');assert.equal(calls[0][1],'play_media');assert.equal(calls[0][2].entity_id,'media_player.homepod');assert.equal(calls[0][2].media_content_type,'audio/mp4');assert.equal(c.phase,'done');assert.ok(trackStops>0);
 await c.start();c.cancel();await new Promise(r=>setImmediate(r));assert.equal(uploads.length,1,'cancel never uploads or plays');assert.equal(c.shadowRoot.getElementById('dialog').open,false);
 let resolve;context.navigator.mediaDevices.getUserMedia=()=>new Promise(r=>resolve=r);const late=c.start();c.cancel();resolve({getTracks:()=>[{stop:()=>trackStops++}]});await late;assert.equal(uploads.length,1,'late microphone grant after cancel does not send');
 context.navigator.mediaDevices.getUserMedia=async()=>{throw Object.assign(new Error(),{name:'NotAllowedError'});};await c.start();assert.equal(c.phase,'error');assert.match(c.shadowRoot.getElementById('status').textContent,/mikrofon/i);
 c._hass.states['media_player.homepod'].state='unavailable';await c.start();assert.equal(c.phase,'error');assert.match(c.shadowRoot.getElementById('status').textContent,/HomePod/);
 c._hass.states['media_player.homepod'].state='off';context.navigator.mediaDevices.getUserMedia=async()=>({getTracks:()=>[{stop:()=>trackStops++}]});
 Recorder.isTypeSupported=()=>false;let processor,closed=0;
 context.window.AudioContext=class{constructor(){this.sampleRate=16000;}createMediaStreamSource(){return {connect(){},disconnect(){}};}createScriptProcessor(){return processor={connect(){},disconnect(){}};}async resume(){}async close(){closed++;}};
 await c.start();processor.onaudioprocess({inputBuffer:{getChannelData:()=>new Float32Array([0,.5,-.5])}});c.stop();await new Promise(r=>setImmediate(r));assert.equal(uploads.length,2);assert.equal(calls.at(-1)[2].media_content_type,'audio/wav');assert.equal(closed,1);
 c._hass.fetchWithAuth=async()=>({ok:false,status:403});await c.start();processor.onaudioprocess({inputBuffer:{getChannelData:()=>new Float32Array([0,.5])}});c.stop();await new Promise(r=>setImmediate(r));assert.equal(c.phase,'error');assert.match(c.shadowRoot.getElementById('status').textContent,/správce/);assert.equal(calls.length,2,'upload rejection never plays');
 const wav=await c.wav([new Float32Array([0,1,-1])],16000).arrayBuffer();assert.equal(new TextDecoder().decode(wav.slice(0,4)),'RIFF');assert.equal(new DataView(wav).getUint32(40,true),6);
 console.log('Direct intercom: immediate mic, stop/play, duplicate, cancel, late grant, permission, offline and WAV checks passed');
})().catch(e=>{console.error(e);process.exit(1)});

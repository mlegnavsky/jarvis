/* An explicit floorplan tap opens the microphone; speech is never interpreted as a command. */
class JarvisHomeIntercom extends HTMLElement {
 constructor(){
  super();this.phase='idle';this.session=0;this.attachShadow({mode:'open'});
  this.shadowRoot.innerHTML=`<style>
   :host{display:block}button{font:inherit;cursor:pointer;min-height:46px;border:0;border-radius:14px;padding:12px 16px;background:#1179a1;color:white}button:disabled{opacity:.5}button:focus-visible{outline:3px solid #69dfff;outline-offset:3px}
   #record{display:flex;align-items:center;justify-content:center;padding:10px;border-radius:50%;background:#071c32;color:#45d7ff;min-width:46px;min-height:46px}ha-icon{--mdc-icon-size:24px}
   dialog{box-sizing:border-box;width:min(350px,calc(100vw - 32px));border:1px solid #41647c;border-radius:22px;padding:24px;color:#edf7ff;background:#0b2238;text-align:center;font:16px system-ui;box-shadow:0 16px 60px #0008}dialog::backdrop{background:#03101c88}h2{font-size:21px;margin:0 0 12px}p{line-height:1.5;color:#bfd0dc}.dot{display:inline-block;width:14px;height:14px;border-radius:50%;background:#f45b64;margin-right:8px}#elapsed{font-size:28px;font-variant-numeric:tabular-nums;margin:16px 0}.buttons{display:flex;gap:10px;justify-content:center;flex-wrap:wrap}#cancel{background:#284156}button[hidden]{display:none}
  </style><button id="record" aria-label="Nahrát vzkaz domů" title="Nahrát vzkaz domů"><ha-icon icon="mdi:bullhorn"></ha-icon></button>
  <dialog id="dialog" aria-labelledby="heading"><h2 id="heading">Vzkaz domů</h2><p id="status" role="status" aria-live="polite"></p><div id="elapsed"></div><div class="buttons"><button id="stop">Odeslat domů</button><button id="cancel">Zrušit</button></div></dialog>`;
  this.el('record').onclick=e=>{e?.stopPropagation();return this.start();};
  this.el('stop').onclick=()=>this.stop();this.el('cancel').onclick=()=>this.cancel();
  this.el('dialog').oncancel=e=>{e.preventDefault();this.cancel();};
 }
 el(id){return this.shadowRoot.getElementById(id);}
 setConfig(c){this.cfg={entity:'media_player.homepod_obyvak_homepod_obyvak',...c};}
 set hass(h){this._hass=h;}
 status(phase,text){this.phase=phase;this.el('status').textContent=text;this.el('stop').hidden=phase!=='recording';this.el('cancel').textContent=['done','error'].includes(phase)?'Zavřít':'Zrušit';this.el('record').disabled=['requesting','recording','sending'].includes(phase);}
 stopTracks(stream=this.stream){for(const t of stream?.getTracks()||[])t.stop();if(stream===this.stream)this.stream=null;}
 async start(){
  if(['requesting','recording','sending'].includes(this.phase))return;
  const id=++this.session;this.el('elapsed').textContent='';if(!this.el('dialog').open)this.el('dialog').showModal();
  const player=this._hass?.states[this.cfg.entity];
  if(!player||['unavailable','unknown'].includes(player.state)){this.status('error','HomePod je nyní nedostupný.');return;}
  if(!navigator.mediaDevices?.getUserMedia){this.status('error','Mikrofon v tomto připojení není dostupný. Je potřeba zabezpečené připojení a povolený mikrofon.');return;}
  this.status('requesting','Povoluji mikrofon…');
  try{
   // Invoke directly from the tap, before any network request or navigation.
   const stream=await navigator.mediaDevices.getUserMedia({audio:{echoCancellation:true,noiseSuppression:true},video:false});
   if(id!==this.session){this.stopTracks(stream);return;}this.stream=stream;this.chunks=[];this.samples=[];
   const Recorder=window.MediaRecorder,mp4=Recorder?.isTypeSupported?.('audio/mp4');
   if(mp4){
    const rec=new Recorder(stream,{mimeType:'audio/mp4'});this.recorder=rec;
    rec.ondataavailable=e=>{if(id===this.session&&e.data.size)this.chunks.push(e.data);};
    rec.onerror=()=>{if(id===this.session){this.cancelCapture();this.status('error','Nahrávání se nepodařilo. Zkus to znovu.');}};
    rec.onstop=()=>{if(id!==this.session)return;this.stopTracks();this.upload(new Blob(this.chunks,{type:rec.mimeType||'audio/mp4'}),'m4a',id);};rec.start();
   }else{
    const Context=window.AudioContext||window.webkitAudioContext;if(!Context)throw new Error('recording_unsupported');
    this.audio=new Context();this.source=this.audio.createMediaStreamSource(stream);this.processor=this.audio.createScriptProcessor(4096,1,1);this.sampleRate=this.audio.sampleRate;
    this.processor.onaudioprocess=e=>{if(this.phase==='recording'&&id===this.session)this.samples.push(new Float32Array(e.inputBuffer.getChannelData(0)));};
    this.source.connect(this.processor);this.processor.connect(this.audio.destination);await this.audio.resume();
    if(id!==this.session){this.cancelCapture();return;}
   }
   this.started=Date.now();this.status('recording','Nahrávám tvůj hlas… Až domluvíš, klepni na Odeslat domů.');this.el('elapsed').textContent='0:00';
   this.tick=setInterval(()=>{this.el('elapsed').textContent='0:'+String(Math.min(30,Math.floor((Date.now()-this.started)/1000))).padStart(2,'0');},250);
   this.limit=setTimeout(()=>this.stop(),30000);
  }catch(error){if(id!==this.session)return;this.cancelCapture();this.status('error',error?.name==='NotAllowedError'?'Povol mikrofon pro Home Assistant, aby šel vzkaz nahrát.':'Mikrofon se nepodařilo spustit. Zkontroluj jeho oprávnění.');}
 }
 clearTimers(){clearTimeout(this.limit);clearInterval(this.tick);}
 closeAudio(){if(this.processor){this.processor.onaudioprocess=null;this.processor.disconnect();this.processor=null;}this.source?.disconnect();this.source=null;if(this.audio){this.audio.close().catch(()=>{});this.audio=null;}}
 cancelCapture(){this.clearTimers();if(this.recorder){this.recorder.onstop=null;this.recorder.ondataavailable=null;if(this.recorder.state!=='inactive')this.recorder.stop();this.recorder=null;}this.closeAudio();this.stopTracks();this.chunks=[];this.samples=[];}
 cancel(){++this.session;this.cancelCapture();this.status('idle','');this.el('dialog').close();}
 disconnectedCallback(){this.cancel();}
 stop(){
  if(this.phase!=='recording')return;this.clearTimers();this.status('sending','Posílám hlasový vzkaz domů…');
  if(this.recorder){this.recorder.stop();this.recorder=null;}
  else{const blob=this.wav(this.samples,this.sampleRate);this.closeAudio();this.stopTracks();this.upload(blob,'wav',this.session);}
 }
 wav(chunks,rate){
  const length=chunks.reduce((n,c)=>n+c.length,0),buffer=new ArrayBuffer(44+length*2),v=new DataView(buffer);
  const str=(at,s)=>{for(let i=0;i<s.length;i++)v.setUint8(at+i,s.charCodeAt(i));};
  str(0,'RIFF');v.setUint32(4,36+length*2,true);str(8,'WAVE');str(12,'fmt ');v.setUint32(16,16,true);v.setUint16(20,1,true);v.setUint16(22,1,true);v.setUint32(24,rate,true);v.setUint32(28,rate*2,true);v.setUint16(32,2,true);v.setUint16(34,16,true);str(36,'data');v.setUint32(40,length*2,true);
  let offset=44;for(const c of chunks)for(const n of c){const s=Math.max(-1,Math.min(1,n));v.setInt16(offset,s<0?s*32768:s*32767,true);offset+=2;}return new Blob([buffer],{type:'audio/wav'});
 }
 async removeMedia(media){try{await this._hass.callWS({type:'media_source/local_source/remove',media_content_id:media});}catch{/* Playback remains independent of cleanup. */}}
 async upload(blob,extension,id){
  let media;
  try{
   if(!blob.size||(blob.type==='audio/wav'&&blob.size<=44))throw new Error('Prázdná nahrávka. Zkus mluvit déle.');
   const form=new FormData();form.append('media_content_id','media-source://media_source/local/jarvis_intercom');form.append('file',blob,'vzkaz-'+Date.now()+'-'+Math.random().toString(36).slice(2,10)+'.'+extension);
   const response=await this._hass.fetchWithAuth('/api/media_source/local_source/upload',{method:'POST',body:form});
   if(!response.ok)throw new Error(response.status===403?'Pro odeslání je potřeba přihlášený správce domácnosti.':'Nahrávku se nepodařilo přenést domů.');
   media=(await response.json()).media_content_id;if(!media?.startsWith('media-source://media_source/local/jarvis_intercom/'))throw new Error('Nahrávku nelze načíst.');
   if(id!==this.session){await this.removeMedia(media);return;}
   await this._hass.callService('media_player','play_media',{entity_id:this.cfg.entity,media_content_id:media,media_content_type:blob.type,announce:true});
   // Leave enough time for the speaker to retrieve and play this short recording.
   setTimeout(()=>this.removeMedia(media),90000);
   if(id===this.session)this.status('done','Hlasový vzkaz byl předán HomePodu k přehrání.');
  }catch(error){if(media)await this.removeMedia(media);if(id===this.session)this.status('error',error?.message||'Vzkaz se nepodařilo odeslat.');}
  finally{if(id===this.session){this.chunks=[];this.samples=[];}}
 }
}
if(!customElements.get('jarvis-home-intercom'))customElements.define('jarvis-home-intercom',JarvisHomeIntercom);

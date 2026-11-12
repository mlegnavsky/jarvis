class JarvisHomeMessage extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({mode:'open'});
    this.shadowRoot.innerHTML = `<ha-card><div class="body"><h2>Vzkaz domů</h2><p>Napiš vzkaz nebo jej nadiktuj mikrofonem na klávesnici. HomePod v obýváku jej přečte po klepnutí na Přehrát doma.</p><label for="message">Sdělení domů</label><textarea id="message" rows="4" maxlength="500" placeholder="Co chceš doma říct?"></textarea><button id="send">📣 Přehrát doma</button><button id="mic">🎙 Nadiktovat vzkaz</button><button id="cancel" hidden>Zrušit</button><p id="transcript"></p><p id="status" role="status" aria-live="polite"></p></div></ha-card><style>:host{display:block}.body{padding:20px}h2{margin:0 0 8px;font-size:20px}p{line-height:1.5;color:var(--secondary-text-color)}button{font:inherit;min-height:48px;padding:12px 18px;cursor:pointer;border:0;border-radius:12px;color:var(--text-primary-color,#fff);background:var(--primary-color,#167ac6);margin:4px}textarea{box-sizing:border-box;width:100%;resize:vertical;min-height:110px;border:1px solid var(--divider-color,#698298);border-radius:12px;padding:12px;margin:8px 0;font:16px system-ui;background:var(--card-background-color,#fff);color:var(--primary-text-color,#142c42)}label{font-weight:600}button:disabled{opacity:.5}button[hidden]{display:none}</style>`;
    this._el('mic').onclick=()=>this._dictate();
    this._el('send').onclick=()=>this._send();
    this._el('cancel').onclick=()=>this._cancel();
  }
  setConfig(config) { this._config={media_player:'media_player.homepod_obyvak_homepod_obyvak',tts:'tts.piper',...config}; }
  set hass(hass) {this._hass=hass;}
  getCardSize(){return 4;}
  _el(id){return this.shadowRoot.getElementById(id);}
  _status(text){this._el('status').textContent=text;}
  _busy(value){this._el('mic').disabled=value;this._el('send').disabled=value;this._el('message').disabled=value;}
  disconnectedCallback(){this._cancel();}
  _cancel(){this._cancelled=true; if(this._recognition){this._recognition.abort();this._recognition=null;}this._el('cancel').hidden=true;this._busy(Boolean(this._sending));}
  _dictate(){
    if(this._sending || this._recognition)return;
    const Recognition=window.SpeechRecognition || window.webkitSpeechRecognition;
    if(!Recognition){this._status('Vzkaz nadiktuj mikrofonem na klávesnici iPhonu, nebo jej napiš do pole výše.');return;}
    this._cancelled=false; this._dictation='';this._failed=false;
    const rec=new Recognition();this._recognition=rec;rec.lang='cs-CZ';rec.continuous=false;rec.interimResults=false;
    this._busy(true);this._el('cancel').hidden=false;this._status('Poslouchám… Potom zkontroluj text a klepni na Přehrát doma.');
    rec.onresult=(event)=>{if(this._recognition!==rec)return;let message='';for(let i=0;i<event.results.length;i++)if(event.results[i].isFinal)message+=event.results[i][0].transcript+' ';this._dictation=message.trim().slice(0,500);this._message=this._dictation;this._el('message').value=this._dictation;};
    rec.onerror=(event)=>{if(this._recognition!==rec)return;this._failed=true;this._status(event.error==='not-allowed'?'Mikrofon není povolený. Povol jej pro Home Assistant v prohlížeči.':'Diktování se nepodařilo. Zkus mikrofon znovu.');};
    rec.onend=()=>{if(this._recognition!==rec)return;this._recognition=null;this._el('cancel').hidden=true;this._busy(false);if(!this._cancelled&&!this._failed)this._status(this._dictation?'Vzkaz je připravený. Klepni na Přehrát doma.':'Nic jsem nerozpoznala. Zkus to znovu nebo vzkaz napiš.');};
    try{rec.start();}catch(_error){this._recognition=null;this._busy(false);this._el('cancel').hidden=true;this._status('Mikrofon se nepodařilo spustit. Zkontroluj jeho oprávnění.');}
  }
  async _send(){
    if(this._sending || this._recognition)return;
    const message=this._el('message').value.trim();
    if(!message){this._status('Nejprve napiš nebo nadiktuj vzkaz.');return;}
    if(message.length>500){this._status('Zpráva může mít nejvýše 500 znaků.');return;}
    const player=this._hass?.states[this._config.media_player];
    if(!player || ['unavailable','unknown'].includes(player.state)){this._status('HomePod je nyní nedostupný. Vzkaz nebyl odeslán.');return;}
    this._sending=true;this._busy(true);this._status('Předávám vzkaz HomePodu…');
    try{await this._hass.callService('tts','speak',{entity_id:this._config.tts,media_player_entity_id:this._config.media_player,message,cache:false});this._status('Vzkaz byl předán k přehrání na HomePodu.');}
    catch(error){this._status('Vzkaz se nepodařilo předat: '+(error?.message||'chyba přehrávání'));}
    finally{this._sending=false;this._busy(false);}
  }
}
if(!customElements.get('jarvis-home-message'))customElements.define('jarvis-home-message',JarvisHomeMessage);

function jarvisBatteryDisplay(raw) {
  if(raw===null || raw===undefined || raw==='' || !Number.isFinite(Number(raw))) return {watts:null,label:'Stav není dostupný',direction:0};
  const watts=Number(raw)===0?0:-Number(raw); // Deye raw polarity is opposite to the display convention.
  return {watts,label:watts>0?'Nabíjí se':watts<0?'Vybíjí se':'V klidu',direction:Math.sign(watts)};
}
class JarvisEnergyFlow extends HTMLElement {
  constructor(){
    super();this.attachShadow({mode:'open'});
    this.shadowRoot.innerHTML=`<ha-card><h2>☀ Solár · Žitenice</h2><img alt="Orientační 3D pohled domu se solárními panely"><svg viewBox="0 0 600 200" role="img" aria-label="Živé toky energie mezi solárem, domem a baterií"><defs><marker id="arr" markerWidth="7" markerHeight="7" refX="6" refY="3" orient="auto-start-reverse"><path d="M0,0 L6,3 L0,6" fill="#45d5cb"/></marker></defs><path id="pvflow" d="M120 72 Q125 140 255 142" class="flow solar" marker-end="url(#arr)"/><path id="batflow" d="M345 142 Q475 140 480 72" class="flow"/><path d="M90 155 L255 155" class="gridline"/><g class="node"><circle cx="120" cy="38" r="28"/><text x="120" y="48" class="glyph">☀</text><text x="120" y="92" id="pv">—</text><text x="120" y="113" class="caption">Výroba</text></g><g class="node"><circle cx="480" cy="38" r="28"/><text x="480" y="48" class="glyph">▰</text><text x="480" y="92" id="battery">—</text><text x="480" y="113" class="caption" id="batterylabel">Baterie</text></g><g class="node"><circle cx="300" cy="142" r="31"/><text x="300" y="153" class="glyph">⌂</text><text x="300" y="193" id="load">—</text></g><text x="20" y="173" id="grid" class="gridtext">Síť —</text></svg><p id="note">Načítám data…</p><style>:host{display:block}ha-card{display:block;overflow:hidden;background:#081b30;color:#eef7ff;border-radius:18px;padding-top:1px}h2{font-size:18px;margin:16px 16px 4px}img{display:block;width:100%;max-height:270px;object-fit:contain;background:#0b1b30}svg{display:block;width:100%;max-height:220px}.node circle{fill:#112b44;stroke:#426080;stroke-width:2}.node text{text-anchor:middle;fill:#f3f8ff;font:600 21px sans-serif}.node .glyph{font-size:31px;fill:#ffd259}.node .caption{font:16px sans-serif;fill:#abc4d8}.gridtext{fill:#a3bed2;font:17px sans-serif}.flow{fill:none;stroke:#45d5cb;stroke-width:4;stroke-dasharray:8 6}.solar{stroke:#ffd259}.gridline{fill:none;stroke:#38536c;stroke-width:2}.moving{animation:flowdash 1.4s linear infinite}.reverse{animation-direction:reverse}p{margin:8px 16px 14px;font-size:13px;color:#b3c7d9}:host([compact]) img{max-height:140px}:host([compact]) svg{max-height:145px}@keyframes flowdash{to{stroke-dashoffset:-28}}@media(prefers-reduced-motion:reduce){.moving{animation:none}}</style>`;
  }
  setConfig(config){this._config=config;this.toggleAttribute('compact',config.compact!==false);}
  getCardSize(){return this._config?.compact===false?7:4;}
  set hass(hass){this._hass=hass;this._update();if(!this._imageUrl&&!this._resolving&&!this._imageFailed)this._resolveImage();}
  _num(id){const x=this._hass?.states[id]?.state;return x!==undefined&&x!==''&&Number.isFinite(Number(x))?Number(x):null;}
  _text(id,text){this.shadowRoot.getElementById(id).textContent=text;}
  _update(){
    const n=new Intl.NumberFormat('cs-CZ',{maximumFractionDigits:0});
    const pv=this._num('sensor.inverter_pv_power'),load=this._num('sensor.inverter_load_power'),grid=this._num('sensor.inverter_grid_power');
    const b=jarvisBatteryDisplay(this._num('sensor.inverter_battery_power'));
    const watts=x=>x===null?'Nedostupné':n.format(x)+' W';
    this._text('pv',watts(pv));this._text('load',watts(load));this._text('grid','Síť '+watts(grid));
    this._text('battery',b.watts===null?'Nedostupné':(b.watts>0?'+':'')+watts(b.watts));this._text('batterylabel',b.label);
    this._text('note','Baterie: + nabíjení · − vybíjení. 3D pohled je orientační.');
    this.shadowRoot.getElementById('pvflow').classList.toggle('moving',pv!==null&&pv>20);
    const path=this.shadowRoot.getElementById('batflow');path.classList.toggle('moving',b.direction!==0&&b.watts!==null);path.classList.toggle('reverse',b.direction<0);
    path.removeAttribute('marker-start');path.removeAttribute('marker-end');
    if(b.direction>0)path.setAttribute('marker-end','url(#arr)');else if(b.direction<0)path.setAttribute('marker-start','url(#arr)');
  }
  async _resolveImage(){this._resolving=true;try{const r=await this._hass.callWS({type:'media_source/resolve_media',media_content_id:'media-source://media_source/local/jarvis_dashboard/solar-house.png'});this._imageUrl=this._hass.hassUrl(r.url);this.shadowRoot.querySelector('img').src=this._imageUrl;}catch(_error){this._imageFailed=true;this.shadowRoot.querySelector('img').hidden=true;this._text('note','Náhled domu se nepodařilo načíst. Hodnoty pocházejí z měniče.');}finally{this._resolving=false;}}
}
if(!customElements.get('jarvis-energy-flow'))customElements.define('jarvis-energy-flow',JarvisEnergyFlow);

function jarvisContextEntity(path){
  for(const node of path){const value=node?.style?.getPropertyValue('--jarvis-entity')?.trim();if(value&&/^(light|switch|media_player|lock|sensor)\.[a-z0-9_]+$/.test(value))return value;}
  return null;
}
if(typeof document!=='undefined'&&!window.jarvisHistoryMenuInstalled){
  window.jarvisHistoryMenuInstalled=true;
  document.addEventListener('contextmenu',event=>{
    if(!window.location.pathname.startsWith('/hlavni-prehled/'))return;
    const entity=jarvisContextEntity(event.composedPath());if(!entity)return;
    event.preventDefault();event.stopPropagation();document.getElementById('jarvis-history-menu')?.remove();
    const menu=document.createElement('div');menu.id='jarvis-history-menu';menu.style.cssText=`position:fixed;left:${Math.min(event.clientX,window.innerWidth-210)}px;top:${Math.min(event.clientY,window.innerHeight-90)}px;z-index:10000;background:#102c45;color:white;border:1px solid #426784;border-radius:12px;padding:6px;box-shadow:0 8px 30px #0008`;
    const button=document.createElement('button');button.textContent='◷ Historie zařízení';button.style.cssText='border:0;background:transparent;color:white;font:16px sans-serif;padding:14px;cursor:pointer';button.onclick=()=>{window.location.assign('/hlavni-prehled/historie-'+entity.replace('.','-'));};menu.append(button);document.body.append(menu);button.focus();
    setTimeout(()=>document.addEventListener('pointerdown',e=>{if(!menu.contains(e.target))menu.remove();},{once:true}),0);
    menu.onkeydown=e=>{if(e.key==='Escape')menu.remove();};
  },true);
}


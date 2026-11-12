/* Room layout and navigation only. No device action runs without a button tap. */
class JarvisRoomPanel extends HTMLElement {
 setConfig(cfg){
  this.cfg=cfg;this.childrenCards=[];this.gesture=null;
  if(!this.shadowRoot)this.attachShadow({mode:'open'});
  this.build().catch(e=>{this.shadowRoot.textContent='Přehled místnosti nelze načíst: '+e.message;});
 }
 esc(v){return String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
 neighbor(direction){return this.cfg.rooms.find(room=>room.path===this.cfg.neighbors?.[direction]);}
 swipeDirection(dx,dy,ms){
  if(ms>800||Math.max(Math.abs(dx),Math.abs(dy))<60)return null;
  if(Math.abs(dx)>Math.abs(dy)*1.5)return dx<0?'right':'left';
  if(Math.abs(dy)>Math.abs(dx)*1.5)return dy<0?'down':'up';
  return null;
 }
 navigate(room){
  if(!room||!/^\/hlavni-prehled\/pokoj-[a-z-]+$/.test(room.path))return;
  history.pushState(null,'',room.path);window.dispatchEvent(new Event('location-changed'));
 }
 async build(){
  const c=this.cfg;
  this.shadowRoot.innerHTML=`<style>
   :host{display:block;max-width:680px;margin:auto;touch-action:pan-y;font-family:var(--paper-font-body1_-_font-family,system-ui)}
   ha-card{display:block;overflow:hidden;border-radius:20px;background:var(--ha-card-background,var(--card-background-color,#fff))}
   nav{display:grid;grid-template-columns:44px 1fr 44px;align-items:center;padding:8px;gap:6px}
   button{font:inherit;cursor:pointer;border:0;border-radius:12px;min-height:44px;background:var(--secondary-background-color,#edf2f7);color:var(--primary-text-color,#142c42)}
   button:focus-visible{outline:3px solid #1b9dcc;outline-offset:-3px}button:disabled{opacity:.45;cursor:default}
   .arrow{font-size:26px}.room{text-align:center;color:var(--primary-text-color);font-size:19px;font-weight:700}.hint{display:block;font-size:11px;font-weight:400;color:var(--secondary-text-color);margin-top:2px}
   .metrics{display:flex;gap:8px;position:absolute;bottom:12px;left:20px;right:20px;z-index:4}.metric{flex:1;border-radius:12px;background:#0b263e;color:#fff;text-align:center;padding:9px 5px;cursor:pointer}.metric small{display:block;font-size:11px;opacity:.76;margin-bottom:3px}.metric b{font-size:22px;font-weight:650;white-space:nowrap}
   #stage{position:relative}#picture{overflow:hidden;border-radius:14px;margin:0 8px;touch-action:none;overscroll-behavior:contain}#picture>*{display:block}
   #status{padding:10px 14px;color:var(--secondary-text-color);font-size:13px;line-height:1.4;background:var(--secondary-background-color,#edf2f7);margin:10px 12px;border-radius:10px}
   .actions{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:10px 12px}.action{padding:10px 6px;min-height:56px;font-size:13px;font-weight:600}.action:first-child{background:#0b527a;color:white}.action small{display:block;font-weight:400;margin-top:3px;font-size:11px}.error{color:#b71c1c;padding:0 12px;font-size:13px}
   .rooms{display:flex;gap:6px;overflow-x:auto;padding:8px 12px 12px;scrollbar-width:none}.rooms button{flex:0 0 auto;min-height:36px;padding:0 12px;font-size:12px;white-space:nowrap}.rooms button[aria-current=true]{background:#0b527a;color:white}
   .direction{position:absolute;z-index:5;background:rgba(8,29,48,.88);color:white;min-height:36px;padding:5px 10px;max-width:42%;font-size:12px;box-shadow:0 2px 8px #0004}.direction.up{top:10px;left:50%;transform:translateX(-50%)}.direction.down{bottom:10px;left:50%;transform:translateX(-50%)}.with-metrics .direction.down{bottom:94px}.direction.left{left:14px;top:45%;transform:translateY(-50%)}.direction.right{right:14px;top:45%;transform:translateY(-50%)}#extra{padding:0 12px 8px} .hidden{display:none}
  </style><ha-card>
   <nav aria-label="Místnost"><button class="home" aria-label="Celý dům">⌂</button><div class="room">${this.esc(c.title)}<span class="hint">Přecházení podle půdorysu domu</span></div><span></span></nav>
   <div class="actions">${(c.actions||[]).map((a,i)=>`<button class="action" data-action="${i}">${this.esc(a.label)}${a.subtitle?`<small>${this.esc(a.subtitle)}</small>`:''}</button>`).join('')}</div><div class="error" role="alert"></div>
   <div id="stage" class="${c.metrics?.length?'with-metrics':''}"><div id="picture"></div>${['up','left','right','down'].map(direction=>{const target=this.neighbor(direction);const arrow={up:'↑',left:'←',right:'→',down:'↓'}[direction];return target?`<button class="direction ${direction}" data-direction="${direction}" aria-label="${this.esc(target.title)}">${arrow} ${this.esc(target.title)}</button>`:'';}).join('')}
   <div class="metrics">${(c.metrics||[]).map((m,i)=>`<button class="metric" data-metric="${i}" aria-label="${this.esc(m.name)}"><small>${this.esc(m.name)}</small><b>—</b></button>`).join('')}</div></div>
   <div id="status" class="${c.status_entity?'':'hidden'}"></div>
   <div id="extra"></div><div class="rooms" aria-label="Místnosti">${c.rooms.map((r,i)=>`<button data-room="${i}" aria-current="${i===c.room_index}">${this.esc(r.title)}</button>`).join('')}</div>
  </ha-card>`;
  const root=this.shadowRoot;
  root.querySelector('.home').onclick=()=>{history.pushState(null,'','/hlavni-prehled/domov');window.dispatchEvent(new Event('location-changed'));};
  root.querySelectorAll('[data-direction]').forEach(b=>b.onclick=()=>this.navigate(this.neighbor(b.dataset.direction)));
  root.querySelectorAll('[data-room]').forEach(b=>b.onclick=()=>this.navigate(c.rooms[Number(b.dataset.room)]));
  root.querySelectorAll('[data-metric]').forEach(b=>b.onclick=()=>this.dispatchEvent(new CustomEvent('hass-more-info',{bubbles:true,composed:true,detail:{entityId:c.metrics[Number(b.dataset.metric)].entity}})));
  root.querySelectorAll('[data-action]').forEach(b=>b.onclick=async()=>{
   b.disabled=true;root.querySelector('.error').textContent='';
   try{const a=c.actions[Number(b.dataset.action)].tap_action;const [domain,service]=a.perform_action.split('.');await this.h.callService(domain,service,a.data||{});}
   catch{root.querySelector('.error').textContent='Povel se nepodařilo provést.';}
   finally{b.disabled=false;}
  });
  this.onpointerdown=e=>{
   this.gesture=null;this.suppressClick=false;
   if(e.isPrimary===false||(e.button!==undefined&&e.button!==0))return;
   if(!e.composedPath().some(n=>n.id==='picture'))return;
   if(e.composedPath().some(n=>/^(BUTTON|INPUT|SELECT|TEXTAREA|A|HA-ICON|HA-STATE-ICON|HUI-STATE-ICON-ELEMENT|JARVIS-DEVICE-STATUS)$/.test(n.tagName||'')))return;
   this.gesture={x:e.clientX,y:e.clientY,time:e.timeStamp,id:e.pointerId};
  };
  this.onpointermove=e=>{
   const g=this.gesture;if(!g||g.id!==e.pointerId)return;
   const dx=e.clientX-g.x,dy=e.clientY-g.y;
   if(Math.max(Math.abs(dx),Math.abs(dy))>12){e.preventDefault();this.suppressClick=true;}
  };
  this.onpointerup=e=>{
   const g=this.gesture;this.gesture=null;if(!g||g.id!==e.pointerId)return;
   const direction=this.swipeDirection(e.clientX-g.x,e.clientY-g.y,e.timeStamp-g.time);
   if(direction){e.preventDefault();e.stopPropagation();this.navigate(this.neighbor(direction));}
  };
  this.onpointercancel=()=>{this.gesture=null;};
  this.onclick=e=>{if(this.suppressClick){this.suppressClick=false;e.preventDefault();e.stopImmediatePropagation();}};
  // Capture prevents a swipe's synthetic click from reaching floorplan controls.
  if(!this.clickGuard){this.clickGuard=e=>{if(this.suppressClick){this.suppressClick=false;e.preventDefault();e.stopImmediatePropagation();}};this.addEventListener('click',this.clickGuard,true);}
  this.onkeydown=e=>{if(e.target!==this)return;const direction={ArrowLeft:'left',ArrowRight:'right',ArrowUp:'up',ArrowDown:'down'}[e.key];if(direction){e.preventDefault();this.navigate(this.neighbor(direction));}};
  this.tabIndex=0;
  const helpers=await window.loadCardHelpers();
  for(const [config,target] of [[c.picture,'#picture'],...(c.extra||[]).map(config=>[config,'#extra'])]){
   if(!config)continue;const card=helpers.createCardElement(config);this.childrenCards.push(card);root.querySelector(target).appendChild(card);if(this.h)card.hass=this.h;
  }
  this.update();
 }
 set hass(h){this.h=h;for(const card of this.childrenCards||[])card.hass=h;this.update();}
 update(){
  if(!this.h||!this.shadowRoot)return;
  (this.cfg.metrics||[]).forEach((m,i)=>{
   const s=this.h.states[m.entity],v=s?.state,n=Number(v),valid=v!==undefined&&v!==null&&v!==''&&Number.isFinite(n);
   const b=this.shadowRoot.querySelector(`[data-metric="${i}"] b`);
   if(b)b.textContent=valid?n.toLocaleString('cs-CZ',{maximumFractionDigits:1})+' '+(s.attributes?.unit_of_measurement||''):'Nedostupné';
  });
  const status=this.shadowRoot.querySelector('#status');if(status&&this.cfg.status_entity){const s=this.h.states[this.cfg.status_entity];status.textContent='Topení · '+(s?.state||'Nedostupné');}
 }
 getCardSize(){return 8;}
}
if(!customElements.get('jarvis-room-panel'))customElements.define('jarvis-room-panel',JarvisRoomPanel);

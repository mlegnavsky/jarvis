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
  const c=this.cfg,heater=c.picture?.elements?.find(e=>e.icon==='mdi:radiator'&&e.entity?.startsWith('switch.'));
  const heaterX=Math.max(0,Math.min(100,parseFloat(heater?.style?.left)||0)),heaterY=Math.max(0,Math.min(100,parseFloat(heater?.style?.top)||0));
  this.shadowRoot.innerHTML=`<style>
   :host{display:block;max-width:680px;margin:auto;touch-action:pan-y;font-family:var(--paper-font-body1_-_font-family,system-ui)}
   ha-card{display:block;overflow:hidden;border-radius:20px;background:var(--ha-card-background,var(--card-background-color,#fff))}
   button{font:inherit;cursor:pointer;border:0;border-radius:12px;min-height:44px;background:var(--secondary-background-color,#edf2f7);color:var(--primary-text-color,#142c42)}
   button:focus-visible{outline:3px solid #1b9dcc;outline-offset:-3px}button:disabled{opacity:.45;cursor:default}
   .metrics{display:flex;flex-direction:column;align-items:center;gap:5px;position:absolute;bottom:16px;left:50%;transform:translateX(-50%);z-index:4;max-width:80%}.metric{display:flex;align-items:center;justify-content:center;gap:5px;min-height:28px;min-width:92px;border-radius:8px;background:rgba(3,19,39,.82);color:#edf4fa;text-align:center;padding:3px 9px;line-height:1.35;cursor:pointer}.metric ha-icon{--mdc-icon-size:14px;flex:none}.metric b{font-size:13px;font-weight:400;white-space:nowrap}
   #stage{position:relative}#picture{overflow:hidden;border-radius:14px;margin:0 8px;touch-action:none;overscroll-behavior:contain}#picture>*{display:block}
   #status{padding:10px 14px;color:var(--secondary-text-color);font-size:13px;line-height:1.4;background:var(--secondary-background-color,#edf2f7);margin:10px 12px;border-radius:10px}
   .actions{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:10px 12px}.action{padding:10px 6px;min-height:56px;font-size:13px;font-weight:600}.action:first-child{background:#0b527a;color:white}.action small{display:block;font-weight:400;margin-top:3px;font-size:11px}.error{color:#b71c1c;padding:0 12px;font-size:13px}
   .heater-state{position:absolute;z-index:3;transform:translateX(-50%);font-size:11px;background:rgba(3,19,39,.9);color:white;padding:3px 7px;border-radius:6px;pointer-events:none;white-space:nowrap}#extra{padding:0 12px 8px}.hidden{display:none}
  </style><ha-card>
   <div class="actions">${(c.actions||[]).map((a,i)=>`<button class="action" data-action="${i}">${this.esc(a.label)}${a.subtitle?`<small>${this.esc(a.subtitle)}</small>`:''}</button>`).join('')}</div><div class="error" role="alert"></div>
   <div id="stage"><div id="picture"></div>${heater&&c.status_entity?`<span id="heater-state" class="heater-state" style="left:${heaterX}%;top:calc(${heaterY}% + 30px)"></span>`:''}
   <div class="metrics">${(c.metrics||[]).map((m,i)=>`<button class="metric" data-metric="${i}" aria-label="${this.esc(m.name)}"><ha-icon icon="${this.esc(m.icon||(/vlhk|humid/i.test(m.name+' '+m.entity)?'mdi:water-percent':'mdi:thermometer'))}" aria-hidden="true"></ha-icon><b>—</b></button>`).join('')}</div></div>
   <div id="status" class="${c.status_entity?'':'hidden'}"></div>
   <div id="extra"></div>
  </ha-card>`;
  const root=this.shadowRoot;
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
 heatingStatus(){
  const report=this.h?.states[this.cfg.status_entity],actual=this.h?.states[report?.attributes?.switch||this.cfg.heater_entity]?.state;
  const state={on:'Zapnuto',off:'Vypnuto'}[actual]||'Nedostupné';
  const reason=report?.state;
  return state+(reason&&!['unknown','unavailable'].includes(reason)?' · '+reason:'');
 }
 update(){
  if(!this.h||!this.shadowRoot)return;
  (this.cfg.metrics||[]).forEach((m,i)=>{
   const s=this.h.states[m.entity],v=s?.state,n=Number(v),valid=v!==undefined&&v!==null&&v!==''&&Number.isFinite(n);
   const b=this.shadowRoot.querySelector(`[data-metric="${i}"] b`);
   if(b)b.textContent=valid?n.toLocaleString('cs-CZ',{maximumFractionDigits:1})+' '+(s.attributes?.unit_of_measurement||''):'Nedostupné';
  });
  const status=this.shadowRoot.querySelector('#status');if(status&&this.cfg.status_entity){status.textContent='Topení · '+this.heatingStatus();}
  const badge=this.shadowRoot.querySelector('#heater-state');if(badge)badge.textContent=this.heatingStatus().split(' · ')[0];
 }
 getCardSize(){return 8;}
}
if(!customElements.get('jarvis-room-panel'))customElements.define('jarvis-room-panel',JarvisRoomPanel);

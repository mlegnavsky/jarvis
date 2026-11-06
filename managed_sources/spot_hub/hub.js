/* Spoty hub1.0.0. Render/read operations never invoke a device service. */
(function(global){
'use strict';
const number=v=>typeof v==='number'&&Number.isFinite(v)?v:null;
const numeric=v=>v!==null&&v!==undefined&&v!==''&&!['unknown','unavailable'].includes(v)&&Number.isFinite(Number(v))?Number(v):null;
const format=(v,d=2)=>number(v)===null?'—':v.toLocaleString('cs-CZ',{minimumFractionDigits:d,maximumFractionDigits:d});
const money=v=>format(v)+' Kč';
const moneyChoice=(data,full,known)=>number(data?.[full])??number(data?.[known]);
const currentNet=(sales,now=Date.now()/1000)=>sales?.price&&Number.isFinite(sales.price.start)&&Number.isFinite(sales.price.end)&&sales.price.start<=now&&now<sales.price.end?number(sales.price.net):null;
function shiftDate(key,period,step){
 const [y,m,d]=key.split('-').map(Number);let year=y,month=m-1,day=d;
 if(period==='month')month+=step;else if(period==='year')year+=step;else day+=step*(period==='week'?7:1);
 if(period==='month'||period==='year'){const base=new Date(Date.UTC(year,month,1));year=base.getUTCFullYear();month=base.getUTCMonth();day=Math.min(day,new Date(Date.UTC(year,month+1,0)).getUTCDate());}
 return new Date(Date.UTC(year,month,day,12)).toISOString().slice(0,10);
}
const math={money,currentNet,shiftDate,moneyChoice};if(typeof module!=='undefined')module.exports=math;
if(typeof document==='undefined')return;
const $=id=>document.getElementById(id),today=()=>new Intl.DateTimeFormat('en-CA',{timeZone:'Europe/Prague',year:'numeric',month:'2-digit',day:'2-digit'}).format(Date.now());
class Hub{
 constructor(){this.period='day';this.date=today();this.request=0;this.lastFinance=0;this.busy=false;this.cards=[];this.config={};this.dead=false;this.mounting=false;}
 getHost(){try{const w=global.parent;if(w.location.origin!==global.location.origin)return null;return w.document.querySelector('home-assistant')?.hass||global.__JARVIS_HASS__||null;}catch{return global.__JARVIS_HASS__||null;}}
 async start(){
  document.addEventListener('hass-more-info',event=>{
   const w=global.parent;if(w===global)return;
   const host=w.document.querySelector('home-assistant');if(!host)return;
   event.stopPropagation();host.dispatchEvent(new w.CustomEvent('hass-more-info',{detail:event.detail,bubbles:true,composed:true}));
  });
  $('date').value=this.date;
  document.querySelectorAll('[data-action]').forEach(b=>b.addEventListener('click',()=>this.action(b.dataset.action)));
  $('automatic').addEventListener('change',()=>this.action($('automatic').checked?'enable':'disable'));
  document.querySelectorAll('[data-period]').forEach(b=>b.addEventListener('click',()=>this.select(b.dataset.period,this.date)));
  $('date').addEventListener('change',()=>{if(/^\d{4}-\d{2}-\d{2}$/.test($('date').value))this.select(this.period,$('date').value);});
  $('previous').onclick=()=>this.select(this.period,shiftDate(this.date,this.period,-1));$('next').onclick=()=>this.select(this.period,shiftDate(this.date,this.period,1));$('today').onclick=()=>this.select(this.period,today());
  $('advanced').addEventListener('toggle',()=>{if($('advanced').open)this.mountLegacy();this.fit();});document.querySelectorAll('details').forEach(x=>x.addEventListener('toggle',()=>this.fit()));
  try{const response=await fetch('/local/jarvis-spot-hub-config.json?v=1.0.0',{credentials:'same-origin'});if(!response.ok)throw Error('configuration');this.config=await response.json();}catch{$('action-error').hidden=false;$('action-error').textContent='Podrobnosti stránky se nepodařilo načíst.';}
  this.update();this.timer=setInterval(()=>this.update(),2000);this.resize=new ResizeObserver(()=>this.fit());this.resize.observe($('app'));global.addEventListener('pagehide',()=>{this.dead=true;clearInterval(this.timer);this.resize.disconnect();},{once:true});
 }
 fit(){if(this.fitPending)return;this.fitPending=true;requestAnimationFrame(()=>{this.fitPending=false;try{const f=global.frameElement;if(!f)return;const height=Math.ceil($('app').getBoundingClientRect().height+4);if(Math.abs((this.frameHeight||0)-height)<3)return;this.frameHeight=height;f.style.height=height+'px';f.style.position='relative';f.style.display='block';const container=f.parentElement;if(container){container.style.paddingTop='0px';container.style.height=height+'px';}}catch{}});}
 update(){
  const h=this.getHost();if(!h){$('connection').textContent='Čekám na připojení HA';$('connection').className='live stale';return;}this.h=h;
  const entity=h.states['sensor.jarvis_energy_sales'],sales=entity?.attributes||{},prefs=sales.settings||{},requested=sales.automatic_requested??prefs.requested_automatic??prefs.automatic;
  const stamp=Date.parse(entity?.last_reported||entity?.last_updated||'');const fresh=Number.isFinite(stamp)&&Date.now()-stamp<60000&&stamp<=Date.now()+5000;
  $('connection').textContent=fresh?'● Živá data':'Čekám na čerstvá data';$('connection').className=fresh?'live':'live stale';
  if(!this.busy)$('automatic').checked=!!requested;
  const on=prefs.automatic&&!prefs.inhibited;$('auto-status').textContent=on?'Zapnuto':requested?'Pozastaveno':'Vypnuto';$('auto-status').className='badge '+(on?'on':requested?'wait':'');
  const net=fresh?currentNet(sales):null;$('net-price').textContent=format(net)+' Kč/kWh';
  const grid=this.read('sensor.inverter_grid_power'),pv=this.read('sensor.inverter_pv_power'),soc=this.read('sensor.inverter_battery');
  $('pv-live').textContent=format(pv===null?null:pv/1000)+' kW';$('soc-live').textContent=format(soc,0)+' %';$('grid-live').textContent=grid===null?'Síť —':(grid<0?'Prodáváme ':'Odebíráme ')+format(Math.abs(grid)/1000)+' kW';
  const active=sales.active&&sales.mode==='pv';const state=active?(sales.observed?'Prodáváme přebytky · '+format(grid===null?null:Math.max(0,-grid)/1000)+' kW':'Zapínám prodej přebytků…'):(sales.active&&sales.mode==='bias'?'Malý trvalý přetok · cíl 2 W':sales.reason||'Čekám na stav řízení.');
  $('sale-state').textContent=fresh?state:'Stav řízení není čerstvý; zobrazené údaje se mohou opožďovat.';
  $('limits').textContent='Přebytky od '+(sales.pv_surplus_soc??97)+' % baterie při kladném výkupu. Velký bateriový prodej zachovává 60 %, malý přetok 30 % (obnovení od 32 %). Maximální dodávka 9,3 kW.';
  $('recovery').textContent=sales.error?'Řízení hlásí: '+sales.error:(sales.measurement_recovery?.pending?'Po výpadku měření čeká HA na stabilní data a potvrzení domácího režimu.':'');
  $('updated').textContent='Živý stav · '+new Date().toLocaleTimeString('cs-CZ',{hour:'2-digit',minute:'2-digit',second:'2-digit'})+' · průběžné částky nejsou fakturace';
  if(!this.cardsMounted&&!this.mounting)this.mountCards();for(const card of this.cards)card.hass=h;
  if(!this.loadingFinance&&Date.now()-this.lastFinance>60000)this.finance();this.fit();
 }
 read(id){const s=this.h?.states[id],t=Date.parse(s?.last_reported||s?.last_updated||'');return Number.isFinite(t)&&Date.now()-t<60000&&t<=Date.now()+5000?numeric(s?.state):null;}
 async action(kind){
  if(this.busy||!this.h)return;
  if(kind==='manual'){const w=global.parent;w.history.pushState(null,'','/hlavni-prehled/vlastni-prodej');w.dispatchEvent(new w.Event('location-changed'));return;}
  this.busy=true;this.error='';$('action-error').hidden=true;document.querySelectorAll('[data-action],#automatic').forEach(b=>b.disabled=true);
  try{
   if(kind==='enable'||kind==='disable'||kind==='surplus')await this.h.callService('jarvis_spot_control','set_sales_automatic',{enabled:kind!=='disable'});
   else if(kind==='charge')await this.h.callService('jarvis_spot_control','start_test',{});
   else if(kind==='stop'){
    if(this.h.states['sensor.jarvis_spot_control']?.attributes?.active)await this.h.callService('jarvis_spot_control','stop_restore',{});
    await this.h.callService('jarvis_spot_control','stop_sale',{});
   }
  }catch(e){$('action-error').hidden=false;$('action-error').textContent=e?.message||'Povel se nepodařilo provést.';}
  finally{this.busy=false;document.querySelectorAll('[data-action],#automatic').forEach(b=>b.disabled=false);this.update();}
 }
 select(period,date){this.period=period;this.date=date;$('date').value=date;document.querySelectorAll('[data-period]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.period===period)));this.lastFinance=0;this.finance();this.syncChart();}
 async readFinances(){
  const keyOf=t=>new Intl.DateTimeFormat('en-CA',{timeZone:'Europe/Prague',year:'numeric',month:'2-digit',day:'2-digit'}).format(t);
  const midnight=key=>{let t=Date.parse(key+'T00:00:00Z');for(let i=0;i<2;i++){const parts=Object.fromEntries(new Intl.DateTimeFormat('en-GB',{timeZone:'Europe/Prague',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',second:'2-digit',hourCycle:'h23'}).formatToParts(t).filter(p=>p.type!=='literal').map(p=>[p.type,p.value]));const local=Date.UTC(+parts.year,+parts.month-1,+parts.day,+parts.hour,+parts.minute,+parts.second);t+=Date.parse(key+'T00:00:00Z')-local;}return t;};
  let first=this.date,last=shiftDate(first,'day',1);const d=new Date(this.date+'T12:00:00Z');
  if(this.period==='week'){first=shiftDate(this.date,'day',-((d.getUTCDay()+6)%7));last=shiftDate(first,'week',1);}
  if(this.period==='month'){first=this.date.slice(0,7)+'-01';last=shiftDate(first,'month',1);}
  if(this.period==='year'){first=this.date.slice(0,4)+'-01-01';last=(Number(this.date.slice(0,4))+1)+'-01-01';}
  const start=midnight(first),end=midnight(last),now=Date.now(),current=today();
  const empty={first,last,expected_days:0,available_days:0,quality:start>=now?'future':'partial',sale_czk:null,purchase_czk:null,known_sale_czk:null,known_purchase_czk:null,cash_balance_czk:null,known_cash_balance_czk:null,export_kwh:null,import_kwh:null};if(start>=now)return empty;
  let expected=0;for(let key=first;key<last&&key<=current;key=shiftDate(key,'day',1))expected++;
  const ids=['sensor.jarvis_dnes_prodano_za','sensor.jarvis_dnes_nakoupeno_za'];let rows=[];
  if(this.period!=='day'||this.date!==current){rows=await this.h.callApi('GET','history/period/'+new Date(start).toISOString()+'?end_time='+encodeURIComponent(new Date(Math.min(end,now)).toISOString())+'&filter_entity_id='+ids.join(',')+'&significant_changes_only');}
  const days=new Map();const add=(state,id)=>{const at=Date.parse(state.last_updated||state.last_changed||''),key=state.attributes?.date||keyOf(at);if(!Number.isFinite(at)||key<first||key>=last||key>current)return;const day=days.get(key)||{};if(!day[id]||at>=day[id].at)day[id]={state,at};days.set(key,day);};
  for(let i=0;i<rows.length;i++)for(const state of rows[i]||[])add(state,state.entity_id||ids[i]);
  if(first<=current&&current<last)for(const id of ids)if(this.h.states[id])add(this.h.states[id],id);
  let knownSale=0,knownPurchase=0,exported=0,imported=0,saleCount=0,purchaseCount=0,exportCount=0,importCount=0,complete=days.size===expected;
  for(const [key,day]of days){const sale=day[ids[0]]?.state,purchase=day[ids[1]]?.state;const a=sale?.attributes||{},b=purchase?.attributes||{};
   const sv=numeric(sale?.state),pv=numeric(purchase?.state),sk=sv??numeric(a.known_sale_czk),pk=pv??numeric(b.known_purchase_czk);if(sk!==null){knownSale+=sk;saleCount++;}if(pk!==null){knownPurchase+=pk;purchaseCount++;}
   const ek=numeric(a.export_kwh??b.export_kwh),ik=numeric(b.import_kwh??a.import_kwh);if(ek!==null){exported+=ek;exportCount++;}if(ik!==null){imported+=ik;importCount++;}
   if(sv===null||pv===null||a.quality==='partial'||b.quality==='partial'||key<current&&Math.min(numeric(a.as_of)??0,numeric(b.as_of)??0)*1000<midnight(shiftDate(key,'day',1))-60000)complete=false;
  }
  const ks=saleCount?knownSale:null,kp=purchaseCount?knownPurchase:null;return {...empty,expected_days:expected,available_days:days.size,quality:complete?'complete':'partial',known_sale_czk:ks,known_purchase_czk:kp,sale_czk:complete?ks:null,purchase_czk:complete?kp:null,known_cash_balance_czk:ks!==null&&kp!==null?ks-kp:null,cash_balance_czk:complete&&ks!==null&&kp!==null?ks-kp:null,export_kwh:exportCount?exported:null,import_kwh:importCount?imported:null};
 }
 async finance(){
  if(!this.h)return;const request=++this.request;this.loadingFinance=true;this.lastFinance=Date.now();
  for(const id of ['sale-money','purchase-money','balance-money'])$(id).textContent='— Kč';$('export-energy').textContent='— kWh';$('import-energy').textContent='— kWh';$('finance-status').textContent='Načítám uložené finanční záznamy…';
  try{
   const r=await this.readFinances();if(request!==this.request||this.dead)return;
   $('sale-money').textContent=money(moneyChoice(r,'sale_czk','known_sale_czk'));$('purchase-money').textContent=money(moneyChoice(r,'purchase_czk','known_purchase_czk'));
   const balance=moneyChoice(r,'cash_balance_czk','known_cash_balance_czk');$('balance-money').textContent=(number(balance)!==null&&balance>0?'+':'')+money(balance);$('balance-money').style.color=balance!==null&&balance<0?'#ad2929':'#148126';
   $('export-energy').textContent=format(number(r.export_kwh))+' kWh';$('import-energy').textContent=format(number(r.import_kwh))+' kWh';
   $('period-label').textContent=r.first===this.date&&this.period==='day'?new Date(this.date+'T12:00:00Z').toLocaleDateString('cs-CZ',{day:'numeric',month:'long',year:'numeric'}):r.first+' – '+shiftDate(r.last,'day',-1);
   $('finance-status').textContent=r.quality==='future'?'Pro budoucí období zatím nejsou naměřená data.':!r.available_days?'Pro toto období nejsou uložené finanční záznamy.':r.quality==='complete'?'Průběžný odhad z uložených čtvrthodin.':'Doložená část období · '+r.available_days+' z '+r.expected_days+' dnů s daty. Historie nebo ocenění není úplné; rozsah závisí na uložené historii HA.';
  }catch(e){if(request!==this.request)return;$('finance-status').textContent='Finanční přehled není dostupný. Zkus změnit období nebo stránku obnovit.';}
  finally{if(request===this.request)this.loadingFinance=false;this.fit();}
 }
 async mountCards(){
  this.mounting=true;
  try{
   const w=global.parent;if(!w.loadCardHelpers)throw Error('Čekám na nativní karty Home Assistantu.');this.helpers=await w.loadCardHelpers();
   if(!w.customElements.get('jarvis-power-sun')){await Promise.race([w.customElements.whenDefined('jarvis-power-sun'),new Promise((_,reject)=>setTimeout(()=>reject(Error('Graf zatím není načtený; obnov stránku.')),8000))]);}
   const chart=this.helpers.createCardElement({type:'custom:jarvis-power-sun'});chart.hass=this.h;$('chart-card').replaceChildren(chart);this.chart=chart;this.cards.push(chart);
   const tidy=()=>{if(!chart.shadowRoot||chart.shadowRoot.querySelector('#spot-hub-style'))return;const style=document.createElement('style');style.id='spot-hub-style';style.textContent='ha-card{border:0;box-shadow:none}.energy-summary,.balance-note,.periods{display:none!important}';chart.shadowRoot.appendChild(style);};
   this.chartObserver=new MutationObserver(tidy);if(chart.shadowRoot)this.chartObserver.observe(chart.shadowRoot,{childList:true});tidy();
   if(this.config.house){const house=this.helpers.createCardElement(this.config.house);house.hass=this.h;$('house-card').replaceChildren(house);this.cards.push(house);}
   this.cardsMounted=true;this.syncChart();
  }catch(e){$('chart-card').textContent=e.message;}
  finally{this.mounting=false;this.fit();}
 }
 syncChart(){if(!this.chart)return;this.chart.selectedDate=this.date;this.chart.period=this.period;this.chart.statsKey=null;this.chart.updated=0;this.chart.chartWindow=null;if(this.period==='day')this.chart.fetchHistory();else this.chart.fetchStats();this.chart.render();}
 async mountLegacy(){if(this.legacyMounted||!this.helpers)return;this.legacyMounted=true;for(const cfg of this.config.advanced||[]){const card=this.helpers.createCardElement(cfg);card.hass=this.h;$('advanced-cards').appendChild(card);this.cards.push(card);}this.fit();}
}
global.SpotHubMath=math;global.spotHub=new Hub();global.spotHub.start();
})(typeof window==='undefined'?globalThis:window);

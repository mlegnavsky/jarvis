/* Spoty hub1.3.0. Render/read operations never invoke a device service. */
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
function reserveView(sales,fresh){
 const p=sales?.weather_reserve||{};const valid=fresh&&number(p.required_soc)!==null;
 return {summary:!fresh?'Čekám na čerstvá data':!valid?'Čekám na výpočet rezervy':p.required_soc>=100?'Z baterie neprodávat':`Ponechat nejméně ${format(Math.max(p.required_soc,sales.sale_floor_soc||0),0)} %`,
  day:p.forecast_day||'—',production:format(p.forecast_pv_kwh,1)+' kWh',conservative:format(p.conservative_pv_kwh,1)+' kWh',
  house:format(p.house_with_margin_kwh,1)+' kWh',base:format(p.house_daily_kwh,1)+' kWh +25 % zásoba',capacity:format(p.capacity_kwh,2)+' kWh',
  reason:p.reason||'Výpočet ještě není dostupný.',quality:p.quality==='unavailable'?'Chybí platné podklady; prodej z baterie čeká.':'Odhad výroby z jedné referenční křivky; spotřeba '+(p.load_quality==='observed'?'průběžně měřená.':'zatím částečná, nejméně8 kWh/den před zásobou.'),
  age:p.forecast_issued_at?new Date(p.forecast_issued_at).toLocaleString('cs-CZ',{timeZone:'Europe/Prague'})+' · stáří '+format(Math.max(0,p.forecast_age_seconds||0)/60,0)+' min':'Předpověď není dostupná.'};
}
function monitorView(report,fresh,now=Date.now()/1000){
 const valid=fresh&&number(report?.checked_at)!==null&&now>=report.checked_at&&now-report.checked_at<30;
 if(!valid)return {summary:'Čekám na čerstvý dohled',result:'Skutečný tok nelze potvrdit.',alerts:[],measurements:[],incidents:[]};
 const op=report.operation||{},labels={measured_export:'Dodávku hlásí měnič',measured_charging:'Měří se nabíjení baterie',awaiting_export:'Čekám na měřenou dodávku',awaiting_charging:'Čekám na měřené nabíjení',unknown:'Chybí platná čerstvá měření',stopping:'Čekám na potvrzení ukončení',waiting:'Čekání podle plánu'};
 return {summary:(report.status==='error'?'Chyba · ':report.status==='warning'?'Upozornění · ':'V pořádku · ')+(op.label||'Dohled'),
  result:labels[op.result]||'Skutečný tok nelze potvrdit.',reason:op.reason||'',notice:op.evidence_notice||'',
  alerts:(report.alerts||[]).map(a=>a.message),
  measurements:Object.values(report.measurements||{}).map(v=>[v.label,format(v.value,1)+' '+(v.unit||''),number(v.age_seconds)===null?'—':format(v.age_seconds,1)+' s',v.status==='fresh'?'Čerstvé':v.status==='stale'?'Zastaralé':'Neplatné nebo chybí']),
  incidents:(report.recent_incidents||[]).slice().reverse().map(v=>[new Date(v.at*1000).toLocaleTimeString('cs-CZ',{timeZone:'Europe/Prague'}),v.event==='cleared'?'Vyřešeno · '+v.code:v.message])};
}
const math={money,currentNet,shiftDate,moneyChoice,reserveView,monitorView};if(typeof module!=='undefined')module.exports=math;
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
  try{const response=await fetch('/local/jarvis-spot-hub-config.json?v=1.2.0',{credentials:'same-origin'});if(!response.ok)throw Error('configuration');this.config=await response.json();}catch{$('action-error').hidden=false;$('action-error').textContent='Podrobnosti stránky se nepodařilo načíst.';}
  this.update();this.timer=setInterval(()=>this.update(),2000);this.resize=new ResizeObserver(()=>this.fit());this.resize.observe($('app'));global.addEventListener('pagehide',()=>{this.dead=true;clearInterval(this.timer);this.resize.disconnect();},{once:true});
 }
 fit(){if(this.fitPending)return;this.fitPending=true;requestAnimationFrame(()=>{this.fitPending=false;try{const f=global.frameElement;if(!f)return;const height=Math.ceil($('app').getBoundingClientRect().height+4);if(Math.abs((this.frameHeight||0)-height)<3)return;this.frameHeight=height;f.style.height=height+'px';f.style.position='relative';f.style.display='block';const container=f.parentElement;if(container){container.style.paddingTop='0px';container.style.height=height+'px';}}catch{}});}
 update(){
  const h=this.getHost();if(!h){this.renderMonitor(null,false);$('connection').textContent='Čekám na připojení HA';$('connection').className='live stale';return;}this.h=h;
  const entity=h.states['sensor.jarvis_energy_sales'],sales=entity?.attributes||{},prefs=sales.settings||{},requested=sales.automatic_requested??prefs.requested_automatic??prefs.automatic;
  const stamp=Date.parse(entity?.last_reported||entity?.last_updated||'');const fresh=Number.isFinite(stamp)&&Date.now()-stamp<60000&&stamp<=Date.now()+5000;
  $('connection').textContent=fresh?'● Živá data':'Čekám na čerstvá data';$('connection').className=fresh?'live':'live stale';
  if(!this.busy)$('automatic').checked=!!requested;
  const stopping=sales.active&&sales.phase==='stopping',on=prefs.automatic&&!prefs.inhibited&&!(sales.profile_issues?.length)&&sales.healthy!==false;$('auto-status').textContent=stopping?'Ukončuji prodej':on?'Zapnuto':requested?'Pozastaveno':'Vypnuto';$('auto-status').className='badge '+(on?'on':requested?'wait':'');
  const net=fresh?currentNet(sales):null;$('net-price').textContent=format(net)+' Kč/kWh';
  const grid=this.read('sensor.inverter_grid_power'),pv=this.read('sensor.inverter_pv_power'),soc=this.read('sensor.inverter_battery');
  $('pv-live').textContent=format(pv===null?null:pv/1000)+' kW';$('soc-live').textContent=format(soc,0)+' %';$('grid-live').textContent=grid===null?'Síť —':(grid<0?'Prodáváme ':'Odebíráme ')+format(Math.abs(grid)/1000)+' kW';
  const active=sales.active&&sales.mode==='pv';const state=active?(sales.observed?'Prodáváme přebytky · '+format(grid===null?null:Math.max(0,-grid)/1000)+' kW':'Zapínám prodej přebytků…'):(sales.active&&sales.mode==='bias'?'Malý trvalý přetok · cíl '+(sales.bias_policy?.target_export_w??20)+' W':sales.reason||'Čekám na stav řízení.');
  $('sale-state').className='muted'+(sales.error||prefs.inhibited?' status-fault':'');
  $('sale-state').textContent=fresh?(stopping?(sales.error||'Čekám na fyzické potvrzení ukončení prodeje.'):state):'Stav řízení není čerstvý; zobrazené údaje se mohou opožďovat.';
  const tr=global.JarvisMessages?.translate||((s)=>s);
  this.renderMonitor(sales.supervision,fresh);
  $('sale-state').textContent=tr($('sale-state').textContent);
  const stop=global.JarvisMessages?.stopInfo(sales.diagnostic_stop||sales.last_stop,prefs.last_controller_error);
  if($('stop-summary'))$('stop-summary').textContent=stop?stop.cause+' '+stop.outcome:'Zatím není zaznamenané ukončení prodeje.';
  if($('stop-cleanup'))$('stop-cleanup').textContent=stop?.cleanup||'';
  if($('stop-technical'))$('stop-technical').textContent=stop?.technical||'';
  const diagnosis=sales.diagnostics||{};
  if($('diagnostic-stage'))$('diagnostic-stage').textContent='Stav: '+({starting:'Spouštění',stopping:'Ověřuji ukončení',measurement_unavailable:'Chybí čerstvá data',safety_block:'Zásah ochrany',configuration_mismatch:'Nesouhlasí nastavení měniče',paused:'Pozastaveno',export_confirmed:'Dodávka potvrzena měřením',waiting_for_export:'Čekám na naměřenou dodávku',off:'Vypnuto',plan_complete:'Dnešní plán splněn',waiting:'Čekám na podmínky'}[diagnosis.stage]||'Načítám');
  if($('diagnostic-live'))$('diagnostic-live').textContent=JSON.stringify(diagnosis,null,2);
  const detail=global.JarvisMessages?.healthInfo(sales.health)||[];
  if(fresh&&detail.length)$('sale-state').textContent=detail.join(' ');
  const policy=sales.policy||{};
  if($('plan-limits'))$('plan-limits').textContent='Rezerva '+(sales.sale_floor_soc??policy.sale_soc??60)+' % · nejvýše '+format((policy.max_w??9300)/1000,1)+' kW · konec při rezervě nebo na konci plánu.';
  if($('sale-fee'))$('sale-fee').textContent='Po poplatku '+format(policy.sale_fee??.3)+' Kč/kWh';
  if($('purchase-price'))$('purchase-price').textContent=format(policy.purchase_rate??5)+' Kč/kWh';
  const block=sales.selected_block,clock=v=>new Date(v*1000).toLocaleTimeString('cs-CZ',{timeZone:'Europe/Prague',hour:'2-digit',minute:'2-digit'});
  $('today-plan').textContent=block?.day===today()?'Dnešní plán: '+clock(block.start)+'–'+clock(block.end)+' · průměr '+format(block.average_net)+' Kč/kWh':'Dnešní cenový plán zatím není dostupný.';
  if(sales.completed_battery_plan?.day===today())$('today-plan').textContent='Dnešní plán splněn.';
  const civil=today().split('-').map(Number),tomorrow=new Date(Date.UTC(civil[0],civil[1]-1,civil[2]+1)).toISOString().slice(0,10),next=sales.next_plan;
  if($('next-plan')){
   const ready=next?.day===tomorrow&&next.status==='ready'&&next.block?.day===tomorrow;
   $('next-plan').textContent=ready?'Další okno: zítra '+clock(next.block.start)+'–'+clock(next.block.end):next?.day===tomorrow&&next.status==='no_window'?'Zítra není vhodné prodejní okno.':'Čekáme na zítřejší ceny.';
   if($('next-plan-detail'))$('next-plan-detail').textContent=ready?'Nejvýhodnější okno z úplných zítřejších cen · průměr '+format(next.block.average_net)+' Kč/kWh po poplatku. '+(prefs.inhibited?'Automatika je pozastavená; zkontroluj důvod.':requested?'Spuštění automaticky po ověření baterie a ochran.':'Automatický prodej je vypnutý.'):'Plán se připraví po načtení úplných cen s kladným výkupem.';
  }
  if($('control-alert')){
   const alert=$('control-alert');alert.hidden=!stopping&&!prefs.inhibited&&sales.healthy!==false&&fresh&&!sales.measurement_recovery?.pending&&!sales.error&&!sales.profile_issues?.length;
   alert.textContent=sales.measurement_recovery?.pending?'Obnova po výpadku dat…':stopping?'Ověřuji bezpečné ukončení…':prefs.inhibited?'Automatika pozastavená · podrobnosti níže.':sales.error||sales.profile_issues?.length?'Řízení hlásí problém · podrobnosti níže.':'Čekáme na čerstvá data…';
  }
  if($('weather-summary')){
   const p=sales.weather_reserve||{},view=reserveView(sales,fresh);
   for(const [id,key] of Object.entries({'weather-summary':'summary','weather-day':'day','weather-production':'production','weather-conservative':'conservative','weather-house':'house','weather-base':'base','weather-capacity':'capacity','weather-reason':'reason','weather-quality':'quality','weather-issued':'age'}))$(id).textContent=view[key];
   const date=t=>new Date(t*1000).toLocaleString('cs-CZ',{timeZone:'Europe/Prague',day:'numeric',month:'numeric',hour:'2-digit',minute:'2-digit'});
   $('weather-horizon').textContent=p.horizon_start?date(p.horizon_start)+' → '+date(p.horizon_end):'Čekám na prodejní okno.';
   const table=(id,rows)=>{const body=$(id);body.replaceChildren();for(const values of rows){const tr=document.createElement('tr');for(const value of values){const td=document.createElement('td');td.textContent=value;tr.appendChild(td);}body.appendChild(tr);}};
   const signature=JSON.stringify([p.forecast_issued_at,p.required_soc,p.house_daily_kwh,p.horizon_start,p.recent_decisions?.length]);
   if(this.weatherSignature!==signature){this.weatherSignature=signature;
    table('weather-hours',(p.intervals||[]).map(v=>[date(v.start)+'–'+date(v.end),format(v.pv_kwh,2),format(v.house_kwh,2)]));
    table('weather-history',(p.recent_decisions||[]).slice().reverse().map(v=>[v.at?new Date(v.at).toLocaleTimeString('cs-CZ',{timeZone:'Europe/Prague',hour:'2-digit',minute:'2-digit'}):'—',v.forecast_day||'—',(v.reserve_soc>=100?'Bez prodeje':v.reserve_soc+' %'),format(v.forecast_pv_kwh,1)]));
   }
  }
  $('limits').textContent='Přebytky od '+(sales.pv_surplus_soc??97)+' % baterie při kladném výkupu. Rezerva plánu '+(sales.sale_floor_soc??policy.sale_soc??60)+' %, domácnosti '+(policy.home_soc??30)+' %, obnovení malého přetoku '+(policy.resume_soc??31)+' %. Maximální dodávka '+format((policy.max_w??9300)/1000,1)+' kW.';
  $('recovery').textContent=sales.error?'Řízení hlásí: '+tr(sales.error):(sales.measurement_recovery?.pending?'Po výpadku měření čeká HA na stabilní data a potvrzení domácího režimu.':'');
  $('updated').textContent='Živý stav · '+new Date().toLocaleTimeString('cs-CZ',{hour:'2-digit',minute:'2-digit',second:'2-digit'})+' · průběžné částky nejsou fakturace';
  if(!this.houseMounted&&!this.houseLoading)this.mountHouse();if(!this.cardsMounted&&!this.mounting)this.mountCards();for(const card of this.cards)card.hass=h;
  for(const label of this.houseLabels||[]){const id=label.dataset.entity;let value;
   if(id==='sensor.jarvis_tok_site')value=grid===null?'—':grid<0?'Prodáváme':'Odebíráme';
   else if(id==='sensor.jarvis_vykon_baterie'){const v=this.read('sensor.inverter_battery_power');value=format(v===null?null:Math.abs(v),0)+' W';}
   else if(id==='sensor.inverter_battery_temperature'||id==='sensor.inverter_temperature'){const v=this.read(id);value=format(v,1)+' °C';}
   else{const v=this.read(id);value=format(v,0)+(id==='sensor.inverter_battery'?' %':' W');}
   if(label.temperatureValue)label.temperatureValue.textContent=value;else label.textContent=value;
  }
  if(!this.loadingFinance&&Date.now()-this.lastFinance>60000)this.finance();this.fit();
 }
 renderMonitor(report,fresh){
  if($('monitor-summary')){
   const view=monitorView(report,fresh);
   $('monitor-summary').textContent=view.summary;$('monitor-result').textContent=view.result;
   $('monitor-reason').textContent=view.reason||'';$('monitor-notice').textContent=view.notice||'';
   $('monitor-alerts').textContent=view.alerts.join(' ');
   const rows=(id,items)=>{const root=$(id);root.replaceChildren();for(const values of items){const row=document.createElement('tr');for(const value of values){const cell=document.createElement('td');cell.textContent=value;row.appendChild(cell);}root.appendChild(row);}};
   rows('monitor-measurements',view.measurements);rows('monitor-incidents',view.incidents);
  }
 }
 read(id){
  const s=this.h?.states[id],sales=this.h?.states['sensor.jarvis_energy_sales'],sample=sales?.attributes?.telemetry?.[id];
  const candidates=[{value:numeric(s?.state),stamp:s?.last_reported||s?.last_updated},{value:numeric(sample?.state),stamp:sample?.source_reported}];
  if(id==='sensor.jarvis_spotreba_domu')candidates.push({value:numeric(sales?.attributes?.house_power_w),stamp:sales?.last_reported||sales?.last_updated});
  const fresh=candidates.map(x=>({...x,t:Date.parse(x.stamp||'')})).filter(x=>x.value!==null&&Number.isFinite(x.t)&&Date.now()-x.t<60000&&x.t<=Date.now()+5000).sort((a,b)=>b.t-a.t);
  return fresh[0]?.value??null;
 }
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
 async mountHouse(){
  this.houseLoading=true;
  try{
   const cfg=this.config.house;if(!cfg)throw Error('Chybí původní karta domečku.');
   const canvas=document.createElement('div');canvas.className='house-canvas';
   const bg=document.createElement('img');bg.className='house-background';bg.src=cfg.image;bg.alt='';canvas.appendChild(bg);
   const source=(cfg.elements||[]).find(e=>e.type==='image'&&e.image?.startsWith('media-source://'));
   if(!source)throw Error('Chybí původní obrázek domu.');
   const result=await this.h.callWS({type:'media_source/resolve_media',media_content_id:source.image});
   const url=new URL(result.url,global.parent.location.origin);if(!result.url||!['http:','https:'].includes(url.protocol)||url.origin!==global.parent.location.origin)throw Error('Obrázek domu není dostupný.');
   const photo=document.createElement('img');photo.className='original-house';photo.src=url.href;photo.alt='Původní obrázek vašeho domu s fotovoltaikou';canvas.appendChild(photo);
   this.houseLabels=[];
   for(const item of cfg.elements||[]){if(item.type!=='state-label')continue;const label=document.createElement('button');label.type='button';label.className='house-indicator';label.dataset.entity=item.entity;label.style.left=item.style.left;label.style.top=item.style.top;label.style.fontSize=item.style['font-size'];label.setAttribute('aria-label',item.entity);label.textContent='—';
    if(item.entity==='sensor.inverter_battery_temperature'||item.entity==='sensor.inverter_temperature'){
     const battery=item.entity==='sensor.inverter_battery_temperature';label.className+=' house-temperature';label.style.fontSize='';label.style.left=battery?'79%':'91.5%';label.style.top='34%';label.title=battery?'Teplota baterie':'Teplota měniče';label.setAttribute('aria-label',label.title);
     const icon=document.createElement('span');icon.className='temperature-icon';icon.innerHTML=battery?'<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="2" y="6" width="17" height="12" rx="2"/><path d="M21 10v4M6 10v4M10 10v4M14 10v4"/></svg>':'<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="4" y="2" width="16" height="20" rx="2"/><path d="M13 6l-4 7h5l-3 5M8 19h.01"/></svg>';
     const text=document.createElement('span');text.className='temperature-value';text.textContent='— °C';label.replaceChildren(icon,text);label.temperatureValue=text;
    }
    label.onclick=()=>{const w=global.parent;w.document.querySelector('home-assistant')?.dispatchEvent(new w.CustomEvent('hass-more-info',{detail:{entityId:item.entity},bubbles:true,composed:true}));};canvas.appendChild(label);this.houseLabels.push(label);}
   $('house-card').replaceChildren(canvas);this.houseMounted=true;this.update();
  }catch(e){$('house-card').textContent=e.message;}
  finally{this.houseLoading=false;this.fit();}
 }
 async mountCards(){
  this.mounting=true;
  try{
   if(!global.customElements.get('jarvis-power-sun'))throw Error('Graf se načítá; obnov stránku, pokud se nezobrazí.');
   const chart=document.createElement('jarvis-power-sun');chart.setConfig({type:'custom:jarvis-power-sun'});chart.hass=this.h;$('chart-card').replaceChildren(chart);this.chart=chart;this.cards.push(chart);
   const tidy=()=>{if(!chart.shadowRoot||chart.shadowRoot.querySelector('#spot-hub-style'))return;const style=document.createElement('style');style.id='spot-hub-style';style.textContent='ha-card{display:block;border:0;box-shadow:none}.balance-note,.periods{display:none!important}';chart.shadowRoot.appendChild(style);};
   this.chartObserver=new MutationObserver(tidy);if(chart.shadowRoot)this.chartObserver.observe(chart.shadowRoot,{childList:true});tidy();
   this.cardsMounted=true;this.syncChart();
  }catch(e){$('chart-card').textContent=e.message;}
  finally{this.mounting=false;this.fit();}
 }
 syncChart(){if(!this.chart)return;this.chart.selectedDate=this.date;this.chart.period=this.period;this.chart.statsKey=null;this.chart.updated=0;this.chart.chartWindow=null;if(this.period==='day')this.chart.fetchHistory();else this.chart.fetchStats();this.chart.render();}
 async mountLegacy(){if(this.legacyMounted)return;if(!this.helpers){if(!global.parent.loadCardHelpers)return;this.helpers=await global.parent.loadCardHelpers();}this.legacyMounted=true;for(const cfg of this.config.advanced||[]){const card=this.helpers.createCardElement(cfg);card.hass=this.h;$('advanced-cards').appendChild(card);this.cards.push(card);}this.fit();}
}
global.SpotHubMath=math;global.spotHub=new Hub();global.spotHub.start();
})(typeof window==='undefined'?globalThis:window);

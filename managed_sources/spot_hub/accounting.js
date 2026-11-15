/* Read-only interval accounting. No service calls, credentials or device writes. */
(function(root){
'use strict';
const finite=v=>v!==null&&v!==undefined&&v!==''&&Number.isFinite(Number(v))?Number(v):null;
const key=t=>new Intl.DateTimeFormat('en-CA',{timeZone:'Europe/Prague',year:'numeric',month:'2-digit',day:'2-digit'}).format(t);
const total=rows=>{const values=(rows||[]).map(r=>finite(r.change)).filter(v=>v!==null&&v>=0);return values.length?values.reduce((a,b)=>a+b,0):null;};
function calculate({start,end,exported=[],imported=[],prices=[],energy=[],importEnergy=[],rates=[]}){
 const quotes=new Map();
 for(const p of prices){const t=Date.parse(p.last_updated||p.last_changed||''),v=finite(p.state);if(Number.isFinite(t)&&v!==null)quotes.set(Math.floor(t/900000),v);}
 const rateAt=t=>{let out={purchase_rate:5,sale_fee:.30};for(const r of rates)if(Number(r.at)*1000<=t)out={...out,...r};return out;};
 let sale=0,priced=0,purchase=0,bought=0;const daily=new Map();
 const day=t=>{const date=key(t);if(!daily.has(date))daily.set(date,{date,known_sale_czk:0,known_purchase_czk:0,priced_export_kwh:0});return daily.get(date);};
 for(const r of exported){const t=Number(r.start),stop=Number(r.end??t+300000),v=finite(r.change);if(t<start||t>=end||v===null||v<0)continue;
  if(stop<=t||stop-t>900000||Math.floor(t/900000)!==Math.floor((stop-1)/900000))continue;
  const price=quotes.get(Math.floor(t/900000));if(price===undefined)continue;
  if(rates.some(r=>Number(r.at)*1000>t&&Number(r.at)*1000<stop))continue;
  const money=v*(price-rateAt(t).sale_fee);sale+=money;priced+=v;const d=day(t);d.known_sale_czk+=money;d.priced_export_kwh+=v;
 }
 for(const r of imported){const t=Number(r.start),v=finite(r.change);if(t<start||t>=end||v===null||v<0||rates.some(rate=>Number(rate.at)*1000>t&&Number(rate.at)*1000<Number(r.end??t+300000)))continue;const money=v*rateAt(t).purchase_rate;purchase+=money;bought+=v;day(t).known_purchase_czk+=money;}
 const meter=total(energy),importMeter=total(importEnergy),missing=meter===null?null:Math.max(0,meter-priced);
 // A fixed purchase tariff can price a daily meter total even without short-term rows.
 const tariffChanged=rates.some(r=>Number(r.at)*1000>start&&Number(r.at)*1000<end);
 if(importMeter!==null&&!tariffChanged){purchase=importMeter*rateAt(start).purchase_rate;for(const row of importEnergy){const v=finite(row.change);if(v!==null&&v>=0)day(Number(row.start)).known_purchase_czk=v*rateAt(Number(row.start)).purchase_rate;}}
 const covered=meter!==null&&Math.abs(meter-priced)<.001;
 const purchaseCovered=importMeter!==null&&(!tariffChanged||Math.abs(importMeter-bought)<.001);
 const knownSale=priced>0||meter===0?sale:null,knownPurchase=bought>0||importMeter!==null?purchase:null;
 return {sale_czk:covered?sale:null,known_sale_czk:knownSale,purchase_czk:purchaseCovered?purchase:null,known_purchase_czk:knownPurchase,
  cash_balance_czk:covered&&purchaseCovered?sale-purchase:null,known_cash_balance_czk:knownSale!==null&&knownPurchase!==null?sale-purchase:null,
  export_kwh:meter??total(exported),import_kwh:importMeter??total(imported),priced_export_kwh:priced,unpriced_export_kwh:missing,
  quality:covered&&purchaseCovered?'estimate':'partial',daily:[...daily.values()],source:'meter_statistics_5minute_and_historical_quarter_price'};
}
function groups(rows,monthly=false){const map=new Map();for(const row of rows){const date=row.date.slice(0,monthly?7:10);const out=map.get(date)||{date,known_sale_czk:null,known_purchase_czk:null};for(const field of ['known_sale_czk','known_purchase_czk']){const value=finite(row[field]);if(value!==null)out[field]=(out[field]??0)+value;}map.set(date,out);}return [...map.values()].sort((a,b)=>a.date.localeCompare(b.date));}
const inflight=new Map(),cache=new Map();
async function request(h,method,query,ttl=60000){const id=JSON.stringify([h.user?.id||'',method,query]),now=Date.now(),old=cache.get(id);if(old&&now-old.at<ttl)return old.value;if(inflight.has(id))return inflight.get(id);
 const promise=(method==='WS'?h.callWS(query):h.callApi('GET',query)).then(value=>{cache.set(id,{at:Date.now(),value});while(cache.size>32)cache.delete(cache.keys().next().value);return value;}).finally(()=>inflight.delete(id));inflight.set(id,promise);return promise;}
function ledgerRead(h,{start,end},now){
 const archive=h.states?.['sensor.jarvis_energy_archive'],server=archive?.attributes?.server,ledger=server?.finance;
 if(ledger?.schema!==2||!Array.isArray(ledger.days)||!ledger.days.length)return null;
 const rows=ledger.days.filter(row=>row.date>=key(start)&&row.date<=key(Math.min(end,now)-1));
 const current=key(now);if(start<=now&&now<end){
  const state=h.states?.['sensor.jarvis_dnes_prodano_za'],buy=h.states?.['sensor.jarvis_dnes_nakoupeno_za'];
  if(state?.attributes?.date===current){const a=state.attributes,b=buy?.attributes||{};rows.push({date:current,known_sale_czk:finite(state.state)??finite(a.known_sale_czk),known_purchase_czk:finite(buy?.state)??finite(b.known_purchase_czk),export_kwh:finite(h.states?.['sensor.inverter_today_energy_export']?.state),import_kwh:finite(h.states?.['sensor.inverter_today_energy_import']?.state),priced_export_kwh:finite(a.export_kwh),quality:a.quality==='estimate'?'estimate':'partial'});}
 }
 if(!rows.length)return null;
 const sum=field=>{const values=rows.map(row=>finite(row[field])).filter(v=>v!==null);return values.length?values.reduce((a,b)=>a+b,0):null;};
 const sale=sum('known_sale_czk'),purchase=sum('known_purchase_czk'),energy=sum('export_kwh'),priced=sum('priced_export_kwh');
 let expected=0;for(let date=key(start);date<=key(Math.min(end,now)-1);){expected++;const d=new Date(date+'T12:00Z');d.setUTCDate(d.getUTCDate()+1);date=d.toISOString().slice(0,10);}
 const complete=rows.length===expected&&rows.every(row=>row.quality==='estimate');
 return {daily:rows,known_sale_czk:sale,sale_czk:complete?sale:null,known_purchase_czk:purchase,purchase_czk:complete?purchase:null,cash_balance_czk:complete&&sale!==null&&purchase!==null?sale-purchase:null,known_cash_balance_czk:sale!==null&&purchase!==null?sale-purchase:null,export_kwh:energy,import_kwh:sum('import_kwh'),priced_export_kwh:priced,unpriced_export_kwh:energy!==null&&priced!==null?Math.max(0,energy-priced):null,quality:complete?'estimate':'partial',available_days:rows.length,expected_days:expected,pending_days:ledger.pending_days||0,source:'private_archive_timed_daily_meter_increments',as_of:ledger.captured_at};
}
async function read(h,{start,end},now=Date.now()){
 const stored=ledgerRead(h,{start,end},now);if(stored)return stored;
 const stop=Math.min(end,now),closed=end<now,ttl=closed?3600000:60000;
 if(start>=stop)return {quality:'future',daily:[],sale_czk:null,purchase_czk:null,export_kwh:null,import_kwh:null};
 const ids=['sensor.inverter_total_energy_export','sensor.inverter_total_energy_import'];
 const query={type:'recorder/statistics_during_period',start_time:new Date(start).toISOString(),end_time:new Date(stop).toISOString(),statistic_ids:ids,period:'5minute',types:['change'],units:{energy:'kWh'}};
 const path='history/period/'+new Date(start).toISOString()+'?end_time='+encodeURIComponent(new Date(stop).toISOString())+'&filter_entity_id=sensor.jarvis_spot_ote&no_attributes&significant_changes_only=0';
 const [detail,meters,prices]=await Promise.all([request(h,'WS',query,ttl),request(h,'WS',{...query,period:'day'},ttl),request(h,'GET',path,ttl)]);
 const prefs=h.states?.['sensor.jarvis_energy_sales']?.attributes?.settings||{};
 const result=calculate({start,end:stop,exported:detail[ids[0]]||[],imported:detail[ids[1]]||[],energy:meters[ids[0]]||[],importEnergy:meters[ids[1]]||[],prices:(prices||[]).flat(),rates:prefs.rate_history||[]});
 const dates=new Set(Object.values(meters).flat().filter(row=>Number.isFinite(Number(row.start))).map(row=>key(Number(row.start))));let expected=0;for(let t=start;t<stop;){expected++;const d=new Date(key(t)+'T12:00Z');d.setUTCDate(d.getUTCDate()+1);t=Date.parse(d.toISOString().slice(0,10)+'T00:00Z');}if(dates.size<expected)result.quality='partial';return {...result,available_days:dates.size,expected_days:expected,as_of:stop};
}
const api={calculate,groups,read,request,ledgerRead};if(typeof module!=='undefined')module.exports=api;root.JarvisAccounting=api;
})(typeof window==='undefined'?globalThis:window);
